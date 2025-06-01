from datetime import datetime
import pytz
import logging
import pyshorteners
import requests

logger = logging.getLogger('CryptoBot')


def get_timestamp() -> str:
    """Return the current UTC timestamp in HH:MM:SS format."""
    utc_now = datetime.now(pytz.UTC)
    return utc_now.strftime("%H:%M:%S")


def get_date() -> str:
    """Return the current UTC date in YYYY-MM-DD format."""
    utc_now = datetime.now(pytz.UTC)
    return utc_now.strftime("%Y-%m-%d")


def shorten_url(url: str) -> str:
    """
    Shorten a URL using TinyURL. If TinyURL fails, fall back to a direct API call.
    Returns the original URL if shortening fails.
    """
    if url == "N/A":
        return url

    # First attempt: Use pyshorteners with TinyURL
    try:
        logger.debug(f"Attempting to shorten URL with pyshorteners: {url}")
        s = pyshorteners.Shortener()
        shortened = s.tinyurl.short(url)
        logger.debug(f"Shortened URL (pyshorteners): {shortened}")
        return shortened
    except Exception as e:
        logger.warning(f"pyshorteners failed to shorten URL {url}: {e}")

    # Fallback: Use TinyURL API directly
    try:
        logger.debug(f"Falling back to TinyURL API for URL: {url}")
        tinyurl_api = f"https://tinyurl.com/api-create.php?url={url}"
        response = requests.get(tinyurl_api, timeout=5)
        response.raise_for_status()
        shortened = response.text
        logger.debug(f"Shortened URL (TinyURL API): {shortened}")
        return shortened
    except Exception as e:
        logger.error(f"Error shortening URL {url} with TinyURL API: {e}")
        return url


def format_tweet(coin, news):
    """
    Format the tweet for a coin update, matching the target post format.
    """
    trend = "📈" if coin["price_change"] >= 0 else "📉"
    shortened_news_url = shorten_url(news['url'])
    shortened_video_url = shorten_url(coin['youtube_video']['url'])
    logger.debug(f"Formatting tweet for {coin['name']}: video data = {coin['youtube_video']}")
    tweet = (
        f"{coin['name'].lower()} ({coin['symbol']}): ${coin['price']:.2f} ({coin['price_change']:.2f}% 24h) {trend}\n"
        f"Predicted: ${coin['predicted_price']:.2f} (Linear regression)\n"
        f"Tx Volume: {coin['transaction_volume']:.2f}M\n"
        f"Top Project: {coin['top_project']}\n"
        f"News: {truncate_text(news['title'], 30)} {shortened_news_url}\n"
        f"Social: {coin['social_metrics']['mentions']} mentions, {coin['social_metrics']['sentiment']}\n"
        f"Video: {truncate_text(coin['youtube_video']['title'], 20)} {shortened_video_url}\n"
        f"#{coin['symbol']}"
    )
    return tweet


def truncate_text(text: str, max_length: int) -> str:
    """
    Truncate text to a specified length, adding '...' if truncated.
    """
    if text == "N/A":
        return text
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."