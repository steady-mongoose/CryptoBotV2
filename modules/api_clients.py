import os
import logging
import tweepy
from pycoingecko import CoinGeckoAPI
from binance.client import Client as BinanceClient  # Import Binance client

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

def get_x_client(posting_only=False):
    """
    Initialize and return X (Twitter) API client with proper error handling.

    Args:
        posting_only (bool): If True, client configured for posting only to minimize rate limit exposure
    """
    x_consumer_key = os.getenv('X_CONSUMER_KEY')
    x_consumer_secret = os.getenv('X_CONSUMER_SECRET')
    x_access_token = os.getenv('X_ACCESS_TOKEN')
    x_access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')

    # Check for missing credentials
    missing_creds = []
    if not x_consumer_key:
        missing_creds.append('X_CONSUMER_KEY')
    if not x_consumer_secret:
        missing_creds.append('X_CONSUMER_SECRET')
    if not x_access_token:
        missing_creds.append('X_ACCESS_TOKEN')
    if not x_access_token_secret:
        missing_creds.append('X_ACCESS_TOKEN_SECRET')

    if missing_creds:
        logger.error(f"Missing X API credentials: {', '.join(missing_creds)}")
        logger.error("Please add these secrets in the Secrets tool:")
        for cred in missing_creds:
            logger.error(f"  - {cred}")
        return None

    try:
        client = tweepy.Client(
            consumer_key=x_consumer_key,
            consumer_secret=x_consumer_secret,
            access_token=x_access_token,
            access_token_secret=x_access_token_secret,
            wait_on_rate_limit=False  # Don't wait on rate limits for posting client
        )

        if posting_only:
            logger.info("X API client initialized for POSTING ONLY (search features disabled)")
        else:
            logger.info("X API client initialized successfully")

        return client
    except Exception as e:
        logger.error(f"Failed to create X API client: {str(e)}")
        logger.error("This could be due to:")
        logger.error("  - Invalid API credentials")
        logger.error("  - Network connectivity issues") 
        logger.error("  - X API service issues")
        return None

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

def get_youtube_api_key() -> str:
    """Return the YouTube API key."""
    if not YOUTUBE_API_KEY:
        logger.warning("YouTube API key not found in environment variables.")
        return ""
    logger.debug("YouTube API key retrieved successfully.")
    return YOUTUBE_API_KEY

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