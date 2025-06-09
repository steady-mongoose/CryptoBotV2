import logging
import threading
import time
import queue
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger('CryptoBot')

# Global queue and worker state
_post_queue = queue.Queue()
_worker_thread = None
_worker_running = False

def _queue_worker():
    """Worker thread that processes queued posts."""
    global _worker_running
    
    logger.info("X queue worker thread started successfully")

    while _worker_running:
        try:
            # Get next item from queue with timeout
            try:
                thread_data = _post_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            # Process the thread
            main_post = thread_data.get('main_post', '')
            posts = thread_data.get('posts', [])
            timestamp = thread_data.get('timestamp', datetime.now())

            logger.info(f"Processing queued thread with {len(posts)} posts from {timestamp}")

            try:
                # Import X client here to avoid circular imports
                from modules.api_clients import get_x_client
                
                # Get X client for posting with detailed logging
                logger.info("🔑 Attempting to get X client for posting...")
                x_client = get_x_client(posting_only=True)
                if not x_client:
                    logger.error("❌ CRITICAL: Failed to get X client - check API credentials!")
                    logger.error("Check these environment variables:")
                    logger.error("- X_CONSUMER_KEY")
                    logger.error("- X_CONSUMER_SECRET") 
                    logger.error("- X_ACCESS_TOKEN")
                    logger.error("- X_ACCESS_TOKEN_SECRET")
                    _post_queue.task_done()
                    continue
                
                logger.info("✅ X client obtained successfully")

                # Post main tweet with detailed logging
                logger.info(f"🐦 POSTING MAIN TWEET: {main_post[:100]}...")
                try:
                    main_tweet = x_client.create_tweet(text=main_post)
                    main_tweet_id = main_tweet.data['id']
                    logger.info(f"✅ MAIN TWEET POSTED SUCCESSFULLY: https://twitter.com/user/status/{main_tweet_id}")
                except Exception as tweet_error:
                    logger.error(f"❌ MAIN TWEET FAILED: {tweet_error}")
                    raise

                # Post replies
                previous_tweet_id = main_tweet_id
                for i, post in enumerate(posts):
                    post_text = post.get('text', '')
                    coin_name = post.get('coin_name', 'Unknown')
                    
                    logger.info(f"Posting reply {i+1} for {coin_name}: {post_text[:50]}...")
                    
                    reply_tweet = x_client.create_tweet(
                        text=post_text,
                        in_reply_to_tweet_id=previous_tweet_id
                    )
                    previous_tweet_id = reply_tweet.data['id']
                    logger.info(f"Posted reply {i+1}: {previous_tweet_id}")

                    # Add delay between posts to avoid rate limits
                    time.sleep(5)

                # Send success notification
                from modules.api_clients import get_notification_webhook_url
                import aiohttp
                import asyncio
                
                webhook_url = get_notification_webhook_url()
                if webhook_url:
                    try:
                        success_message = f"🎉 X POSTING SUCCESS!\n✅ Posted main tweet: https://twitter.com/user/status/{main_tweet_id}\n✅ Posted {len(posts)} replies\n🕒 {datetime.now().strftime('%H:%M:%S')}"
                        
                        async def send_notification():
                            async with aiohttp.ClientSession() as session:
                                await session.post(webhook_url, json={"content": success_message})
                        
                        asyncio.run(send_notification())
                    except:
                        pass
                
                logger.info(f"🎉 REAL SUCCESS: Posted to X - Main tweet: {main_tweet_id}, Replies: {len(posts)}")
                print(f"🎉 ACTUAL X POSTING SUCCESS! Main tweet: https://twitter.com/user/status/{main_tweet_id}")

            except Exception as api_error:
                logger.error(f"❌ REAL X API ERROR: {api_error}")
                logger.error(f"Failed to post thread with {len(posts)} posts")
                
                # Send failure notification
                from modules.api_clients import get_notification_webhook_url
                import aiohttp
                import asyncio
                
                webhook_url = get_notification_webhook_url()
                if webhook_url:
                    try:
                        error_message = f"❌ X POSTING FAILED!\n💥 Error: {str(api_error)[:100]}\n🕒 {datetime.now().strftime('%H:%M:%S')}"
                        
                        async def send_notification():
                            async with aiohttp.ClientSession() as session:
                                await session.post(webhook_url, json={"content": error_message})
                        
                        asyncio.run(send_notification())
                    except:
                        pass
                
                # More detailed error handling
                error_str = str(api_error).lower()
                if "rate limit" in error_str or "429" in error_str:
                    logger.warning("Rate limit hit - waiting 2 minutes before retry")
                    time.sleep(120)
                elif "auth" in error_str or "401" in error_str or "403" in error_str:
                    logger.error("❌ AUTHENTICATION ERROR - X API credentials invalid!")
                    logger.error("🔑 Check your X API secrets: X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET")
                    print("❌ X API AUTHENTICATION FAILED - CHECK YOUR SECRETS!")
                elif "duplicate" in error_str:
                    logger.warning("Duplicate content detected - continuing with next post")
                else:
                    logger.error(f"General API error: {api_error}")
                    print(f"❌ X API ERROR: {api_error}")
                # Continue processing other posts

            _post_queue.task_done()

        except Exception as e:
            logger.error(f"Error in queue worker: {e}")
            time.sleep(5)  # Wait before retrying

def start_x_queue():
    """Start the X posting queue worker."""
    global _worker_thread, _worker_running

    if not _worker_running:
        _worker_running = True
        _worker_thread = threading.Thread(target=_queue_worker, daemon=True)
        _worker_thread.start()
        logger.info("X queue worker started")

def stop_x_queue():
    """Stop the X posting queue worker."""
    global _worker_running
    _worker_running = False
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=5)
    logger.info("X queue worker stopped")

def queue_x_thread(posts: List[Dict], main_post_text: str = ""):
    """Queue posts for X posting."""
    try:
        thread_data = {
            'main_post': main_post_text,
            'posts': posts,
            'timestamp': datetime.now()
        }
        _post_queue.put(thread_data)
        logger.info(f"Queued thread with {len(posts)} posts")
    except Exception as e:
        logger.error(f"Error queuing posts: {e}")

def get_x_queue_status() -> Dict:
    """Get current queue status."""
    return {
        'queue_size': _post_queue.qsize(),
        'worker_running': _worker_running,
        'last_post_time': None,  # Could track this if needed
        'next_post_available': True
    }