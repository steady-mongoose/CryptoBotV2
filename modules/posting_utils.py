import logging
import tweepy
import asyncio
import aiohttp
from modules.utils import get_timestamp, get_date, format_tweet, truncate_text
from modules.api_clients import get_discord_webhook_url
import os
from typing import List, Dict

logger = logging.getLogger('CryptoBot')

def get_discord_webhook_url():
    """Get Discord webhook URL from environment variables."""
    return os.getenv('DISCORD_WEBHOOK_URL')

async def post_to_discord(message, news_items):
    """Post the crypto update to Discord using a webhook."""
    webhook_url = get_discord_webhook_url()
    if not webhook_url:
        logger.error("Discord webhook URL not found")
        return

    async with aiohttp.ClientSession() as session:
        try:
            # Handle string message (main post)
            if isinstance(message, str):
                data = {
                    "content": message,
                    "username": "CryptoBot"
                }
                async with session.post(webhook_url, json=data) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Posted main message to Discord")
                    else:
                        logger.error(f"Failed to post main message to Discord: {response.status} - {await response.text()}")
            else:
                logger.error(f"Expected string message, got {type(message)}")
        except Exception as e:
            logger.error(f"Unexpected error in post_to_discord: {e}")
            raise

async def post_to_x(message, news_items):
    """
    Post the crypto update to X, including a main tweet and individual coin replies.
    """
    try:
        from modules.api_clients import get_x_client

        # Get X client
        try:
            x_client = get_x_client()
        except Exception as e:
            logger.error(f"Failed to initialize X client: {e}")
            return

        # Ensure message is a string
        if not isinstance(message, str):
            logger.error(f"Message parameter must be a string, got {type(message)}")
            return

        # Post main tweet
        logger.debug(f"Main tweet content: {message}")
        main_tweet_response = x_client.create_tweet(text=message)
        main_tweet_id = main_tweet_response.data['id']
        logger.info(f"Posted main tweet to X with ID: {main_tweet_id}")

    except tweepy.TweepyException as e:
        logger.error(f"Error posting main tweet to X: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in post_to_x: {e}")

# Engage with influencers
async def engage_with_influencers(coin_name, coin_data, x_client):
    """
    Engage with influencers by liking recent tweets about the coin.
    """
    try:
        # Simulated influencer engagement (replace with actual search logic)
        influencer_tweet_id = "123456789"  # Mocked tweet ID
        influencer_name = f"CryptoInfluencer{coin_name.split()[0]}"
        x_client.like(tweet_id=influencer_tweet_id)  # Use 'like' for tweepy.Client (v2)
        logger.info(f"Liked tweet {influencer_tweet_id} from {influencer_name} about {coin_name}")
    except tweepy.TweepyException as e:
        logger.error(f"Tweepy error engaging with influencers for {coin_name}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error engaging with influencers for {coin_name}: {e}")
        raise