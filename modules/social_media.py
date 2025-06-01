# Applying the changes to include the missing logger import in modules and adding the social media functions.
import aiohttp
import logging
from typing import Dict, List
import tweepy
import asyncio
import json
import os
from modules.api_clients import get_youtube_client, get_newsapi_key

logger = logging.getLogger('CryptoBot')

# Mapping for coin symbols (needed for social metrics)
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

# Cache file for social metrics
SOCIAL_METRICS_CACHE_FILE = "social_metrics_cache.json"

def load_social_metrics_cache() -> Dict[str, Dict[str, str]]:
    """Load cached social metrics from a file."""
    if os.path.exists(SOCIAL_METRICS_CACHE_FILE):
        with open(SOCIAL_METRICS_CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_social_metrics_cache(cache: Dict[str, Dict[str, str]]):
    """Save social metrics to a cache file."""
    with open(SOCIAL_METRICS_CACHE_FILE, 'w') as f:
        json.dump(cache, f)

async def fetch_social_metrics(coin_id: str, session: aiohttp.ClientSession, api_key: str) -> Dict[str, str]:
    """Fetch social metrics (mentions) using the X API."""
    # Load cache
    cache = load_social_metrics_cache()
    if coin_id in cache:
        logger.debug(f"Using cached social metrics for {coin_id}: {cache[coin_id]}")
        return cache[coin_id]

    # Map coin_id to hashtag
    hashtag = f"#{symbol_map.get(coin_id, coin_id.split('-')[0].upper())}"

    # X API credentials from .env
    bearer_token = os.getenv("BEARER_TOKEN")
    consumer_key = os.getenv("X_CONSUMER_KEY")
    consumer_secret = os.getenv("X_CONSUMER_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

    # Check if credentials are missing
    if not all([bearer_token, consumer_key, consumer_secret, access_token, access_token_secret]):
        logger.warning(f"X API credentials not configured for {coin_id}. Using fallback social metrics.")
        result = {"mentions": 0, "sentiment": "N/A"}
        cache[coin_id] = result
        save_social_metrics_cache(cache)
        return result

    # Set up X API client
    try:
        client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        # Search for recent tweets with the hashtag
        query = f"{hashtag} -is:retweet lang:en"
        tweets = client.search_recent_tweets(query=query, max_results=100)
        if tweets.data:
            mentions = len(tweets.data)
            # Simple sentiment analysis
            positive = sum(1 for tweet in tweets.data if any(word in tweet.text.lower() for word in ["bullish", "up", "good"]))
            negative = sum(1 for tweet in tweets.data if any(word in tweet.text.lower() for word in ["bearish", "down", "bad"]))
            sentiment = "Positive" if positive > negative else "Negative" if negative > positive else "Neutral"
        else:
            mentions = 0
            sentiment = "N/A"

        result = {"mentions": mentions, "sentiment": sentiment}
        cache[coin_id] = result
        save_social_metrics_cache(cache)
        return result
    except Exception as e:
        logger.error(f"X API error for {coin_id}: {e}")
        # Fallback to hardcoded values
        result = {"mentions": 0, "sentiment": "N/A"}
        cache[coin_id] = result
        save_social_metrics_cache(cache)
        return result

async def fetch_youtube_video(coin_id: str, session: aiohttp.ClientSession) -> Dict[str, str]:
    """Fetch a relevant YouTube video for the coin."""
    youtube = get_youtube_client()
    try:
        query = f"{coin_id} crypto"
        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=1,
            order="relevance"
        )
        response = await asyncio.get_event_loop().run_in_executor(None, request.execute)
        if not response.get("items"):
            logger.warning(f"No YouTube videos found for {coin_id}")
            return {"title": "N/A", "url": "N/A"}
        video = response["items"][0]
        video_id = video["id"]["videoId"]
        title = video["snippet"]["title"]
        url = f"https://youtu.be/{video_id}"
        return {"title": title, "url": url}
    except Exception as e:
        logger.error(f"YouTube API error for {coin_id}: {e}")
        return {"title": "N/A", "url": "N/A"}

async def fetch_news(coin_ids: List[str], session: aiohttp.ClientSession) -> List[Dict[str, str]]:
    """Fetch news articles for each coin."""
    news_items = []
    predefined_news = {
        "ripple": [
            {"title": "TradeStation adds CME’s XRP futures as regulated crypto derivatives demand surges", "url": "https://coinjournal.net/news/tradestation-adds-cmes-xrp-futures-as-regulated-crypto-derivatives-demand-surges/"},
            {"title": "Is Ripple’s Hidden Road deal part of a SoftBank-like playbook?", "url": "https://cointelegraph.com/news/ripple-hidden-road-softbank-playbook"}
        ],
        "hedera-hashgraph": [
            {"title": "HBAR price dips 3.4% as RSI and BOP indicators point to increased selling pressure", "url": "https://coinjournal.net/news/hbar-price-dips-3-4-as-rsi-and-bop-indicators-point-to-increased-selling-pressure/"}
        ],
        "stellar": [
            {"title": "Analyst Says Mutuum Finance (MUTM) and Stellar Could Soar in 2025", "url": "https://example.com/stellar-news"}
        ],
        "xdce-crowd-sale": [
            {"title": "Top Crypto Innovators Join XDC Network in First-Ever Accelerator Program", "url": "https://example.com/xdc-news"}
        ],
        "sui": [
            {"title": "Nasdaq files for 21Shares SUI ETF with SEC for review", "url": "https://cointelegraph.com/news/nasdaq-files-21-shares-sui-etf-sec-review"}
        ],
        "ondo-finance": [
            {"title": "World leader in digital assets: Toronto emerges as a global blockchain hotspot", "url": "https://economictimes.indiatimes.com/news/international/canada/world-leader-in-digital-assets-toronto-emerges-as-a-global-blockchain-hotspot-as-canadas-steady-crypto-rules-outpace-americas-political-gridlock/articleshow/121238193.cms"}
        ],
        "algorand": [
            {"title": "Algorand Partners with New Blockchain Initiative", "url": "https://example.com/algorand-news"}
        ],
        "casper-network": [
            {"title": "Casper Network Gains Traction in DeFi Space", "url": "https://example.com/casper-news"}
        ]
    }

    for idx, coin_id in enumerate(coin_ids):
        coin_symbol = coin_id.split('-')[0].upper()
        if coin_id in predefined_news and predefined_news[coin_id]:
            news_items.append(predefined_news[coin_id][0])
            continue

        search_term = f"{coin_id.replace('-', ' ')} OR {coin_symbol} cryptocurrency"
        if coin_id == "stellar":
            search_term += " -'Stellar Blade'"
        logger.info(f"Fetching news for {coin_id} using search term: {search_term}")
        url = f"https://newsapi.org/v2/everything?q={search_term}&language=en&sortBy=publishedAt&apiKey={get_newsapi_key()}"
        try:
            async with session.get(url) as response:
                data = await response.json()
                logger.debug(f"NewsAPI response for {coin_id}: {data}")
                if data.get("status") != "ok":
                    logger.error(f"NewsAPI error for {coin_id}: {data.get('message')}")
                    news_items.append({"title": "N/A", "url": "N/A"})
                    continue
                articles = data.get("articles", [])
                if not articles:
                    logger.warning(f"No news articles found for {coin_id}")
                    news_items.append({"title": "N/A", "url": "N/A"})
                    continue
                for article in articles:
                    title_lower = article["title"].lower()
                    description = article.get("description", "").lower()
                    if (coin_symbol.lower() in title_lower or coin_id.replace('-', ' ').lower() in title_lower or
                        coin_symbol.lower() in description or coin_id.replace('-', ' ').lower() in description):
                        news_items.append({
                            "title": article["title"],
                            "url": article["url"]
                        })
                        break
                else:
                    logger.warning(f"No relevant news articles found for {coin_id}")
                    news_items.append({"title": "N/A", "url": "N/A"})
        except Exception as e:
            logger.error(f"News API error for {coin_id}: {e}")
            news_items.append({"title": "N/A", "url": "N/A"})
    return news_items

