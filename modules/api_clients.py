import os
import logging
import tweepy
from pycoingecko import CoinGeckoAPI
from binance.client import Client as BinanceClient
from googleapiclient.discovery import build
import aiohttp

logger = logging.getLogger('CryptoBot')

# Get environment variables for various APIs
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET")

# X/Twitter API credentials
X_API_KEY = os.getenv("X_CONSUMER_KEY")
X_API_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

def get_x_client(posting_only=False, account_number=1):
    """
    Get X API client with dual account support and posting-only mode.

    Args:
        posting_only (bool): If True, optimize for posting only to avoid rate limits
        account_number (int): 1 for primary account, 2 for secondary account

    Returns:
        tweepy.Client or None
    """
    try:
        # Select account credentials
        if account_number == 1:
            consumer_key = os.getenv('X_CONSUMER_KEY')
            consumer_secret = os.getenv('X_CONSUMER_SECRET')
            access_token = os.getenv('X_ACCESS_TOKEN')
            access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
            bearer_token = os.getenv('X_BEARER_TOKEN')
            account_type = "Primary (Verified)"
        else:
            consumer_key = os.getenv('X2_CONSUMER_KEY')
            consumer_secret = os.getenv('X2_CONSUMER_SECRET')
            access_token = os.getenv('X2_ACCESS_TOKEN')
            access_token_secret = os.getenv('X2_ACCESS_TOKEN_SECRET')
            bearer_token = os.getenv('X2_BEARER_TOKEN')
            account_type = "Secondary (Failover)"

        if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
            logger.error(f"Missing X API credentials for account {account_number}")
            if account_number == 2:
                logger.error("Add these secrets for second account:")
                logger.error("  - X2_CONSUMER_KEY")
                logger.error("  - X2_CONSUMER_SECRET")
                logger.error("  - X2_ACCESS_TOKEN")
                logger.error("  - X2_ACCESS_TOKEN_SECRET")
                logger.error("  - X2_BEARER_TOKEN (optional)")
            return None

        if posting_only:
            client = tweepy.Client(
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=False
            )
            logger.info(f"X {account_type} posting-only client initialized (no search capability)")
        else:
            if not bearer_token and not posting_only:
                logger.warning("Bearer token missing for full client; ensure tweet.read scope is included")
            client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=False
            )
            logger.info(f"X {account_type} full client initialized")

        # Validate client setup without making API calls
        try:
            if not consumer_key.startswith(('AAAA', 'BBBB')) and len(consumer_key) < 20:
                logger.warning(f"X {account_type} consumer key format appears invalid")
            
            if not access_token.startswith(('1', '2', '3')) and len(access_token) < 40:
                logger.warning(f"X {account_type} access token format appears invalid")
                
            logger.info(f"X {account_type} client initialized successfully")
            return client
            
        except Exception as validation_error:
            logger.error(f"X {account_type} client validation failed: {validation_error}")
            return None

    except Exception as e:
        logger.error(f"Error initializing X client for account {account_number}: {e}")
        return None

def get_x_client_with_failover(posting_only: bool = False):
    """Get X API client with automatic failover between accounts."""
    # Try primary account first
    client, account_number = get_x_client(posting_only, account_number=1), 1
    if client:
        return client, account_number

    logger.warning("Primary X account failed, trying failover account...")

    # Try failover account
    client, account_number = get_x_client