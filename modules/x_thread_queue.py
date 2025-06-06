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
        """Queue an entire thread for posting with relaxed duplicate prevention."""
        import hashlib
        import os
        
        # Generate content hash for duplicate detection
        content_hash = hashlib.md5(main_post_text.encode()).hexdigest()[:8]
        current_time = datetime.now()
        
        # Create persistent state file for duplicate tracking
        state_file = "last_thread_state.txt"
        
        # RELAXED duplicate checking - only block obvious spam
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    last_data = f.read().strip().split('|')
                    if len(last_data) >= 2:
                        last_hash = last_data[0]
                        last_time_str = last_data[1]
                        last_time = datetime.fromisoformat(last_time_str)
                        
                        time_diff = (current_time - last_time).total_seconds() / 60  # minutes
                        
                        # Only block if EXACT same content within 10 minutes (much more relaxed)
                        if last_hash == content_hash and time_diff < 10:
                            logger.warning(f"🚫 EXACT DUPLICATE: Same content posted {time_diff:.1f} minutes ago")
                            logger.warning("This appears to be genuine spam - blocking")
                            return False
                        else:
                            logger.info(f"✅ Content okay: {time_diff:.1f} minutes since last post")
                            
            except Exception as e:
                logger.debug(f"Could not read state file: {e}")
        
        # Always allow queuing unless it's obvious spam
        logger.info(f"✅ Queuing thread - duplicate check passed")
        
        # Save current posting state for future reference only
        try:
            with open(state_file, 'w') as f:
                f.write(f"{content_hash}|{current_time.isoformat()}")
        except Exception as e:
            logger.warning(f"Could not save state file: {e}")
            
        thread_data = {
            'main_post': main_post_text,
            'posts': posts,
            'timestamp': current_time,
            'retry_count': 0,
            'content_hash': content_hash
        }
        self.thread_queue.put(thread_data)
        logger.info(f"✅ Queued X thread with {len(posts)} posts (hash: {content_hash})")
        logger.info(f"Queue size now: {self.thread_queue.qsize()}")
        return True

    def _worker(self):
        """Background worker that processes the posting queues."""
        logger.debug("X posting worker started")

        while self.is_running:
            try:
                # Check if we're rate limited
                if self._is_rate_limited():
                    remaining_time = (self.rate_limit_reset_time - datetime.now()).total_seconds()
                    if remaining_time > 0:
                        logger.info(f"Rate limited for {remaining_time/60:.1f} more minutes. Queue has {self.post_queue.qsize()} posts + {self.thread_queue.qsize()} threads waiting.")
                        time.sleep(60)  # Wait 1 minute before checking again
                        continue
                    else:
                        # Rate limit has expired, clear it
                        logger.info("Rate limit window has reset, resuming posting...")
                        self.rate_limit_reset_time = None

                # Initialize client if needed (posting-only to avoid rate limit conflicts)
                if not self.client:
                    # Initialize posting-only client to avoid rate limits
                    logger.debug("Initializing X client for queue worker...")
                    try:
                        self.client = get_x_client(posting_only=True)
                        if not self.client:
                            logger.error("❌ CRITICAL: Failed to initialize X posting client")
                            logger.error("🔑 Missing or invalid X API credentials in Secrets:")
                            logger.error("  - X_CONSUMER_KEY")
                            logger.error("  - X_CONSUMER_SECRET") 
                            logger.error("  - X_ACCESS_TOKEN")
                            logger.error("  - X_ACCESS_TOKEN_SECRET")
                            logger.error("🚨 X posting will not work until credentials are fixed")
                            logger.error("⏸️  Queue worker will retry in 2 minutes...")
                            time.sleep(120)  # Wait longer for credential fixes
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
            logger.info(f"🧵 Processing thread with {len(thread_data['posts'])} posts")

            # Post main tweet
            main_tweet = self.client.create_tweet(text=thread_data['main_post'])
            logger.info(f"✅ Posted main thread tweet: {main_tweet.data['id']}")

            previous_tweet_id = main_tweet.data['id']

            # Post replies with enhanced error handling
            for i, post_data in enumerate(thread_data['posts']):
                try:
                    reply_tweet = self.client.create_tweet(
                        text=post_data['text'],
                        in_reply_to_tweet_id=previous_tweet_id
                    )
                    previous_tweet_id = reply_tweet.data['id']
                    logger.info(f"✅ Posted thread reply {i+1}/{len(thread_data['posts'])}: {reply_tweet.data['id']}")

                    # Extended wait between posts for free tier safety
                    time.sleep(12)  # Increased delay to prevent rate limits

                except tweepy.TooManyRequests as e:
                    logger.warning(f"Rate limited during thread posting at reply {i+1}")
                    self._handle_rate_limit()
                    # Mark thread as partially completed and stop
                    logger.info(f"Thread partially posted: {i} of {len(thread_data['posts'])} replies completed")
                    break

                except Exception as e:
                    logger.error(f"Error posting thread reply {i+1}: {e}")
                    # Continue with next post instead of failing entire thread
                    continue

            self.thread_queue.task_done()
            logger.info("🧵 Thread processing completed")

        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Error processing thread queue: {e}")
            # Ensure task is marked done even on error
            try:
                self.thread_queue.task_done()
            except:
                pass

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
        # Set rate limit reset time to 15 minutes (standard X API reset window)
        self.rate_limit_reset_time = datetime.now() + timedelta(minutes=15)
        logger.warning(f"Rate limited, will retry after {self.rate_limit_reset_time}")
        logger.info("Posts will remain queued and automatically process when rate limit resets")

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