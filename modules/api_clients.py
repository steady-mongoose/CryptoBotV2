import os
import logging
import tweepy
from pycoingecko import CoinGeckoAPI
from binance.client import Client as BinanceClient  # Import Binance client
from googleapiclient.discovery import build

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
            # Primary account (verified)
            consumer_key = os.getenv('X_CONSUMER_KEY')
            consumer_secret = os.getenv('X_CONSUMER_SECRET')
            access_token = os.getenv('X_ACCESS_TOKEN')
            access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
            bearer_token = os.getenv('X_BEARER_TOKEN')
            account_type = "Primary (Verified)"
        else:
            # Secondary account (non-verified)
            consumer_key = os.getenv('X2_CONSUMER_KEY')
            consumer_secret = os.getenv('X2_CONSUMER_SECRET')
            access_token = os.getenv('X2_ACCESS_TOKEN')
            access_token_secret = os.getenv('X2_ACCESS_TOKEN_SECRET')
            bearer_token = os.getenv('X2_BEARER_TOKEN')
            account_type = "Secondary (Non-verified)"

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
            # Posting-only client - no bearer token to avoid search rate limits
            client = tweepy.Client(
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=False  # Don't wait, fail fast for queue system
            )
            logger.info(f"X {account_type} posting-only client initialized (no search capability)")
        else:
            # Full client with bearer token (use sparingly)
            client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=False
            )
            logger.info(f"X {account_type} full client initialized")

        return client

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
    client, account_number = get_x_client(posting_only, account_number=2), 2
    if client:
        return client, account_number

    logger.error("Both X accounts failed")
    return None, None

def get_coinmarketcap_api_key() -> str:
    """Return the CoinMarketCap API key."""
    key = os.getenv("COINMARKETCAP_API_KEY")
    if not key:
        logger.warning("CoinMarketCap API key not found in environment variables.")
    else:
        logger.debug("CoinMarketCap API key retrieved successfully.")
    return key if key else ""

def get_coingecko_client() -> CoinGeckoAPI:
    """Initialize and return the CoinGecko API client."""
    try:
        client = CoinGeckoAPI()
        logger.debug("CoinGecko API client initialized successfully.")
        return client
    except Exception as e:
        logger.error(f"Error initializing CoinGecko client: {e}")
        raise

def get_newsapi_key() -> str:
    """Return the NewsAPI key."""
    if not NEWSAPI_KEY:
        logger.warning("NewsAPI key not found in environment variables.")
        return ""
    logger.debug("NewsAPI key retrieved successfully.")
    return NEWSAPI_KEY

def get_lunarcrush_api_key() -> str:
    """Return the LunarCrush API key."""
    if not LUNARCRUSH_API_KEY:
        logger.warning("LunarCrush API key not found in environment variables.")
        return ""
    logger.debug("LunarCrush API key retrieved successfully.")
    return LUNARCRUSH_API_KEY

def get_cryptocompare_api_key() -> str:
    """Return the CryptoCompare API key."""
    key = os.getenv("CRYPTOCOMPARE_API_KEY")
    if not key:
        logger.warning("CryptoCompare API key not found in environment variables.")
        return ""
    logger.debug("CryptoCompare API key retrieved successfully.")
    return key

def get_youtube_api_key():
    """Get YouTube API key from environment variables."""
    return os.getenv('YOUTUBE_API_KEY')

def get_coinbase_api_credentials() -> tuple:
    """Return the Coinbase API key and secret."""
    if not COINBASE_API_KEY or not COINBASE_API_SECRET:
        logger.warning("Coinbase API key or secret not found in environment variables.")
        return "", ""
    logger.debug("Coinbase API credentials retrieved successfully.")
    return COINBASE_API_KEY, COINBASE_API_SECRET

def get_binance_client() -> BinanceClient:
    """Initialize and return the Binance API client using API key and secret for authenticated endpoints."""
    try:
        api_key = os.getenv("BINANCE_US_API_KEY")
        api_secret = os.getenv("BINANCE_US_API_SECRET")

        # Log the presence of Binance credentials (without revealing their values)
        logger.debug(f"Binance API Credentials - API Key set: {bool(api_key)}, API Secret set: {bool(api_secret)}")

        if not api_key or not api_secret:
            logger.warning("Binance API key or secret not found in environment variables. Falling back to public client.")
            client = BinanceClient()  # Public client for unauthenticated endpoints
        else:
            client = BinanceClient(api_key, api_secret)
            # Test the client with a simple API call to verify authentication
            client.get_system_status()
            logger.debug("Binance API client initialized successfully with authenticated access.")
            return client

        logger.debug("Binance API public client initialized successfully.")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Binance API client: {e}")
        return None

def get_discord_webhook_url():
    """Get Discord webhook URL from environment variables."""
    return os.getenv('DISCORD_WEBHOOK_URL')

def get_notification_webhook_url():
    """Get notification webhook URL for completion notifications."""
    return os.getenv('NOTIFICATION_WEBHOOK_URL')

def get_notification_config():
    """Get notification configuration for completion alerts."""
    return {
        'discord_webhook': os.getenv('NOTIFICATION_WEBHOOK_URL'),
        'signal_number': os.getenv('SIGNAL_PHONE_NUMBER'),
        'sms_number': os.getenv('SMS_PHONE_NUMBER'),
        'enabled': os.getenv('NOTIFICATIONS_ENABLED', 'false').lower() == 'true'
    }