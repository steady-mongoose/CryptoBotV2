import threading
import queue
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import tweepy
from modules.api_clients import get_x_client

logger = logging.getLogger('CryptoBot')

class XThreadQueue:
    def __init__(self):
        self.post_queue = queue.Queue()
        self.thread_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.client = None
        self.rate_limit_reset_time = None

    def start_worker(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("X posting worker started")

    def stop_worker(self):
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("X posting worker stopped")

    def queue_thread(self, posts: List[Dict], main_post_text: str):
        thread_data = {
            'main_post': main_post_text,
            'posts': posts,
            'timestamp': datetime.now()
        }
        self.thread_queue.put(thread_data)
        logger.info(f"Queued X thread with {len(posts)} posts")

    def _worker(self):
        while self.is_running:
            try:
                if self._is_rate_limited():
                    time.sleep(60)
                    continue

                if not self.client:
                    self.client = get_x_client(posting_only=True)
                    if not self.client:
                        time.sleep(30)
                        continue

                if not self.thread_queue.empty():
                    self._process_thread_queue()
                else:
                    time.sleep(5)

            except tweepy.TooManyRequests:
                self.rate_limit_reset_time = datetime.now() + timedelta(minutes=15)
                time.sleep(60)
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(30)

    def _process_thread_queue(self):
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
                    logger.info(f"Posted thread reply {i+1}")
                    time.sleep(10)
                except Exception as e:
                    logger.error(f"Error posting reply {i+1}: {e}")
                    break

            self.thread_queue.task_done()
        except queue.Empty:
            pass

    def _is_rate_limited(self):
        return self.rate_limit_reset_time and datetime.now() < self.rate_limit_reset_time

    def get_queue_status(self) -> Dict:
        return {
            'thread_queue_size': self.thread_queue.qsize(),
            'worker_running': self.is_running and self.worker_thread and self.worker_thread.is_alive(),
            'rate_limited': self._is_rate_limited()
        }

# Global instance
x_queue = XThreadQueue()

def start_x_queue():
    x_queue.start_worker()

def stop_x_queue():
    x_queue.stop_worker()

def queue_x_thread(posts: List[Dict], main_post_text: str):
    x_queue.queue_thread(posts, main_post_text)

def get_x_queue_status() -> Dict:
    return x_queue.get_queue_status()