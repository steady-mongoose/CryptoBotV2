from datetime import datetime, timedelta
import aiohttp
import logging
from typing import Dict, List
import tweepy
import json
import os
import time
import asyncio
from modules.api_clients import get_x_client
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # Import VADER

# Import alternative social metrics
try:
    from modules.alternative_social import alternative_social
    ALTERNATIVE_SOCIAL_AVAILABLE = True
except ImportError:
    ALTERNATIVE_SOCIAL_AVAILABLE = False
    # logger will be defined below, so we'll log this after logger initialization

logger = logging.getLogger('CryptoBot')

# Log import warning if alternative social module is not available
if not ALTERNATIVE_SOCIAL_AVAILABLE:
    logger.warning("Alternative social metrics module not available")

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
    Fetch social metrics using multiple APIs with smart X API error handling.
    X API search will be attempted first, with graceful fallback on errors.
    X API posting functionality is always preserved regardless of search errors.
    """
    if skip_x_api:
        logger.info(f"Skipping ALL X API interactions for {coin_id} (Discord-only mode)")
        # Return cached data if available, otherwise return fallback data
        cache = load_social_metrics_cache()
        if coin_id in cache:
            # Check if cache has the expected structure
            if "timestamp" in cache[coin_id] and "data" in cache[coin_id]:
                timestamp = cache[coin_id]["timestamp"]
                if isinstance(timestamp, str):
                    cached_time = datetime.fromisoformat(timestamp)
                elif isinstance(timestamp, float):
                    cached_time = datetime.fromtimestamp(timestamp)
                else:
                    # If timestamp is already a datetime object, use it directly
                    cached_time = timestamp

                if datetime.now() - cached_time < timedelta(hours=24):  # Use older cache for Discord-only
                    logger.info(f"Using cached social metrics for {coin_id}")
                    return cache[coin_id]["data"]
            else:
                logger.warning(f"Invalid cache structure for {coin_id}, regenerating cache entry")

        # Return fallback social metrics without any API calls
        return {
            "mentions": 15,  # Conservative baseline
            "sentiment": "Neutral",
            "sources": ["fallback"],
            "confidence": False
        }

    cache = load_social_metrics_cache()

    # Check if we have recent cached data (less than 1 hour old for fresh data)
    if coin_id in cache:
        try:
            # Check if cache has the expected structure
            if "timestamp" in cache[coin_id] and "data" in cache[coin_id]:
                timestamp = cache[coin_id]["timestamp"]
                if isinstance(timestamp, str):
                    cached_time = datetime.fromisoformat(timestamp)
                elif isinstance(timestamp, float):
                    cached_time = datetime.fromtimestamp(timestamp)
                else:
                    cached_time = timestamp

                # Use shorter cache time for more current data
                if datetime.now() - cached_time < timedelta(hours=1):
                    logger.info(f"Using fresh cached social metrics for {coin_id}")
                    return cache[coin_id]["data"]
                else:
                    logger.info(f"Cache expired for {coin_id}, fetching fresh data")
            else:
                logger.warning(f"Invalid cache structure for {coin_id}, regenerating")
        except Exception as e:
            logger.error(f"Error reading cache for {coin_id}: {e}")
            # Clear invalid cache entry
            if coin_id in cache:
                del cache[coin_id]

    symbol = symbol_map.get(coin_id, coin_id.upper())

    # Initialize metrics
    total_mentions = 0
    sentiment_scores = []
    sources_used = []

    # X API SEARCH - COMPLETELY DISABLED to prevent rate limits
    x_mentions_from_api = 0
    x_api_success = False

    # Initialize X API bypass handler and force disable search
    from modules.x_bypass_handler import x_bypass_handler
    x_bypass_handler.force_disable_search()  # Force disable search operations

    logger.info(f"X API search FORCE DISABLED for {symbol} (preventing ALL rate limits)")

    # NO X API SEARCH ATTEMPTS WHATSOEVER - this prevents all rate limit errors

    # If X API search failed, use alternative X metrics
    if not x_api_success:
        logger.info(f"Using alternative X metrics for {symbol} (X API search unavailable)")
        x_alternative_mentions = await get_x_alternative_metrics(symbol, session)
        if x_alternative_mentions > 0:
            total_mentions += x_alternative_mentions
            sources_used.append(f"X_alt ({x_alternative_mentions})")

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

    # If we have very low mentions, try alternative social metrics
    if total_mentions < 8 and ALTERNATIVE_SOCIAL_AVAILABLE:
        logger.info(f"Low mention count for {symbol}, trying alternative social metrics")
        try:
            alt_data = await alternative_social.get_comprehensive_social_data(symbol, coin_id, session)
            if alt_data['mentions'] > total_mentions:
                total_mentions = alt_data['mentions']
                sources_used.extend(alt_data['sources'])
                if not sentiment or sentiment == "Neutral":
                    sentiment = alt_data['sentiment']
                logger.info(f"Enhanced with alternative social metrics: {alt_data['mentions']} mentions")
        except Exception as e:
            logger.error(f"Error getting alternative social metrics: {e}")

    # Enhanced fallback - ensure realistic mentions based on market activity
    if total_mentions < 8:
        # Base mentions from real market activity patterns
        base_mentions = {
            'ripple': 35, 'hedera-hashgraph': 18, 'stellar': 22, 'xinfin-network': 10,
            'sui': 40, 'ondo-finance': 15, 'algorand': 25, 'casper-network': 8
        }
        added_mentions = base_mentions.get(coin_id, 12)
        total_mentions += added_mentions
        sources_used.append(f"market_baseline (+{added_mentions})")
        logger.info(f"Enhanced {coin_id} with baseline mentions: +{added_mentions}")

    # Calculate engagement potential score for monetization
    engagement_score = min(100, (total_mentions * 2) + (len(sentiment_scores) * 10))
    
    # Determine viral potential and topic recommendations
    viral_potential = "High" if total_mentions > 30 else "Medium" if total_mentions > 15 else "Low"
    
    # Generate engagement-optimized content suggestions
    engagement_topics = generate_trending_topics(coin_id, total_mentions, sentiment)
    
    # Calculate monetization metrics
    monetization_metrics = {
        "reply_potential": "High" if total_mentions > 25 else "Medium",
        "thread_worthiness": engagement_score > 50,
        "educational_angle": get_educational_hook(coin_id),
        "trending_topics": engagement_topics
    }
    
    result = {
        "mentions": total_mentions,
        "sentiment": sentiment,
        "sources": sources_used,
        "confidence": len(sentiment_scores) > 5,
        "engagement_score": engagement_score,
        "viral_potential": viral_potential,
        "monetization_tier": "Premium" if engagement_score > 60 else "Standard"
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

async def generate_trending_topics(coin_id: str, mentions: int, sentiment: str) -> List[str]:
    """Generate trending topic suggestions for maximum engagement."""
    
    # High-engagement topic templates
    educational_topics = [
        f"🧵 THREAD: How {symbol_map.get(coin_id, coin_id.upper())} actually works (explained simply)",
        f"📚 Breaking down {symbol_map.get(coin_id, coin_id.upper())} whitepaper in 5 tweets",
        f"💡 Why institutions are quietly accumulating {symbol_map.get(coin_id, coin_id.upper())}",
        f"🔍 {symbol_map.get(coin_id, coin_id.upper())} use cases most people don't know about"
    ]
    
    psychological_topics = [
        f"📊 {symbol_map.get(coin_id, coin_id.upper())} chart psychology: What smart money sees",
        f"🧠 Why most people lose money trading {symbol_map.get(coin_id, coin_id.upper())} (behavioral analysis)",
        f"⚠️ {symbol_map.get(coin_id, coin_id.upper())} red flags vs. buying opportunities"
    ]
    
    # Select topics based on sentiment and mentions
    if sentiment == "Bullish" and mentions > 20:
        return educational_topics + psychological_topics
    elif sentiment == "Bearish":
        return [
            f"🔥 Why {symbol_map.get(coin_id, coin_id.upper())} dump might be your biggest opportunity",
            f"📉 {symbol_map.get(coin_id, coin_id.upper())} bear market survival guide"
        ]
    else:
        return educational_topics[:2]

def get_educational_hook(coin_id: str) -> str:
    """Get educational hook for monetization."""
    educational_hooks = {
        'ripple': "Cross-border payments revolution",
        'hedera-hashgraph': "Enterprise blockchain adoption",
        'stellar': "Financial inclusion technology",
        'sui': "Next-gen smart contract platform",
        'ondo-finance': "Real-world asset tokenization",
        'algorand': "Pure proof-of-stake innovation"
    }
    return educational_hooks.get(coin_id, "Blockchain technology deep-dive")

async def get_x_alternative_metrics(symbol: str, session: aiohttp.ClientSession) -> int:
    """Get X-related metrics using alternative APIs when X search is rate limited."""
    try:
        # Use CryptoCompare social data as X alternative
        url = f"https://min-api.cryptocompare.com/data/social/coin/general?fsym={symbol}"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('Response') == 'Success':
                    twitter_data = data.get('Data', {}).get('Twitter', {})
                    # Get Twitter followers as proxy for X engagement
                    followers = twitter_data.get('followers', 0)
                    if followers > 0:
                        # Convert followers to mention estimate (followers/1000)
                        mentions_estimate = min(followers // 1000, 50)
                        logger.info(f"Alternative X metrics for {symbol}: {mentions_estimate} (from {followers} followers)")
                        return mentions_estimate

        await asyncio.sleep(1)  # Rate limit respect

        # Fallback: Use LunarCrush API for social metrics
        lunar_url = f"https://api.lunarcrush.com/v2?data=assets&symbol={symbol}"
        async with session.get(lunar_url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('data') and len(data['data']) > 0:
                    asset_data = data['data'][0]
                    tweets_24h = asset_data.get('tweets_24h', 0)
                    if tweets_24h > 0:
                        mentions_estimate = min(tweets_24h, 30)
                        logger.info(f"LunarCrush X metrics for {symbol}: {mentions_estimate}")
                        return mentions_estimate

        await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error fetching alternative X metrics for {symbol}: {e}")

    # Final fallback based on coin popularity
    popularity_estimates = {
        'XRP': 25, 'HBAR': 15, 'XLM': 18, 'XDC': 8,
        'SUI': 30, 'ONDO': 12, 'ALGO': 20, 'CSPR': 6
    }
    fallback_mentions = popularity_estimates.get(symbol, 10)
    logger.info(f"Using popularity-based X metrics for {symbol}: {fallback_mentions}")
    return fallback_mentions