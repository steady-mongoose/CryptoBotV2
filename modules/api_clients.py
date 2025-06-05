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

def get_x_client(posting_only: bool = False) -> tweepy.Client:
    """
    Initialize and return the X API client using Tweepy with Twitter API v2 and rate limit handling.
    
    Args:
        posting_only: If True, only initialize for posting (no search/read operations)
    """
    try:
        # Log the presence of credentials (without revealing their values)
        logger.debug(f"X API Credentials - Consumer Key set: {bool(X_API_KEY)}, "
                     f"Consumer Secret set: {bool(X_API_SECRET)}, "
                     f"Access Token set: {bool(X_ACCESS_TOKEN)}, "
                     f"Access Token Secret set: {bool(X_ACCESS_TOKEN_SECRET)}, "
                     f"Bearer Token set: {bool(X_BEARER_TOKEN)}")

        if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_BEARER_TOKEN]):
            raise ValueError("Missing one or more X API credentials (X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_BEARER_TOKEN)")

        # Configure client with conservative rate limit handling for posting-only mode
        wait_on_rate_limit = True if not posting_only else False
        
        client = tweepy.Client(
            bearer_token=X_BEARER_TOKEN,
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=wait_on_rate_limit
        )
        
        if posting_only:
            logger.debug("X API client initialized for POSTING ONLY (bypassing search to avoid 429 errors)")
        else:
            logger.debug("X API client initialized with full functionality and rate limit handling enabled.")

        # Test the client with a simple API call to verify authentication
        try:
            user = client.get_me()
            logger.debug(f"Successfully authenticated with X API. User: {user.data.username}")
        except tweepy.Unauthorized as e:
            logger.error(f"Failed to authenticate with X API: Unauthorized - {e}. Check if credentials are valid and app has 'Read and Write' permissions.")
            return None
        except tweepy.Forbidden as e:
            logger.error(f"Failed to authenticate with X API: Forbidden - {e}. Check if the app or account is restricted.")
            return None
        except tweepy.TooManyRequests as e:
            if posting_only:
                logger.warning(f"Rate limited during auth test - client still usable for posting: {e}")
                return client  # Return client anyway for posting
            else:
                logger.error(f"Rate limited during authentication: {e}")
                return None
        except tweepy.TweepyException as e:
            logger.error(f"Failed to authenticate with X API: {e}")
            return None

        return client
    except Exception as e:
        logger.error(f"Error initializing X client: {e}")
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