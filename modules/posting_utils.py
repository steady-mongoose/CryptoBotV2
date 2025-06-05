import logging
import aiohttp
import os
import tweepy
from modules.api_clients import get_x_client

logger = logging.getLogger('CryptoBot')

def get_discord_webhook_url():
    """Get Discord webhook URL from environment variables."""
    return os.getenv('DISCORD_WEBHOOK_URL')

async def post_to_x(message, media_items=None):
    """Post a message to X using posting-only client to avoid rate limit conflicts."""
    x_client = get_x_client(posting_only=True)

    if not x_client:
        logger.error("X client not initialized for posting.")
        return

    try:
        if media_items:
            media_ids = []
            for item in media_items:
                media = await x_client.media_upload(item)
                media_ids.append(media.media_id)
            tweet = await x_client.create_tweet(text=message, media_ids=media_ids)
        else:
            tweet = await x_client.create_tweet(text=message)

        logger.info(f"Successfully posted to X: {message}")
        return tweet
    except tweepy.TooManyRequests as e:
        logger.error(f"Rate limited while posting to X: {e}")
        raise
    except Exception as e:
        logger.error(f"Error posting to X: {e}")
        raise