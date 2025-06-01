import logging
import tweepy
import asyncio
import aiohttp
from modules.utils import get_timestamp, get_date, format_tweet, truncate_text
from modules.api_clients import get_discord_webhook_url

logger = logging.getLogger('CryptoBot')

async def post_to_discord(message, news_items):
    """Post the crypto update to Discord using a webhook."""
    webhook_url = get_discord_webhook_url()
    async with aiohttp.ClientSession() as session:
        try:
            # Main message
            main_message = message
            data = {
                "content": main_message,
                "username": "CryptoBot"
            }
            async with session.post(webhook_url, json=data) as response:
                if 200 <= response.status < 300:
                    logger.info(f"Posted main message to Discord: {main_message}")
                else:
                    logger.error(f"Failed to post main message to Discord: {response.status} - {await response.text()}")

            # Individual coin updates
            for idx, coin in enumerate(formatted_coin_data):
                try:
                    news = news_items[idx % len(news_items)]
                    tweet_text = format_tweet(coin, news)
                    tweet_text += (
                        f"\nSocial: {coin['social_metrics']['mentions']} mentions, {coin['social_metrics']['sentiment']}"
                        f"\nVideo: {truncate_text(coin['youtube_video']['title'], 30)} {coin['youtube_video']['url']}"
                        f"\n#{coin['symbol']}"
                    )
                    data = {
                        "content": tweet_text,
                        "username": "CryptoBot"
                    }
                    async with session.post(webhook_url, json=data) as response:
                        if 200 <= response.status < 300:
                            logger.info(f"Posted update for {coin['name']} to Discord")
                        else:
                            logger.error(f"Failed to post update for {coin['name']} to Discord: {response.status} - {await response.text()}")
                except Exception as e:
                    logger.error(f"Error posting update for {coin['name']} to Discord: {e}")
                    continue
        except Exception as e:
            logger.error(f"Unexpected error in post_to_discord: {e}")
            raise

# Post to X
async def post_to_x(message, news_items):
    """
    Post the crypto update to X, including a main tweet and individual coin replies.
    """
    try:
        # Post main tweet
        main_tweet = message
        logger.debug(f"Main tweet content: {main_tweet}")
        main_tweet_response = x_client.create_tweet(text=main_tweet)
        main_tweet_id = main_tweet_response.data['id']
        logger.info(f"Posted main tweet to X with ID: {main_tweet_id}")

        # Post individual coin updates as replies
        for idx, coin in enumerate(formatted_coin_data):
            try:
                news = news_items[idx % len(news_items)]  # Cycle through news items
                # Format the tweet content
                tweet_text = format_tweet(coin, news)
                # Add social metrics and YouTube video
                tweet_text += (
                    f"\nSocial: {coin['social_metrics']['mentions']} mentions, {coin['social_metrics']['sentiment']}"
                    f"\nVideo: {truncate_text(coin['youtube_video']['title'], 30)} {coin['youtube_video']['url']}"
                    f"\n#{coin['symbol']}"
                )
                tweet_length = len(tweet_text) - len(news['url']) - len(coin['youtube_video']['url']) + 46  # URLs count as 23 chars each
                logger.debug(f"Tweet for {coin['name']}: Length = {tweet_length} characters")
                if tweet_length > 280:
                    logger.warning(f"Tweet for {coin['name']} exceeds 280 characters, truncating")
                    tweet_text = tweet_text[:254] + "..."
                try:
                    response = x_client.create_tweet(
                        text=tweet_text,
                        in_reply_to_tweet_id=main_tweet_id
                    )
                    logger.info(f"Posted update for {coin['name']} to X with ID: {response.data['id']}")
                except tweepy.TweepyException as te:
                    logger.error(f"Tweepy error posting update for {coin['name']} to X: {te}")
                    if isinstance(te, tweepy.RateLimitError):
                        logger.warning("Rate limit exceeded, pausing for 15 minutes")
                        await asyncio.sleep(900)  # Wait 15 minutes
                        response = x_client.create_tweet(
                            text=tweet_text,
                            in_reply_to_tweet_id=main_tweet_id
                        )
                        logger.info(f"Posted update for {coin['name']} to X with ID: {response.data['id']}")
            except Exception as e:
                logger.error(f"Error posting update for {coin['name']}: {e}")
                continue

    except tweepy.TweepyException as e:
        logger.error(f"Error posting main tweet to X: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in post_to_x: {e}")
        raise

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