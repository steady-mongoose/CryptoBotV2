from datetime import datetime, timedelta
import aiohttp
import logging
from typing import Dict
import tweepy
import json
import os
import time
import asyncio
from modules.api_clients import get_x_client
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # Import VADER

logger = logging.getLogger('CryptoBot')

# Updated symbol mapping for correct coin IDs to match hashtags
symbol_map = {
    "ripple": "XRP",
    "hedera-hashgraph": "HBAR",
    "stellar": "XLM",
    "xdce-crowd-sale": "XDC",
    "sui": "SUI",
    "ondo-finance": "ONDO",
    "algorand": "ALGO",
    "casper-network": "CSPR"
}

SOCIAL_METRICS_CACHE_FILE = "social_metrics_cache.json"

# Initialize VADER sentiment analyzer
sentiment_analyzer = SentimentIntensityAnalyzer()

def load_social_metrics_cache() -> Dict[str, Dict]:
    """Load cached social metrics from a file."""
    if os.path.exists(SOCIAL_METRICS_CACHE_FILE):
        try:
            with open(SOCIAL_METRICS_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading social metrics cache: {e}")
            return {}
    return {}

def save_social_metrics_cache(cache: Dict[str, Dict]):
    """Save social metrics to a file."""
    try:
        with open(SOCIAL_METRICS_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=4)
        logger.debug("Social metrics cache saved successfully.")
    except Exception as e:
        logger.error(f"Error saving social metrics cache: {e}")

async def fetch_social_metrics_multi_source(coin_id: str, session: aiohttp.ClientSession, skip_x_api: bool = False) -> Dict[str, any]:
    """
    Fetch social metrics using multiple APIs: X API v2, Reddit API, and sentiment analysis.
    """
    if skip_x_api:
        logger.info(f"Skipping ALL X API interactions for {coin_id} (Discord-only mode)")
        # Return cached data if available, otherwise return fallback data
        cache = load_social_metrics_cache()
        if coin_id in cache:
            timestamp = cache[coin_id]["timestamp"]
            if isinstance(timestamp, str):
                cached_time = datetime.fromisoformat(timestamp)
            else:
                # If timestamp is already a datetime object, use it directly
                cached_time = timestamp
            
            if datetime.now() - cached_time < timedelta(hours=24):  # Use older cache for Discord-only
                logger.info(f"Using cached social metrics for {coin_id}")
                return cache[coin_id]["data"]
        
        # Return fallback social metrics without any API calls
        return {
            "mentions": 15,  # Conservative baseline
            "sentiment": "Neutral",
            "sources": ["fallback"],
            "confidence": False
        }
    
    cache = load_social_metrics_cache()

    # Check if we have recent cached data (less than 2 hours old for more frequent updates)
    if coin_id in cache:
        timestamp = cache[coin_id]["timestamp"]
        if isinstance(timestamp, str):
            cached_time = datetime.fromisoformat(timestamp)
        else:
            # If timestamp is already a datetime object, use it directly
            cached_time = timestamp
        
        if datetime.now() - cached_time < timedelta(hours=2):
            logger.info(f"Using cached social metrics for {coin_id}")
            return cache[coin_id]["data"]

    symbol = symbol_map.get(coin_id, coin_id.upper())

    # Initialize metrics
    total_mentions = 0
    sentiment_scores = []
    sources_used = []

    # Try X API v2 for recent mentions (skip if Discord-only mode)
    if not skip_x_api:
        x_client = None
        try:
            x_client = get_x_client()
            logger.debug(f"X client initialized for {symbol}")
        except Exception as e:
            logger.warning(f"Failed to initialize X client: {e}")
            x_client = None
        
        if x_client:
            try:
                search_query = f"${symbol} OR #{symbol} -is:retweet lang:en"
                logger.debug(f"Searching X for: {search_query}")

                tweets = x_client.search_recent_tweets(
                    query=search_query,
                    max_results=20,  # Free tier limit
                    tweet_fields=['created_at', 'public_metrics']
                )

                if tweets.data:
                    x_mentions = len(tweets.data)
                    total_mentions += x_mentions
                    # Collect tweet text for sentiment
                    tweet_texts = [tweet.text for tweet in tweets.data]
                    sentiment_scores.extend([sentiment_analyzer.polarity_scores(text)['compound'] for text in tweet_texts])
                    sources_used.append(f"X ({x_mentions})")
                    logger.info(f"X API: {x_mentions} mentions for {symbol}")

            except tweepy.TooManyRequests:
                logger.warning(f"X API rate limit exceeded for {symbol}")
            except Exception as e:
                logger.error(f"Error fetching X data for {symbol}: {str(e)}")
    else:
        logger.info(f"Skipping X API calls for {symbol} (Discord-only mode)")

    # Try Reddit API for additional social data
    try:
        reddit_url = f"https://www.reddit.com/r/cryptocurrency/search.json?q={symbol}&sort=new&limit=10"
        async with session.get(reddit_url, headers={'User-Agent': 'CryptoBot/1.0'}) as response:
            if response.status == 200:
                reddit_data = await response.json()
                reddit_posts = reddit_data.get('data', {}).get('children', [])
                reddit_mentions = len(reddit_posts)
                total_mentions += reddit_mentions

                # Analyze post titles for sentiment
                post_titles = [post['data']['title'] for post in reddit_posts]
                sentiment_scores.extend([sentiment_analyzer.polarity_scores(title)['compound'] for title in post_titles])
                sources_used.append(f"Reddit ({reddit_mentions})")
                logger.info(f"Reddit API: {reddit_mentions} mentions for {symbol}")

        await asyncio.sleep(1)  # Respect Reddit rate limits

    except Exception as e:
        logger.error(f"Error fetching Reddit data for {symbol}: {str(e)}")

    # Try CoinGecko developer stats as additional metric
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=false&community_data=true&developer_data=false"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                community_data = data.get('community_data', {})

                # Reddit subscribers as additional mentions metric
                reddit_subscribers = community_data.get('reddit_subscribers', 0)
                if reddit_subscribers > 0:
                    # Scale down to reasonable mention count
                    reddit_metric = min(reddit_subscribers // 1000, 50)
                    total_mentions += reddit_metric
                    sources_used.append(f"CoinGecko community ({reddit_metric})")

                await asyncio.sleep(2)  # Respect CoinGecko rate limits

    except Exception as e:
        logger.error(f"Error fetching CoinGecko community data for {symbol}: {str(e)}")

    # Calculate overall sentiment from all sources
    if sentiment_scores:
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        if avg_sentiment >= 0.1:
            sentiment = "Bullish"
        elif avg_sentiment <= -0.1:
            sentiment = "Bearish"
        else:
            sentiment = "Neutral"

        logger.info(f"Sentiment analysis for {symbol}: {avg_sentiment:.3f} ({sentiment})")
    else:
        sentiment = "Neutral"
        logger.info(f"No sentiment data available for {symbol}, using Neutral")

    # Ensure minimum mentions for realistic appearance
    if total_mentions < 5:
        # Add base mentions from coin popularity
        base_mentions = {
            'ripple': 25, 'hedera-hashgraph': 15, 'stellar': 18, 'xinfin-network': 8,
            'sui': 30, 'ondo-finance': 12, 'algorand': 20, 'casper-network': 6
        }
        total_mentions += base_mentions.get(coin_id, 10)
        sources_used.append("baseline")

    result = {
        "mentions": total_mentions,
        "sentiment": sentiment,
        "sources": sources_used,
        "confidence": len(sentiment_scores) > 5  # High confidence if we have enough data
    }

    logger.info(f"Social metrics for {symbol}: {total_mentions} mentions ({', '.join(sources_used)}), {sentiment} sentiment")

    # Cache the result
    cache[coin_id] = {
        "data": result,
        "timestamp": datetime.now().isoformat()
    }
    save_social_metrics_cache(cache)

    return result

# Maintain backward compatibility
async def fetch_social_metrics(coin_id: str, session: aiohttp.ClientSession, skip_x_api: bool = False) -> Dict[str, any]:
    """Wrapper function for backward compatibility"""
    return await fetch_social_metrics_multi_source(coin_id, session, skip_x_api)