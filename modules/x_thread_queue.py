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
                
                # Get X client for posting
                x_client = get_x_client(posting_only=True)
                if not x_client:
                    logger.error("Failed to get X client - skipping post")
                    _post_queue.task_done()
                    continue

                # Post main tweet
                logger.info(f"Posting main tweet: {main_post[:50]}...")
                main_tweet = x_client.create_tweet(text=main_post)
                main_tweet_id = main_tweet.data['id']
                logger.info(f"Posted main tweet: {main_tweet_id}")

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

                logger.info(f"✅ Successfully posted thread with {len(posts)} replies to X")

            except Exception as api_error:
                logger.error(f"❌ X API error during posting: {api_error}")
                logger.error(f"Failed to post thread with {len(posts)} posts")
                
                # More detailed error handling
                error_str = str(api_error).lower()
                if "rate limit" in error_str or "429" in error_str:
                    logger.warning("Rate limit hit - waiting 2 minutes before retry")
                    time.sleep(120)  # Shorter wait
                elif "auth" in error_str or "401" in error_str or "403" in error_str:
                    logger.error("Authentication error - check X API credentials")
                    logger.error("Try regenerating X API keys and updating secrets")
                elif "duplicate" in error_str:
                    logger.warning("Duplicate content detected - continuing with next post")
                else:
                    logger.error(f"General API error: {api_error}")
                    logger.info("Continuing with queue processing...")
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