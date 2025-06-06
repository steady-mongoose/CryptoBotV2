from datetime import datetime
import logging

logger = logging.getLogger('CryptoBot')

def get_timestamp() -> str:
    """Get the current timestamp in HH:MM:SS format (UTC)."""
    return datetime.utcnow().strftime("%H:%M:%S")

def get_date() -> str:
    """Get the current date in YYYY-MM-DD format (UTC)."""
    return datetime.utcnow().strftime("%Y-%m-%d")

def format_tweet(data: dict) -> str:
    """Format the coin data into a tweet-like string matching the Currency Gator format."""
    try:
        # Determine trend emoji based on price change
        trend = "📈" if data["price_change_24h"] >= 0 else "📉"

        # Format the tweet
        tweet = (
            f"{data['coin_name'].lower()} ({data['coin_symbol']}): ${data['price']:.2f} ({data['price_change_24h']:.2f}% 24h) {trend}\n"
            f"Predicted: ${data['predicted_price']:.2f} (Linear regression)\n"
            f"Tx Volume: {data['tx_volume']:.2f}M\n"
            f"Top Project: {data['top_project']}\n"
            f"{data['hashtag']}\n"
            f"Social: {data['social_metrics']['mentions']} mentions, {data['social_metrics']['sentiment']}\n"
            f"Video: {data['youtube_video']['title']}... {data['youtube_video']['url']}"
        )
        return tweet
    except Exception as e:
        logger.error(f"Error formatting tweet for {data.get('coin_name', 'Unknown')}: {e}")
        return ""