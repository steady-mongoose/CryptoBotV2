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

            # Simulate posting (replace with actual X API calls when ready)
            logger.info(f"Main post: {main_post[:50]}...")

            for i, post in enumerate(posts):
                post_text = post.get('text', '')
                coin_name = post.get('coin_name', 'Unknown')
                logger.info(f"Reply {i+1} for {coin_name}: {post_text[:50]}...")

                # Add delay between posts to avoid rate limits
                time.sleep(2)

            _post_queue.task_done()
            logger.info("Thread processing completed")

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