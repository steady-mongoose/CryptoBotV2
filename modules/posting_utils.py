import logging
import tweepy
import asyncio
import aiohttp
import json
from modules.utils import get_timestamp, get_date
from modules.api_clients import get_discord_webhook_url, get_x_client
import os
from typing import List, Dict, Optional

logger = logging.getLogger('CryptoBot')

def format_tweet(text: str, max_length: int = 280) -> str:
    """Format text for X/Twitter with character limit."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to specified length."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

async def post_to_discord(content: str, attachments: List = None):
    """Post content to Discord webhook."""
    try:
        webhook_url = get_discord_webhook_url()
        if not webhook_url:
            logger.error("Discord webhook URL not found")
            return False
        
        async with aiohttp.ClientSession() as session:
            payload = {"content": content}
            async with session.post(webhook_url, json=payload) as response:
                if response.status == 200:
                    logger.info("Successfully posted to Discord")
                    return True
                else:
                    logger.error(f"Failed to post to Discord: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error posting to Discord: {e}")
        return False

async def post_to_x(content: str, attachments: List = None, reply_to_id: Optional[str] = None) -> Optional[str]:
    """Post content to X/Twitter with rate limiting protection."""
    try:
        client = get_x_client()
        
        # Format content for X's character limit
        formatted_content = format_tweet(content, 280)
        
        # Create tweet parameters
        tweet_params = {"text": formatted_content}
        if reply_to_id:
            tweet_params["in_reply_to_tweet_id"] = reply_to_id
        
        # Post the tweet
        response = client.create_tweet(**tweet_params)
        
        if response.data:
            tweet_id = response.data['id']
            logger.info(f"Successfully posted to X: {tweet_id}")
            return str(tweet_id)
        else:
            logger.error("Failed to get tweet ID from response")
            return None
            
    except tweepy.TooManyRequests as e:
        logger.error(f"X rate limit exceeded: {e}")
        raise
    except tweepy.Forbidden as e:
        logger.error(f"X API forbidden (check account status): {e}")
        raise
    except tweepy.Unauthorized as e:
        logger.error(f"X API unauthorized (check credentials): {e}")
        raise
    except Exception as e:
        logger.error(f"Error posting to X: {e}")
        raise

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

async def post_to_x(message: str, news_items: List[Dict] = None, main_tweet_id: str = None):
    """Post message to X (formerly Twitter) as part of a thread with enhanced rate limiting."""
    max_retries = 3
    base_delay = 300  # 5 minutes initial delay for rate limits
    
    for attempt in range(max_retries):
        try:
            x_client = get_x_client()

            # Validate message length (X has a 280 character limit)
            if len(message) > 280:
                message = message[:277] + "..."
                logger.warning("Tweet message truncated to fit 280 character limit")

            # Post tweet (either main tweet or reply to thread)
            if main_tweet_id:
                # This is a reply in the thread
                response = x_client.create_tweet(text=message, in_reply_to_tweet_id=main_tweet_id)
                tweet_id = response.data['id']
                logger.info(f"Posted reply tweet to thread {main_tweet_id}: {tweet_id}")
            else:
                # This is the main tweet that starts the thread
                response = x_client.create_tweet(text=message)
                tweet_id = response.data['id']
                logger.info(f"Posted main tweet to X: {tweet_id}")

            return tweet_id

        except tweepy.TooManyRequests as e:
            if attempt < max_retries - 1:
                # Calculate exponential backoff delay
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {delay} seconds...")
                await asyncio.sleep(delay)
                continue
            else:
                logger.error(f"X API Rate Limited after {max_retries} attempts: {e}")
                logger.error("FREE TIER: Rate limits exceeded - stopping execution")
                raise

        except tweepy.Unauthorized as e:
            logger.error(f"X API Unauthorized (401): Check your API credentials in Replit Secrets")
            logger.error(f"Ensure your X API keys have write permissions and are not expired")
            logger.error(f"FREE TIER: Verify your app has proper permissions and isn't restricted")
            raise
        except tweepy.Forbidden as e:
            logger.error(f"X API Forbidden (403): {e}")
            logger.error("Your account may be restricted or the app may not have proper permissions")
            logger.error("FREE TIER: Check if you've exceeded monthly tweet limits (1,500 tweets/month)")
            raise
        except tweepy.BadRequest as e:
            logger.error(f"X API Bad Request (400): {e}")
            logger.error("FREE TIER: You may have exceeded your monthly usage limits or have invalid request")
            logger.error("Consider upgrading to a paid plan or reducing bot activity")
            raise
        except Exception as e:
            logger.error(f"Error posting tweet to X: {e}")
            raise

    # This should never be reached due to the raise statements above
    raise Exception("Failed to post after all retry attempts")

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