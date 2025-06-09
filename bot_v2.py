import argparse
import asyncio
import logging
import os
from datetime import datetime, timedelta
import aiohttp
import numpy as np
from sklearn.linear_model import LinearRegression
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import tweepy

# Import only essential modules
from modules.api_clients import get_x_client, get_youtube_api_key
from modules.social_media import fetch_social_metrics
from modules.database import Database
from modules.x_thread_queue import start_x_queue, stop_x_queue, queue_x_thread, get_x_queue_status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler('crypto_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CryptoBot')

# Environment variables
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Initialize database
db = Database('crypto_bot.db')

# List of coins to track
COINS = [
    {'name': 'ripple', 'coingecko_id': 'ripple', 'symbol': 'XRP', 'hashtag': '#XRP'},
    {'name': 'hedera hashgraph', 'coingecko_id': 'hedera-hashgraph', 'symbol': 'HBAR', 'hashtag': '#HBAR'},
    {'name': 'stellar', 'coingecko_id': 'stellar', 'symbol': 'XLM', 'hashtag': '#XLM'},
    {'name': 'xdce crowd sale', 'coingecko_id': 'xinfin-network', 'symbol': 'XDC', 'hashtag': '#XDC'},
    {'name': 'sui', 'coingecko_id': 'sui', 'symbol': 'SUI', 'hashtag': '#SUI'},
    {'name': 'ondo finance', 'coingecko_id': 'ondo-finance', 'symbol': 'ONDO', 'hashtag': '#ONDO'},
    {'name': 'algorand', 'coingecko_id': 'algorand', 'symbol': 'ALGO', 'hashtag': '#ALGO'},
    {'name': 'casper network', 'coingecko_id': 'casper-network', 'symbol': 'CSPR', 'hashtag': '#CSPR'}
]

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

def get_date():
    return datetime.now().strftime("%Y-%m-%d")

async def fetch_coingecko_data(coingecko_id: str, session: aiohttp.ClientSession):
    """Fetch data from CoinGecko."""
    fallback_data = {
        'ripple': {'price': 2.21, 'change_24h': 5.2, 'volume': 1800.0},
        'hedera-hashgraph': {'price': 0.168, 'change_24h': 3.1, 'volume': 90.0},
        'stellar': {'price': 0.268, 'change_24h': 2.8, 'volume': 200.0},
        'xinfin-network': {'price': 0.045, 'change_24h': -1.2, 'volume': 25.0},
        'sui': {'price': 4.35, 'change_24h': 8.5, 'volume': 450.0},
        'ondo-finance': {'price': 1.95, 'change_24h': 4.1, 'volume': 65.0},
        'algorand': {'price': 0.42, 'change_24h': 1.9, 'volume': 85.0},
        'casper-network': {'price': 0.021, 'change_24h': -0.5, 'volume': 12.0}
    }

    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}?tickers=false&market_data=true"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                price = float(data['market_data']['current_price']['usd'])
                price_change_24h = float(data['market_data']['price_change_percentage_24h'])

                # Get volume data
                url2 = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart?vs_currency=usd&days=1"
                async with session.get(url2) as response2:
                    if response2.status == 200:
                        market_data = await response2.json()
                        tx_volume = sum([v[1] for v in market_data['total_volumes']]) / 1_000_000
                        historical_prices = [p[1] for p in market_data['prices']][-30:]
                        return price, price_change_24h, tx_volume, historical_prices

            # Fallback
            fallback = fallback_data.get(coingecko_id, {'price': 1.0, 'change_24h': 0.0, 'volume': 50.0})
            historical_prices = [fallback['price'] * (0.95 + 0.1 * i / 30) for i in range(30)]
            return fallback['price'], fallback['change_24h'], fallback['volume'], historical_prices

    except Exception as e:
        logger.error(f"Error fetching data for {coingecko_id}: {e}")
        fallback = fallback_data.get(coingecko_id, {'price': 1.0, 'change_24h': 0.0, 'volume': 50.0})
        historical_prices = [fallback['price'] * (0.95 + 0.1 * i / 30) for i in range(30)]
        return fallback['price'], fallback['change_24h'], fallback['volume'], historical_prices

def predict_price(historical_prices, current_price):
    if not historical_prices or len(historical_prices) < 2:
        return current_price * 1.005
    try:
        X = np.array(range(len(historical_prices))).reshape(-1, 1)
        y = np.array(historical_prices)
        model = LinearRegression()
        model.fit(X, y)
        predicted_price = model.predict([[len(historical_prices)]])[0]
        return predicted_price
    except Exception as e:
        logger.error(f"Error predicting price: {e}")
        return current_price * 1.005

async def fetch_youtube_video(youtube, coin: str, current_date: str):
    try:
        search_query = f"{coin} crypto 2025"
        request = youtube.search().list(
            part="snippet",
            q=search_query,
            type="video",
            maxResults=3,
            publishedAfter="2024-01-01T00:00:00Z"
        )
        response = request.execute()

        for item in response.get('items', []):
            video_id = item['id']['videoId']
            if not db.has_video_been_used(video_id):
                title = item['snippet']['title']
                url = f"https://youtu.be/{video_id}"
                db.add_used_video(coin, video_id, current_date)
                return {"title": title, "url": url, "video_id": video_id}

        # Fallback
        return {
            "title": f"Latest {coin.title()} Crypto Analysis",
            "url": f"https://youtube.com/results?search_query={coin.replace(' ', '+')}+crypto+2025",
            "video_id": ""
        }
    except Exception as e:
        logger.error(f"YouTube API error for {coin}: {e}")
        return {
            "title": f"{coin.title()} Crypto Updates",
            "url": f"https://youtube.com/results?search_query={coin.replace(' ', '+')}+crypto",
            "video_id": ""
        }

def format_tweet(data):
    change_symbol = "📉" if data['price_change_24h'] < 0 else "📈"

    tweet_content = (
        f"🚀 {data['coin_name']} ({data['coin_symbol']}) {change_symbol}\n\n"
        f"💰 Current: ${data['price']:.4f}\n"
        f"📈 24h: {data['price_change_24h']:+.2f}%\n"
        f"🔮 AI Prediction: ${data['predicted_price']:.4f}\n"
        f"📊 Volume: ${data['tx_volume']:.1f}M\n\n"
        f"📱 Social Buzz: {data['social_metrics']['mentions']} mentions ({data['social_metrics']['sentiment']})\n"
        f"🎥 Analysis: {data['youtube_video']['title'][:40]}...\n"
        f"{data['youtube_video']['url']}\n\n"
        f"{data['hashtag']} #CryptoAnalysis #Trading"
    )

    return tweet_content

async def main_bot_run(test_discord: bool = False, queue_only: bool = False):
    logger.info("Starting CryptoBotV2...")

    # Initialize clients
    x_client = None if test_discord else get_x_client(posting_only=True)
    youtube = build('youtube', 'v3', developerKey=get_youtube_api_key())

    async with aiohttp.ClientSession() as session:
        current_date = get_date()
        current_time = get_timestamp()

        # Fetch data for each coin
        results = []
        for coin in COINS:
            logger.info(f"Fetching data for {coin['symbol']}...")

            # Fetch price data
            price, price_change_24h, tx_volume, historical_prices = await fetch_coingecko_data(coin['coingecko_id'], session)
            predicted_price = predict_price(historical_prices, price)

            # Fetch social metrics
            social_metrics = await fetch_social_metrics(coin['coingecko_id'], session, skip_x_api=test_discord)

            # Get YouTube video
            youtube_video = await fetch_youtube_video(youtube, coin['name'], current_date)

            coin_data = {
                'coin_name': coin['name'],
                'coin_symbol': coin['symbol'],
                'price': price,
                'price_change_24h': price_change_24h,
                'predicted_price': predicted_price,
                'tx_volume': tx_volume,
                'hashtag': coin['hashtag'],
                'social_metrics': social_metrics,
                'youtube_video': youtube_video
            }

            results.append(coin_data)

        # Create main post
        main_post_text = f"🚀 Crypto Market Update ({current_date} at {current_time})! 📈 Latest on top altcoins. #Crypto #Altcoins"

        # Post to platforms
        if test_discord:
            # Discord only
            async with session.post(DISCORD_WEBHOOK_URL, json={"content": main_post_text}) as response:
                if response.status == 204:
                    logger.info("Posted main update to Discord")

            for data in results:
                reply_text = format_tweet(data)
                async with session.post(DISCORD_WEBHOOK_URL, json={"content": reply_text}) as response:
                    if response.status == 204:
                        logger.info(f"Posted {data['coin_name']} to Discord")
                await asyncio.sleep(0.5)

        elif queue_only:
            # X queue only
            start_x_queue()

            thread_posts = []
            for data in results:
                thread_posts.append({
                    'text': format_tweet(data),
                    'coin_name': data['coin_name']
                })

            queue_x_thread(thread_posts, main_post_text)
            logger.info(f"Queued thread with {len(thread_posts)} posts")

        else:
            # Direct X posting
            main_tweet = x_client.create_tweet(text=main_post_text)
            logger.info(f"Posted main tweet: {main_tweet.data['id']}")

            previous_tweet_id = main_tweet.data['id']
            for data in results:
                reply_text = format_tweet(data)
                reply_tweet = x_client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=previous_tweet_id
                )
                previous_tweet_id = reply_tweet.data['id']
                logger.info(f"Posted reply for {data['coin_name']}")
                await asyncio.sleep(5)

        logger.info("Bot run completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CryptoBotV2")
    parser.add_argument('--test-discord', action='store_true', help='Post to Discord only')
    parser.add_argument('--queue-only', action='store_true', help='Use X queue system')
    args = parser.parse_args()

    try:
        asyncio.run(main_bot_run(test_discord=args.test_discord, queue_only=args.queue_only))
    except Exception as e:
        logger.error(f"Script failed: {e}")
        raise
    finally:
        stop_x_queue()
        db.close()