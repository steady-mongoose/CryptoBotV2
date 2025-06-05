import threading
import queue
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import tweepy
from modules.api_clients import get_x_client
from modules.x_rate_limits import rate_limit_checker

logger = logging.getLogger('CryptoBot')

class XThreadQueue:
    """Thread-based queue system for X posting with rate limit handling."""

    def __init__(self):
        self.post_queue = queue.Queue()
        self.thread_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.client = None
        self.rate_limit_reset_time = None

    def start_worker(self):
        """Start the background worker thread."""
        if self.worker_thread and self.worker_thread.is_alive():
            logger.debug("Worker thread already running")
            return

        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("X posting worker thread started")

    def stop_worker(self):
        """Stop the background worker thread."""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("X posting worker thread stopped")

    def queue_post(self, text: str, in_reply_to_tweet_id: Optional[str] = None, priority: int = 1):
        """Queue a post for X with optional reply-to and priority."""
        post_data = {
            'text': text,
            'in_reply_to_tweet_id': in_reply_to_tweet_id,
            'priority': priority,
            'timestamp': datetime.now(),
            'retry_count': 0
        }
        self.post_queue.put(post_data)
        logger.debug(f"Queued X post: {text[:50]}...")

    def queue_thread(self, posts: List[Dict], main_post_text: str):
        """Queue an entire thread for posting."""
        thread_data = {
            'main_post': main_post_text,
            'posts': posts,
            'timestamp': datetime.now(),
            'retry_count': 0
        }
        self.thread_queue.put(thread_data)
        logger.info(f"Queued X thread with {len(posts)} posts")

    def _worker(self):
        """Background worker that processes the posting queues."""
        logger.debug("X posting worker started")

        while self.is_running:
            try:
                # Check if we're rate limited
                if self._is_rate_limited():
                    logger.debug("Rate limited, waiting...")
                    time.sleep(60)  # Wait 1 minute before checking again
                    continue

                # Initialize client if needed (posting-only to avoid rate limit conflicts)
                if not self.client:
                    # Initialize posting-only client to avoid rate limits
                    logger.debug("Initializing X client for queue worker...")
                    try:
                        self.client = get_x_client(posting_only=True)
                        if not self.client:
                            logger.error("Failed to initialize X posting client - missing credentials or API error")
                            logger.error("Please check X API credentials in Secrets:")
                            logger.error("  - X_CONSUMER_KEY")
                            logger.error("  - X_CONSUMER_SECRET") 
                            logger.error("  - X_ACCESS_TOKEN")
                            logger.error("  - X_ACCESS_TOKEN_SECRET")
                            time.sleep(60)
                            continue
                        logger.info("✅ X queue worker initialized with POSTING-ONLY client")
                        
                        # Test the client by checking user info (minimal API call)
                        try:
                            user_info = self.client.get_me()
                            logger.info(f"✅ X client verified for user: @{user_info.data.username}")
                        except Exception as e:
                            logger.warning(f"X client verification failed: {e}")
                            # Don't fail completely, just log warning
                            
                    except Exception as e:
                        logger.error(f"Error initializing X client: {e}")
                        self.client = None
                        time.sleep(30)
                        continue

                # Process thread queue first (higher priority)
                if not self.thread_queue.empty():
                    self._process_thread_queue()

                # Process individual posts
                elif not self.post_queue.empty():
                    self._process_post_queue()

                else:
                    # No posts to process, wait a bit
                    time.sleep(5)

            except Exception as e:
                logger.error(f"Error in X posting worker: {e}")
                time.sleep(30)  # Wait before retrying

        logger.debug("X posting worker stopped")

    def _process_thread_queue(self):
        """Process a complete thread from the queue."""
        try:
            thread_data = self.thread_queue.get_nowait()

            # Post main tweet
            main_tweet = self.client.create_tweet(text=thread_data['main_post'])
            logger.info(f"Posted main thread tweet: {main_tweet.data['id']}")

            previous_tweet_id = main_tweet.data['id']

            # Post replies
            for i, post_data in enumerate(thread_data['posts']):
                try:
                    reply_tweet = self.client.create_tweet(
                        text=post_data['text'],
                        in_reply_to_tweet_id=previous_tweet_id
                    )
                    previous_tweet_id = reply_tweet.data['id']
                    logger.info(f"Posted thread reply {i+1}/{len(thread_data['posts'])}: {reply_tweet.data['id']}")

                    # Extended wait between posts for free tier (increased for safety)
                    time.sleep(10)  # Increased delay to prevent rate limits

                except tweepy.TooManyRequests:
                    logger.warning("Rate limited during thread posting, requeueing remaining posts")
                    # Requeue remaining posts as individual posts
                    for remaining_post in thread_data['posts'][i:]:
                        self.queue_post(
                            remaining_post['text'],
                            previous_tweet_id,
                            priority=2
                        )
                    break

                except Exception as e:
                    logger.error(f"Error posting thread reply {i+1}: {e}")
                    continue

            self.thread_queue.task_done()

        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Error processing thread queue: {e}")

    def _process_post_queue(self):
        """Process individual posts from the queue."""
        try:
            post_data = self.post_queue.get_nowait()

            # Check retry count
            if post_data['retry_count'] >= 3:
                logger.warning(f"Dropping post after 3 retries: {post_data['text'][:50]}...")
                self.post_queue.task_done()
                return

            # Attempt to post
            tweet = self.client.create_tweet(
                text=post_data['text'],
                in_reply_to_tweet_id=post_data.get('in_reply_to_tweet_id')
            )
            logger.info(f"Posted queued tweet: {tweet.data['id']}")
            self.post_queue.task_done()

        except tweepy.TooManyRequests:
            # Rate limited, requeue with higher retry count
            post_data['retry_count'] += 1
            self.post_queue.put(post_data)
            self._handle_rate_limit()

        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Error posting from queue: {e}")
            post_data['retry_count'] += 1
            if post_data['retry_count'] < 3:
                self.post_queue.put(post_data)
            self.post_queue.task_done()

    def _is_rate_limited(self):
        """Check if we're currently rate limited."""
        if self.rate_limit_reset_time and datetime.now() < self.rate_limit_reset_time:
            return True
        return False

    def _handle_rate_limit(self):
        """Handle rate limit by setting reset time."""
        # Set rate limit reset time to 60 minutes for free tier safety (increased)
        self.rate_limit_reset_time = datetime.now() + timedelta(minutes=60)
        logger.warning(f"Rate limited, will retry after {self.rate_limit_reset_time}")

    def get_queue_status(self) -> Dict:
        """Get current status of the queues."""
        return {
            'post_queue_size': self.post_queue.qsize(),
            'thread_queue_size': self.thread_queue.qsize(),
            'worker_running': self.is_running and self.worker_thread and self.worker_thread.is_alive(),
            'rate_limited': self._is_rate_limited(),
            'rate_limit_reset': self.rate_limit_reset_time.isoformat() if self.rate_limit_reset_time else None
        }

# Global instance
x_queue = XThreadQueue()

def start_x_queue():
    """Start the X posting queue worker."""
    x_queue.start_worker()

def stop_x_queue():
    """Stop the X posting queue worker."""
    x_queue.stop_worker()

def queue_x_post(text: str, in_reply_to_tweet_id: Optional[str] = None, priority: int = 1):
    """Queue a single X post."""
    x_queue.queue_post(text, in_reply_to_tweet_id, priority)

def queue_x_thread(posts: List[Dict], main_post_text: str):
    """Queue a complete X thread."""
    x_queue.queue_thread(posts, main_post_text)

def get_x_queue_status() -> Dict:
    """Get X queue status."""
    return x_queue.get_queue_status()