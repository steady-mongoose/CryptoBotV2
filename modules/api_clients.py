import os
import logging
import tweepy
from pycoingecko import CoinGeckoAPI

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

def get_x_client() -> tweepy.Client:
    """Initialize and return the X API client using Tweepy with Twitter API v2 and rate limit handling."""
    try:
        if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_BEARER_TOKEN]):
            raise ValueError("Missing one or more X API credentials (X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_BEARER_TOKEN)")

        client = tweepy.Client(
            bearer_token=X_BEARER_TOKEN,
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True  # Enable automatic rate limit handling
        )
        logger.debug("X API client initialized successfully with rate limit handling enabled.")
        return client
    except Exception as e:
        logger.error(f"Error initializing X client: {e}")
        raise

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