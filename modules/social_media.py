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

async def fetch_social_metrics(coin_id: str, session: aiohttp.ClientSession, max_retries: int = 5, rate_limit_delay: int = 60) -> Dict[str, str]:
    """
    Fetch social metrics (mentions and sentiment) using the X API with caching and rate limit handling.
    Returns a dictionary with the number of mentions and sentiment (Positive, Negative, or Neutral).
    """
    logger.debug(f"Fetching social metrics for {coin_id}")

    # Load cache and check if data is still valid (within TTL)
    cache = load_social_metrics_cache()
    cached_entry = cache.get(coin_id)
    ttl = 300  # Reduced to 5 minutes TTL for fresher data during debugging
    if cached_entry and "timestamp" in cached_entry and (time.time() - cached_entry["timestamp"]) < ttl:
        logger.debug(f"Using cached social metrics for {coin_id}: {cached_entry['metrics']}")
        return cached_entry["metrics"]

    # Determine the hashtag based on the coin_id
    hashtag_symbol = symbol_map.get(coin_id, coin_id.split('-')[0].upper())
    hashtag = f"#{hashtag_symbol}"
    logger.debug(f"Hashtag for {coin_id}: {hashtag}")

    try:
        x_client = get_x_client()  # Use the client from api_clients.py with wait_on_rate_limit=True
        if not x_client:
            logger.error("X API client not available. Check API credentials in Replit Secrets.")
            result = {"mentions": 0, "sentiment": "N/A"}
            cache[coin_id] = {
                "metrics": result,
                "timestamp": time.time()
            }
            save_social_metrics_cache(cache)
            return result

        query = f"{hashtag} -is:retweet lang:en"
        logger.debug(f"X API query: {query}")

        for attempt in range(max_retries):
            try:
                tweets = x_client.search_recent_tweets(
                    query=query,
                    max_results=100,
                    tweet_fields=["created_at", "text"],
                    user_fields=["public_metrics"],
                    expansions=["author_id"]
                )
                mentions = len(tweets.data) if tweets.data else 0
                logger.debug(f"Fetched {mentions} mentions for {hashtag}")

                # Perform sentiment analysis using VADER
                sentiment = "N/A"
                if mentions > 0:
                    sentiment_scores = []
                    for tweet in tweets.data:
                        scores = sentiment_analyzer.polarity_scores(tweet.text)
                        compound_score = scores['compound']
                        sentiment_scores.append(compound_score)

                    # Calculate average sentiment
                    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                    logger.debug(f"Average sentiment score for {hashtag}: {avg_sentiment}")
                    # Classify sentiment based on compound score
                    if avg_sentiment >= 0.05:
                        sentiment = "Positive"
                    elif avg_sentiment <= -0.05:
                        sentiment = "Negative"
                    else:
                        sentiment = "Neutral"

                result = {"mentions": mentions, "sentiment": sentiment}
                cache[coin_id] = {
                    "metrics": result,
                    "timestamp": time.time()
                }
                save_social_metrics_cache(cache)
                logger.info(f"Social metrics for {coin_id}: {mentions} mentions, {sentiment} sentiment")
                return result

            except tweepy.errors.TooManyRequests as e:
                reset_time = int(e.response.headers.get("x-rate-limit-reset", time.time() + rate_limit_delay))
                wait_time = max(reset_time - int(time.time()), rate_limit_delay)
                logger.warning(f"Rate limit hit for X API on {coin_id}. Waiting {wait_time} seconds before retrying (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(wait_time)
                continue
            except tweepy.Unauthorized as e:
                logger.error(f"X API unauthorized error for {coin_id}: {e}. Check API credentials.")
                break
            except tweepy.Forbidden as e:
                logger.error(f"X API forbidden error for {coin_id}: {e}")
                break
            except tweepy.TweepyException as e:
                logger.error(f"X API error for {coin_id}: {e}")
                break

        # If all retries fail, return default values
        logger.error(f"Failed to fetch social metrics for {coin_id} after {max_retries} attempts.")
        result = {"mentions": 0, "sentiment": "N/A"}
        cache[coin_id] = {
            "metrics": result,
            "timestamp": time.time()
        }
        save_social_metrics_cache(cache)
        return result

    except Exception as e:
        logger.error(f"Unexpected error fetching social metrics for {coin_id}: {e}")
        result = {"mentions": 0, "sentiment": "N/A"}
        cache[coin_id] = {
            "metrics": result,
            "timestamp": time.time()
        }
        save_social_metrics_cache(cache)
        return result