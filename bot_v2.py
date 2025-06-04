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
import sqlite3
import tweepy
from textblob import TextBlob

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

# Environment variables (updated to match Replit secrets)
X_BEARER_TOKEN = os.getenv('X_BEARER_TOKEN')
X_CONSUMER_KEY = os.getenv('X_CONSUMER_KEY')  # Changed from X_API_KEY
X_CONSUMER_SECRET = os.getenv('X_CONSUMER_SECRET')  # Changed from X_API_SECRET
X_ACCESS_TOKEN = os.getenv('X_ACCESS_TOKEN')
X_ACCESS_TOKEN_SECRET = os.getenv('X_ACCESS_TOKEN_SECRET')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Validate environment variables
required_vars = {
    'X_BEARER_TOKEN': X_BEARER_TOKEN,
    'X_CONSUMER_KEY': X_CONSUMER_KEY,
    'X_CONSUMER_SECRET': X_CONSUMER_SECRET,
    'X_ACCESS_TOKEN': X_ACCESS_TOKEN,
    'X_ACCESS_TOKEN_SECRET': X_ACCESS_TOKEN_SECRET,
    'YOUTUBE_API_KEY': YOUTUBE_API_KEY,
    'DISCORD_WEBHOOK_URL': DISCORD_WEBHOOK_URL
}
missing_vars = [var_name for var_name, var_value in required_vars.items() if var_value is None]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}. Please set them in the Replit Secrets tab.")
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize SQLite database
conn = sqlite3.connect('crypto_bot.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS social_metrics (
    coin TEXT PRIMARY_KEY,
    mentions INTEGER,
    sentiment TEXT,
    last_updated TIMESTAMP
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS used_videos (
    coin TEXT,
    video_id TEXT,
    date_used TEXT,
    PRIMARY KEY (coin, video_id)
)''')
conn.commit()

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

# Utility functions
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

        # API client initialization
        def get_x_client():
            try:
                client = tweepy.Client(
                    bearer_token=X_BEARER_TOKEN,
                    consumer_key=X_CONSUMER_KEY,
                    consumer_secret=X_CONSUMER_SECRET,
                    access_token=X_ACCESS_TOKEN,
                    access_token_secret=X_ACCESS_TOKEN_SECRET,
                    wait_on_rate_limit=True
                )
                user = client.get_me()
                logger.debug(f"Successfully authenticated with X API. User: {user.data.username}")
                return client
            except Exception as e:
                logger.error(f"Failed to initialize X API client: {str(e)}")
                return None

        def get_youtube_service():
            try:
                youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
                logger.debug("YouTube API key retrieved successfully.")
                return youtube
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API: {str(e)}")
                return None

        # Fetch price from Coinbase with retry logic
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

        # Fetch price, 24h change, transaction volume, and historical data from CoinGecko
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

        # Predict price using linear regression
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

        # Fetch social metrics with caching
        async def fetch_social_metrics(x_client, coin: str, hashtag: str):
            # Check if cached data is recent (within 10 days)
            cursor.execute("SELECT mentions, sentiment, last_updated FROM social_metrics WHERE coin = ?", (coin,))
            result = cursor.fetchone()
            current_time = datetime.now()

            if result and (current_time - datetime.fromisoformat(result[2])) < timedelta(days=10):
                mentions, sentiment, _ = result
                logger.info(f"Using cached social metrics for {coin}: {mentions} mentions, {sentiment} sentiment")
                return {"mentions": mentions, "sentiment": sentiment}

            # Fetch new data if cache is outdated
            try:
                query = f"{hashtag} -is:retweet lang:en"
                tweets = x_client.search_recent_tweets(query=query, max_results=10)  # Reduced to 10 to minimize API usage
                if not tweets.data:
                    logger.warning(f"No tweets found for {hashtag}")
                    mentions = 0
                    sentiment_label = "N/A"
                else:
                    mentions = len(tweets.data)
                    logger.debug(f"Fetched {mentions} mentions for {hashtag}")

                    # Sentiment analysis
                    sentiments = [TextBlob(tweet.text).sentiment.polarity for tweet in tweets.data]
                    avg_sentiment = sum(sentiments) / len(sentiments)
                    sentiment_label = "Positive" if avg_sentiment > 0 else "Negative" if avg_sentiment < 0 else "Neutral"
                    logger.debug(f"Average sentiment score for {hashtag}: {avg_sentiment:.6f}")
                    logger.info(f"Social metrics for {coin}: {mentions} mentions, {sentiment_label} sentiment")

                # Update cache
                cursor.execute("INSERT OR REPLACE INTO social_metrics (coin, mentions, sentiment, last_updated) VALUES (?, ?, ?, ?)",
                               (coin, mentions, sentiment_label, current_time.isoformat()))
                conn.commit()

                return {"mentions": mentions, "sentiment": sentiment_label}
            except Exception as e:
                logger.error(f"Error fetching social metrics for {coin}: {str(e)}")
                return {"mentions": 0, "sentiment": "N/A"}

        # Fetch YouTube video with uniqueness tracking
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
                    cursor.execute("SELECT 1 FROM used_videos WHERE coin = ? AND video_id = ?", (coin, video_id))
                    if not cursor.fetchone():
                        title = item['snippet']['title']
                        url = f"https://youtu.be/{video_id}"
                        cursor.execute("INSERT INTO used_videos (coin, video_id, date_used) VALUES (?, ?, ?)",
                                       (coin, video_id, current_date))
                        conn.commit()
                        logger.info(f"Fetched YouTube video for {coin}: {title}")
                        return {"title": title, "url": url}

                logger.warning(f"No unused YouTube videos found for {coin}.")
                return {"title": "N/A", "url": "N/A"}
            except HttpError as e:
                logger.error(f"Error fetching YouTube video for {coin}: {str(e)}")
                return {"title": "N/A", "url": "N/A"}

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
    reply_text = format_$tweet(data)
    async with discord_session.post(DISCORD_WEBHOOK_URL, json={"content": reply_text}) as response:
        if response.status == 204:
            logger.info(f"Successfully posted {data['coin_name']} update to Discord. Status code: 204")
        else:
            logger.error(f"Failed to post {data['coin_name']} update to Discord. Status code: {response.status}")
    await asyncio.sleep(0.5)
else:
# Post to X
logger.debug("Starting main tweet posting")
main_tweet = x_client.create_tweet(text=main_post['text'])
logger.info(f"Posted main tweet with ID: {main_tweet.data['id']}.")

previous_tweet_id = main_tweet.data['id']
for data in results:
reply_text = format_tweet(data)
logger.debug(f"Starting reply tweet for {data['coin_name']}")
reply_tweet = x_client.create_tweet(
    text=reply_text,
    in_reply_to_tweet_id=previous_tweet_id
)
previous_tweet_id = reply_tweet.data['id']
logger.info(f"Posted reply for {data['coin_name']} with ID: {reply_tweet.data['id']}.")
await asyncio.sleep(0.5)

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
        conn.close()
        logger.debug(f"Script execution finished. Total runtime: {(datetime.now() - start_time).total_seconds():.2f} seconds")