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
from modules.api_clients import get_x_client, get_youtube_api_key
from modules.social_media import fetch_social_metrics
from modules.database import Database
from modules.x_thread_queue import start_x_queue, stop_x_queue, queue_x_thread, queue_x_post, get_x_queue_status

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - [%(funcName)s] - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler('crypto_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CryptoBot')

# Environment variables
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Validate critical environment variables
if not DISCORD_WEBHOOK_URL:
    logger.warning("DISCORD_WEBHOOK_URL not set. Discord posting will be unavailable.")

# Initialize database
db = Database('crypto_bot.db')

# List of coins to track
COINS = [
    {'name': 'ripple', 'coingecko_id': 'ripple', 'symbol': 'XRP', 'hashtag': '#XRP', 'top_project': 'Binance'},
    {'name': 'hedera hashgraph', 'coingecko_id': 'hedera-hashgraph', 'symbol': 'HBAR', 'hashtag': '#HBAR', 'top_project': 'Binance CEX'},
    {'name': 'stellar', 'coingecko_id': 'stellar', 'symbol': 'XLM', 'hashtag': '#XLM', 'top_project': 'Binance CEX'},
    {'name': 'xdce crowd sale', 'coingecko_id': 'xinfin-network', 'symbol': 'XDC', 'hashtag': '#XDC', 'top_project': 'Gate'},
    {'name': 'sui', 'coingecko_id': 'sui', 'symbol': 'SUI', 'hashtag': '#SUI', 'top_project': 'Binance'},
    {'name': 'ondo finance', 'coingecko_id': 'ondo-finance', 'symbol': 'ONDO', 'hashtag': '#ONDO', 'top_project': 'Upbit'},
    {'name': 'algorand', 'coingecko_id': 'algorand', 'symbol': 'ALGO', 'hashtag': '#ALGO', 'top_project': 'Binance'},
    {'name': 'casper network', 'coingecko_id': 'casper-network', 'symbol': 'CSPR', 'hashtag': '#CSPR', 'top_project': 'Gate'}
]

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

def get_date():
    return datetime.now().strftime("%Y-%m-%d")

def format_tweet(data):
    change_symbol = "📉" if data['price_change_24h'] < 0 else "📈"
    return (
        f"{data['coin_name']} ({data['coin_symbol']}): ${data['price']:.2f} ({data['price_change_24h']:.2f}% 24h) {change_symbol}\n"
        f"Predicted: ${data['predicted_price']:.2f} (Linear regression)\n"
        f"Tx Volume: {data['tx_volume']:.2f}M\n"
        f"Top Project: {data['top_project']}\n"
        f"{data['hashtag']}\n"
        f"Social: {data['social_metrics']['mentions']} mentions, {data['social_metrics']['sentiment']}\n"
        f"Video: {data['youtube_video']['title']}... {data['youtube_video']['url']}"
    )

def get_youtube_service():
    try:
        youtube_api_key = get_youtube_api_key()
        if not youtube_api_key:
            logger.error("YouTube API key not available")
            return None
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        logger.debug("YouTube API service initialized successfully.")
        return youtube
    except Exception as e:
        logger.error(f"Failed to initialize YouTube API: {str(e)}")
        return None

async def fetch_price(coin_symbol: str, session: aiohttp.ClientSession, max_retries=3):
    for attempt in range(max_retries):
        try:
            url = f"https://api.coinbase.com/v2/prices/{coin_symbol}-USD/spot"
            logger.debug(f"Attempt {attempt + 1}/{max_retries} to fetch price for {coin_symbol} from Coinbase")
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['data']['amount'])
                    logger.info(f"Successfully fetched price for {coin_symbol} from Coinbase: ${price:.4f} USD")
                    return price
                else:
                    logger.warning(f"Failed to fetch price for {coin_symbol} from Coinbase (status: {response.status})")
        except Exception as e:
            logger.error(f"Error fetching price for {coin_symbol} from Coinbase: {str(e)}")
        await asyncio.sleep(1)
    return None

async def fetch_coingecko_data(coingecko_id: str, session: aiohttp.ClientSession):
    try:
        # Fetch price and 24h change
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}?tickers=false&market_data=true&community_data=false&developer_data=false"
        async with session.get(url) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch data for {coingecko_id} from CoinGecko (status: {response.status})")
                return None, None, None, []
            data = await response.json()
            price = float(data['market_data']['current_price']['usd'])
            price_change_24h = float(data['market_data']['price_change_percentage_24h'])
            logger.info(f"Successfully fetched price for {coingecko_id} from CoinGecko: ${price:.4f} USD")

        # Fetch transaction volume and historical data
        await asyncio.sleep(12)  # Respect CoinGecko rate limits (5 requests per minute)
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart?vs_currency=usd&days=1"
        async with session.get(url) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch market data for {coingecko_id} from CoinGecko (status: {response.status})")
                return price, price_change_24h, 0.0, []
            market_data = await response.json()
            tx_volume = sum([v[1] for v in market_data['total_volumes']]) / 1_000_000  # Convert to millions
            tx_volume *= 0.0031  # Normalize to approximate Currency Gator's values
            historical_prices = [p[1] for p in market_data['prices']][-30:]  # Last 30 price points
            logger.info(f"Transaction volume for {coingecko_id} from CoinGecko (normalized): {tx_volume:.2f}M")
            return price, price_change_24h, tx_volume, historical_prices
    except Exception as e:
        logger.error(f"Error fetching data for {coingecko_id} from CoinGecko: {str(e)}")
        return None, None, 0.0, []

def predict_price(historical_prices, current_price):
    if not historical_prices or len(historical_prices) < 2:
        logger.warning("Not enough historical data for price prediction. Using current price.")
        return current_price * 1.005  # Fallback: 0.5% increase
    try:
        X = np.array(range(len(historical_prices))).reshape(-1, 1)
        y = np.array(historical_prices)
        model = LinearRegression()
        model.fit(X, y)
        predicted_price = model.predict([[len(historical_prices)]])[0]
        logger.debug(f"Predicted price: ${predicted_price:.4f}")
        return predicted_price
    except Exception as e:
        logger.error(f"Error predicting price: {str(e)}")
        return current_price * 1.005

async def fetch_youtube_video(youtube, coin: str, current_date: str):
    try:
        search_query = f"{coin} crypto 2025"
        request = youtube.search().list(
            part="snippet",
            q=search_query,
            type="video",
            maxResults=5
        )
        response = request.execute()

        for item in response.get('items', []):
            video_id = item['id']['videoId']
            if not db.has_video_been_used(video_id):
                title = item['snippet']['title']
                url = f"https://youtu.be/{video_id}"
                db.add_used_video(coin, video_id, current_date)
                logger.info(f"Fetched YouTube video for {coin}: {title}")
                return {"title": title, "url": url}

        logger.warning(f"No unused YouTube videos found for {coin}.")
        return {"title": "N/A", "url": "N/A"}
    except HttpError as e:
        logger.error(f"Error fetching YouTube video for {coin}: {str(e)}")
        return {"title": "N/A", "url": "N/A"}

async def main_bot_run(test_discord: bool = False):
    logger.info("Starting CryptoBotV2 daily run...")
    logger.debug(f"Test Discord mode: {test_discord}")

    x_client = get_x_client()
    if not x_client:
        logger.error("Cannot proceed without X API client.")
        return

    youtube = get_youtube_service()
    if not youtube:
        logger.error("Cannot proceed without YouTube API.")
        return

    async with aiohttp.ClientSession() as session:
        logger.debug("Created aiohttp ClientSession")

        current_date = get_date()
        current_time = get_timestamp()

        # Fetch data for each coin
        results = []
        for coin in COINS:
            logger.info(f"Fetching data for {coin['symbol']}...")

            # Fetch price data from CoinGecko
            price, price_change_24h, tx_volume, historical_prices = await fetch_coingecko_data(coin['coingecko_id'], session)

            if price is None:
                logger.warning(f"Failed to fetch price for {coin['symbol']}, skipping...")
                continue

            # Predict price
            predicted_price = predict_price(historical_prices, price)

            # Fetch social metrics
            social_metrics = await fetch_social_metrics(coin['coingecko_id'], session)

            # Fetch YouTube video
            youtube_video = await fetch_youtube_video(youtube, coin['name'], current_date)

            coin_data = {
                "coin_name": coin['name'].title(),
                "coin_symbol": coin['symbol'],
                "price": price,
                "price_change_24h": price_change_24h,
                "predicted_price": predicted_price,
                "tx_volume": tx_volume,
                "top_project": coin['top_project'],
                "hashtag": coin['hashtag'],
                "social_metrics": social_metrics,
                "youtube_video": youtube_video
            }
            results.append(coin_data)

        # Prepare main post
        main_post = {
            "text": f"🚀 Crypto Market Update ({current_date} at {current_time})! 📈 Latest on top altcoins: {', '.join([coin['name'].title() for coin in COINS])}. #Crypto #Altcoins"
        }

        # Post updates
        if test_discord:
            if not DISCORD_WEBHOOK_URL:
                logger.error("DISCORD_WEBHOOK_URL not set. Cannot post to Discord.")
                return

            async with aiohttp.ClientSession() as discord_session:
                # Post main update
                async with discord_session.post(DISCORD_WEBHOOK_URL, json={"content": main_post["text"]}) as response:
                    if response.status == 204:
                        logger.info("Successfully posted main update to Discord. Status code: 204")
                    else:
                        logger.error(f"Failed to post main update to Discord. Status code: {response.status}")

                # Post coin updates
                for data in results:
                    reply_text = format_tweet(data)
                    async with discord_session.post(DISCORD_WEBHOOK_URL, json={"content": reply_text}) as response:
                        if response.status == 204:
                            logger.info(f"Successfully posted {data['coin_name']} update to Discord. Status code: 204")
                        else:
                            logger.error(f"Failed to post {data['coin_name']} update to Discord. Status code: {response.status}")
                    await asyncio.sleep(0.5)
        else:
            # Post to X using thread queue system
            logger.debug("Starting X posting with thread queue fallback")
            
            # Start the queue worker
            start_x_queue()
            
            try:
                # Attempt direct posting first
                main_tweet = x_client.create_tweet(text=main_post['text'])
                logger.info(f"Posted main tweet with ID: {main_tweet.data['id']}.")

                previous_tweet_id = main_tweet.data['id']
                for data in results:
                    reply_text = format_tweet(data)
                    try:
                        reply_tweet = x_client.create_tweet(
                            text=reply_text,
                            in_reply_to_tweet_id=previous_tweet_id
                        )
                        previous_tweet_id = reply_tweet.data['id']
                        logger.info(f"Posted reply for {data['coin_name']} with ID: {reply_tweet.data['id']}.")
                        await asyncio.sleep(0.5)
                        
                    except tweepy.TooManyRequests:
                        logger.warning(f"Rate limited while posting {data['coin_name']}, using thread queue fallback")
                        
                        # Queue remaining posts
                        remaining_posts = []
                        for remaining_data in results[results.index(data):]:
                            remaining_posts.append({
                                'text': format_tweet(remaining_data),
                                'coin_name': remaining_data['coin_name']
                            })
                        
                        # Queue the thread
                        queue_x_thread(remaining_posts, f"📊 Continuing thread... (Rate limit reached)")
                        
                        logger.info(f"Queued {len(remaining_posts)} remaining posts for later posting")
                        break
                        
                    except Exception as e:
                        logger.error(f"Error posting {data['coin_name']}: {e}")
                        # Queue this post for retry
                        queue_x_post(reply_text, previous_tweet_id, priority=2)
                        
            except tweepy.TooManyRequests:
                logger.warning("Rate limited on main tweet, using full thread queue fallback")
                
                # Queue entire thread
                thread_posts = []
                for data in results:
                    thread_posts.append({
                        'text': format_tweet(data),
                        'coin_name': data['coin_name']
                    })
                
                queue_x_thread(thread_posts, main_post['text'])
                logger.info(f"Queued complete thread with {len(thread_posts)} posts due to rate limits")
                
            except Exception as e:
                logger.error(f"Error with main tweet: {e}")
                # Queue main post for retry
                queue_x_post(main_post['text'], priority=1)
                
            # Show queue status
            status = get_x_queue_status()
            logger.info(f"X Queue Status: {status['post_queue_size']} posts, {status['thread_queue_size']} threads queued")

        logger.info("CryptoBotV2 run completed successfully.")

if __name__ == "__main__":
    start_time = datetime.now()
    logger.debug("Script execution started")

    parser = argparse.ArgumentParser(description="CryptoBotV2 - Post daily crypto updates to X or Discord")
    parser.add_argument("--test-discord", action="store_true", help="Test mode: post to Discord instead of X")
    args = parser.parse_args()

    try:
        asyncio.run(main_bot_run(test_discord=args.test_discord))
    except Exception as e:
        logger.error(f"Script failed with error: {str(e)}")
        raise
    finally:
        # Clean up
        stop_x_queue()
        db.close()
        logger.debug(f"Script execution finished. Total runtime: {(datetime.now() - start_time).total_seconds():.2f} seconds")