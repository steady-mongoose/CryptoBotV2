import tweepy
from googleapiclient.discovery import build
from pycoingecko import CoinGeckoAPI
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger('CryptoBot')

# Load environment variables from .env file
load_dotenv()

# API credentials from .env
X_API_KEY = os.getenv("X_CONSUMER_KEY")
X_API_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
LUNARCRUSH_API_KEY = os.getenv("LUNARCRUSH_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

def get_x_client() -> tweepy.Client:
    """Initialize and return the X API client using Tweepy 4.15.0 with Twitter API v2."""
    try:
        if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
            raise ValueError("Missing X API credentials")
        return tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
    except Exception as e:
        logger.error(f"Error initializing X client: {e}")
        raise

def get_youtube_client():
    """Initialize and return the YouTube API client."""
    try:
        if not YOUTUBE_API_KEY:
            raise ValueError("YouTube API key not found")
        return build("youtube", "v3", developerKey=YOUTUBE_API_KEY, cache_discovery=False)
    except Exception as e:
        logger.error(f"Error initializing YouTube client: {e}")
        raise

def get_coingecko_client():
    """Initialize and return the CoinGecko API client."""
    try:
        return CoinGeckoAPI()
    except Exception as e:
        logger.error(f"Error initializing CoinGecko client: {e}")
        raise

def get_lunarcrush_api_key():
    """Return the LunarCrush API key."""
    if not LUNARCRUSH_API_KEY:
        logger.error("LunarCrush API key not found")
        return ""
    return LUNARCRUSH_API_KEY

def get_newsapi_key():
    """Return the NewsAPI key."""
    if not NEWSAPI_KEY:
        logger.error("NewsAPI key not found")
        return ""
    return NEWSAPI_KEY

def get_discord_webhook_url():
    """Return the Discord webhook URL."""
    if not DISCORD_WEBHOOK_URL:
        logger.error("Discord webhook URL not found")
        return ""
    return DISCORD_WEBHOOK_URL

def get_coinmarketcap_api_key():
    """Return the CoinMarketCap API key."""
    if not COINMARKETCAP_API_KEY:
        logger.error("CoinMarketCap API key not found")
        return ""
    return COINMARKETCAP_API_KEY

def get_x_api_key():
    """Return the X API key."""
    if not X_API_KEY:
        logger.error("X API key not found")
        return ""
    return X_API_KEY

def get_discord_webhook_url():
    """Return the Discord webhook URL."""
    if not DISCORD_WEBHOOK_URL:
        logger.error("Discord webhook URL not found")
        return ""
    return DISCORD_WEBHOOK_URL

def get_youtube_client():
    """Return the YouTube API client."""
    if not YOUTUBE_API_KEY:
        logger.error("YouTube API key not found")
        return None
    return build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def get_newsapi_key():
    """Return the News API key."""
    if not NEWSAPI_KEY:
        logger.error("News API key not found")
        return ""
    return NEWSAPI_KEY

def get_coinmarketcap_api_key():
    """Return the CoinMarketCap API key."""
    if not COINMARKETCAP_API_KEY:
        logger.error("CoinMarketCap API key not found")
        return ""
    return COINMARKETCAP_API_KEY