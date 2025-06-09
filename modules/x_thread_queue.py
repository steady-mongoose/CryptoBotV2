
import logging
import threading
import time
import queue
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger('CryptoBot')

class XQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        self.last_post_time = None
        self.post_interval = 300  # 5 minutes between posts
        
    def start_worker(self):
        """Start the queue worker thread."""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            logger.info("X queue worker started")
    
    def stop_worker(self):
        """Stop the queue worker thread."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("X queue worker stopped")
    
    def queue_thread(self, posts: List[Dict], main_post_text: str):
        """Queue a thread for posting."""
        thread_data = {
            'main_post': main_post_text,
            'posts': posts,
            'timestamp': datetime.now().isoformat()
        }
        self.queue.put(thread_data)
        logger.info(f"Queued thread with {len(posts)} posts")
    
    def get_queue_status(self) -> Dict:
        """Get current queue status."""
        return {
            'queue_size': self.queue.qsize(),
            'worker_running': self.running,
            'last_post_time': self.last_post_time.isoformat() if self.last_post_time else None,
            'next_post_available': self._can_post_now()
        }
    
    def _can_post_now(self) -> bool:
        """Check if we can post now based on rate limits."""
        if not self.last_post_time:
            return True
        
        time_since_last = datetime.now() - self.last_post_time
        return time_since_last.total_seconds() >= self.post_interval
    
    def _worker(self):
        """Worker thread that processes the queue."""
        while self.running:
            try:
                if not self.queue.empty() and self._can_post_now():
                    thread_data = self.queue.get(timeout=1)
                    self._process_thread(thread_data)
                    self.last_post_time = datetime.now()
                else:
                    time.sleep(30)  # Check every 30 seconds
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in queue worker: {e}")
                time.sleep(60)  # Wait before retrying
    
    def _process_thread(self, thread_data: Dict):
        """Process a queued thread."""
        try:
            from modules.api_clients import get_x_client
            
            x_client = get_x_client(posting_only=True)
            if not x_client:
                logger.error("Could not get X client for queue processing")
                return
            
            # Post main tweet
            main_tweet = x_client.create_tweet(text=thread_data['main_post'])
            logger.info(f"Posted main tweet from queue: {main_tweet.data['id']}")
            
            # Post replies
            previous_tweet_id = main_tweet.data['id']
            for post in thread_data['posts']:
                time.sleep(5)  # Rate limit protection
                reply_tweet = x_client.create_tweet(
                    text=post['text'],
                    in_reply_to_tweet_id=previous_tweet_id
                )
                previous_tweet_id = reply_tweet.data['id']
                logger.info(f"Posted reply for {post['coin_name']}")
                
        except Exception as e:
            logger.error(f"Error processing queued thread: {e}")

# Global queue instance
x_queue = XQueue()

def start_x_queue():
    x_queue.start_worker()

def stop_x_queue():
    x_queue.stop_worker()

def queue_x_thread(posts: List[Dict], main_post_text: str):
    x_queue.queue_thread(posts, main_post_text)

def get_x_queue_status() -> Dict:
    return x_queue.get_queue_status()
