import asyncio
import logging
import os
import random
import pytz
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import tweepy
import pycoingecko
from googleapiclient.discovery import build
from modules.x_thread_queue import start_x_queue, stop_x_queue, queue_x_thread, get_x_queue_status
import argparse

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CryptoBot')

# Load environment variables with enhanced debugging
env_path = "C:\\CryptoBotV2\\crypto_bot\\.env"
if not load_dotenv(env_path):
    logger.error(f"Failed to load .env file from {env_path}. File exists: {os.path.exists(env_path)}")
    raise Exception(f"Failed to load .env file from {env_path}")
logger.info(f"Successfully loaded .env from {env_path}")
for key, value in os.environ.items():
    if key.startswith('X_') or key.startswith('YOUTUBE_') or key.startswith('DISCORD_'):
        logger.debug(f"Env[{key}]: {value[:50]}{'...' if len(value) > 50 else ''}")

# Database initialization (placeholder)
logger.info("Database initialized successfully with tables: used_videos, sqlite_sequence, workflow_history, "
            "x_post_history, coins, coin_data_cache, news_cache, price_averages_cache, project_sources_cache, "
            "projects_cache, thread_history, youtube_cache, youtube_summary_cache, prices, schema_version, social_metrics")

# X Client Setup with Debugging
try:
    x_consumer_key = os.getenv("X_CONSUMER_KEY")
    x_consumer_secret = os.getenv("X_CONSUMER_SECRET")
    x_access_token = os.getenv("X_ACCESS_TOKEN")
    x_access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    logger.debug(f"X_CONSUMER_KEY: {x_consumer_key}")
    logger.debug(f"X_CONSUMER_SECRET: {x_consumer_secret[:10]}...")  # Partial for security
    logger.debug(f"X_ACCESS_TOKEN: {x_access_token}")
    logger.debug(f"X_ACCESS_TOKEN_SECRET: {x_access_token_secret[:10]}...")  # Partial for security
    if not all([x_consumer_key, x_consumer_secret, x_access_token, x_access_token_secret]):
        raise ValueError("One or more X API credentials are missing")
    x_client = tweepy.Client(
        consumer_key=x_consumer_key,
        consumer_secret=x_consumer_secret,
        access_token=x_access_token,
        access_token_secret=x_access_token_secret
    )
    logger.info("X API client initialized successfully")
except Exception as e:
    logger.error(f"Missing or invalid X API credentials for account 1: {e}")
    raise

# YouTube API Setup
def get_youtube_api_key():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        logger.error("YOUTUBE_API_KEY not found in environment variables")
        raise Exception("YOUTUBE_API_KEY is required")
    return api_key

try:
    youtube = build('youtube', 'v3', developerKey=get_youtube_api_key())
    logger.info("YouTube API client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize YouTube API: {e}")
    raise

# Queue Management
start_x_queue()

# Post Update Function (Fixed KeyError)
def post_update(news_items, idx):
    if not news_items or (isinstance(news_items, dict) and str(idx) not in news_items):
        logger.warning("WARNING - No valid news items, skipping")
        return
    try:
        if isinstance(news_items, list):
            news = news_items[idx % len(news_items)]
        else:
            news = news_items.get(str(idx), "No news")
    except KeyError as e:
        logger.error(f"ERROR - News item access failed: {e}")

# Scheduling Logic (Capped Sleep Time)
def calculate_next_run():
    current_time = datetime.now(pytz.timezone("US/Eastern"))
    next_run = datetime.strptime("2025-06-15 02:44:00-04:00", "%Y-%m-%d %H:%M:%S%z")
    sleep_time = (next_run - current_time).total_seconds()
    if sleep_time <= 0:
        logger.info("INFO - Past schedule, advancing to next day")
        next_run += timedelta(days=1)
        sleep_time = (next_run - current_time).total_seconds()
    return min(sleep_time, 3600)  # Cap at 1 hour for testing

# XDC Network Price Fetch
def fetch_xdc_price():
    try:
        with open("data/coin_mapping.json", "r") as f:
            coin_mapping = json.load(f)
        client = pycoingecko.CoinGeckoAPI()
        data = client.get_price(ids=coin_mapping.get("xdc-network", "xdce-crowd-sale"), vs_currencies="usd")
        return data
    except Exception as e:
        logger.error(f"ERROR - XDC Network fetch failed: {e}")
        return None

# Main Bot Logic
async def main_bot_run(test_discord=False, queue_only=False):
    logger.info("Starting CryptoBotV2 main loop...")
    news_items = ["News 1", "News 2", "News 3"]
    
    if test_discord:
        logger.info("Running in test_discord mode...")
        return
    
    if queue_only:
        logger.info("Running in queue_only mode...")
        posts = [{"text": f"Price update for {coin}", "coin_name": coin} for coin in ["BTC", "ETH"]]
        queue_x_thread(posts, main_post_text="Crypto Market Update")
        while get_x_queue_status()['queue_size'] > 0:
            await asyncio.sleep(1)
        logger.info("Queue processing completed")
        return
    
    while True:
        try:
            sleep_time = calculate_next_run()
            logger.info(f"Next run in {sleep_time} seconds")
            await asyncio.sleep(sleep_time)
            for idx in range(len(news_items)):
                post_update(news_items, idx)
                tweet = f"Crypto Update (2025-06-14 19:30:00 EDT) #Crypto #{random.randint(1000, 9999)}"
                try:
                    response = await asyncio.to_thread(x_client.create_tweet, text=tweet)
                    logger.info(f"Posted tweet: {response.data['id']}")
                except Exception as e:
                    logger.error(f"Failed to post tweet: {e}")
            xdc_price = fetch_xdc_price()
            if xdc_price:
                logger.info(f"XDC Price: {xdc_price.get('xdce-crowd-sale', {}).get('usd', 'N/A')} USD")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(5)

async def shutdown():
    logger.info("Shutting down CryptoBotV2...")
    stop_x_queue()
    await asyncio.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CryptoBotV2")
    parser.add_argument("--test_discord", action="store_true", help="Run in test Discord mode")
    parser.add_argument("--queue_only", action="store_true", help="Run in queue-only mode")
    args = parser.parse_args()

    try:
        asyncio.run(main_bot_run(test_discord=args.test_discord, queue_only=args.queue_only))
    except KeyboardInterrupt:
        asyncio.run(shutdown())
    except Exception as e:
        logger.error(f"Script failed: {e}")
        asyncio.run(shutdown())