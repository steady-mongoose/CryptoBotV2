import tweepy
from googleapiclient.discovery import build
from pycoingecko import CoinGeckoAPI
import os
import logging

logger = logging.getLogger('CryptoBot')

def get_x_client() -> tweepy.Client:
    """Initialize and return the X API client using Tweepy 4.15.0 with Twitter API v2."""
    try:
        # Get credentials from environment variables (Replit Secrets)
        x_api_key = os.getenv("X_CONSUMER_KEY")
        x_api_secret = os.getenv("X_CONSUMER_SECRET") 
        x_access_token = os.getenv("X_ACCESS_TOKEN")
        x_access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        
        if not all([x_api_key, x_api_secret, x_access_token, x_access_token_secret]):
            logger.error("Missing X API credentials in environment variables")
            logger.info("Please check your Replit Secrets for: X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET")
            raise ValueError("Missing X API credentials")
            
        return tweepy.Client(
            consumer_key=x_api_key,
            consumer_secret=x_api_secret,
            access_token=x_access_token,
            access_token_secret=x_access_token_secret,
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

