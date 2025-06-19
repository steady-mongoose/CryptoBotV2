import logging
import threading
import queue
import asyncio
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from modules.rate_limit_manager import rate_manager

logger = logging.getLogger('CryptoBot')

# Global queue and worker state
_post_queue = queue.Queue()
_worker_thread = None
_worker_running = False

async def verify_post_exists(tweet_id: str) -> dict:
    """Verify that a posted tweet exists and is accessible on the platform."""
    try:
        import aiohttp
        verification_url = f"https://twitter.com/user/status/{tweet_id}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.head(verification_url, timeout=15) as response:
                    if response.status == 200:
                        async with session.get(verification_url, timeout=15) as content_response:
                            if content_response.status == 200:
                                content = await content_response.text()
                                if any(indicator in content.lower() for indicator in ['twitter', 'tweet', 'post', 'status']):
                                    return {
                                        "exists": True,
                                        "content_verified": True,
                                        "status_code": response.status,
                                        "method": "full_verification",
                                        "url": verification_url
                                    }
                                return {
                                    "exists": False,
                                    "content_verified": False,
                                    "error": "Content not found in response",
                                    "status_code": content_response.status,
                                    "method": "content_check_failed"
                                }
                            return {
                                "exists": False,
                                "content_verified": False,
                                "error": f"Content fetch failed: HTTP {content_response.status}",
                                "status_code": content_response.status,
                                "method": "content_fetch_failed"
                            }
                    elif response.status == 401:  # Unauthorized
                        logger.warning(f"401 Unauthorized for tweet {tweet_id}; skipping verification")
                        return {
                            "exists": False,
                            "content_verified": False,
                            "error": "401 Unauthorized",
                            "status_code": response.status,
                            "method": "auth_failed"
                        }
                    else:
                        return {
                            "exists": False,
                            "content_verified": False,
                            "error": f"URL not accessible: HTTP {response.status}",
                            "status_code": response.status,
                            "method": "url_check_failed"
                        }
            except asyncio.TimeoutError:
                return {
                    "exists": False,
                    "content_verified": False,
                    "error": "Verification timeout - X platform may be slow",
                    "status_code": None,
                    "method": "timeout"
                }
    except Exception as e:
        return {
            "exists": False,
            "content_verified": False,
            "error": f"Verification exception: {str(e)}",
            "status_code": None,
            "method": "exception"
        }

async def _queue_worker_async():
    """Asynchronous worker to process queued posts."""
    logger.info("X queue worker thread started successfully")

    while _worker_running:
        try:
            thread_data = await asyncio.to_thread(_post_queue.get, timeout=1.0)
        except queue.Empty:
            await asyncio.sleep(0.1)
            continue

        main_post = thread_data.get('main_post', '')
        posts = thread_data.get('posts', [])
        timestamp = thread_data.get('timestamp', datetime.now())

        logger.info(f"Processing queued thread with {len(posts)} posts from {timestamp}")

        try:
            from modules.api_clients import get_x_client_with_failover, get_notification_webhook_url
            import aiohttp

            logger.info("🔑 Attempting to get X client with failover...")
            x_client, account_num = get_x_client_with_failover(posting_only=True)
            if not x_client:
                logger.error("❌ CRITICAL: Both X accounts failed - check API credentials!")
                logger.error("Primary account variables: X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET")
                logger.error("Failover account variables: X_CONSUMER_KEY_2, X_CONSUMER_SECRET_2, X_ACCESS_TOKEN_2, X_ACCESS_TOKEN_SECRET_2")
                _post_queue.task_done()
                continue

            logger.info(f"✅ Using X account #{account_num}")
            logger.info("✅ X client obtained successfully")

            best_account = rate_manager.get_best_account()
            if not best_account:
                wait_time = rate_manager.get_wait_time()
                logger.warning(f"All accounts rate limited - waiting {wait_time//60} minutes")
                await asyncio.sleep(wait_time)
                continue

            logger.info(f"🐦 POSTING MAIN TWEET: {main_post[:100]}...")
            main_tweet = await asyncio.to_thread(x_client.create_tweet, text=main_post)
            main_tweet_id = main_tweet.data['id']
            rate_manager.record_post(account_num)
            logger.info(f"✅ MAIN TWEET POSTED SUCCESSFULLY: https://twitter.com/user/status/{main_tweet_id}")

            previous_tweet_id = main_tweet_id
            for i, post in enumerate(posts):
                post_text = post.get('text', '')
                coin_name = post.get('coin_name', 'Unknown')
                logger.info(f"Posting reply {i+1} for {coin_name}: {post_text[:50]}...")
                reply_tweet = await asyncio.to_thread(
                    x_client.create_tweet,
                    text=post_text,
                    in_reply_to_tweet_id=previous_tweet_id
                )
                previous_tweet_id = reply_tweet.data['id']
                logger.info(f"Posted reply {i+1}: {previous_tweet_id}")
                await asyncio.sleep(10 if i == 0 else 15 if len(posts) > 5 else 8)

            thread_url = f"https://twitter.com/user/status/{main_tweet_id}"
            verification_status = await verify_post_exists(main_tweet_id)

            webhook_url = get_notification_webhook_url()
            if webhook_url:
                success_message = (
                    f"🎉 X POSTING VERIFIED SUCCESS!\n✅ THREAD URL: {thread_url}\n✅ Posted {len(posts)} replies\n"
                    f"🔍 VERIFIED: {verification_status.get('method')}\n🕒 {datetime.now().strftime('%H:%M:%S')}"
                    if verification_status.get('exists') and verification_status.get('content_verified')
                    else f"❌ X POSTING FAILED VERIFICATION!\n🚫 Could not verify: {verification_status.get('error')}\n"
                    f"📍 Attempted: {thread_url}\n🕒 {datetime.now().strftime('%H:%M:%S')}"
                )
                async with aiohttp.ClientSession() as session:
                    await session.post(webhook_url, json={"content": success_message})

            thread_export = {
                "main_tweet": {
                    "id": main_tweet_id,
                    "url": thread_url,
                    "text": main_post[:100] + "..." if len(main_post) > 100 else main_post,
                    "timestamp": datetime.now().isoformat()
                },
                "replies": [
                    {"text": post.get('text', '')[:100] + "..." if len(post.get('text', '')) > 100 else post.get('text', ''),
                     "coin_name": post.get('coin_name', 'Unknown')}
                    for post in posts
                ],
                "verification": verification_status,
                "workflow_type": "x_queue_posting",
                "posted_at": datetime.now().isoformat()
            }

            print("=" * 60)
            print("🚀 X POSTING WORKFLOW RESULTS")
            print("=" * 60)
            print(f"📍 THREAD URL: {thread_url}")
            print(f"📊 POSTS COUNT: {len(posts)} replies")
            print(f"🔍 VERIFICATION: {'PASSED' if verification_status.get('exists') else 'FAILED'}")
            print("📁 FULL JSON EXPORT:")
            print(json.dumps(thread_export, indent=2))
            print("=" * 60)

            export_filename = f"x_thread_export_{main_tweet_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            try:
                with open(export_filename, 'w') as f:
                    json.dump(thread_export, f, indent=2)
                print(f"💾 Thread data exported to: {export_filename}")
            except Exception as e:
                logger.error(f"Failed to save thread export: {e}")
                print(f"❌ Export save failed: {e}")

            if verification_status.get('exists') and verification_status.get('content_verified', False):
                logger.info(f"✅ X POSTING SUCCESS - VERIFIED: Main tweet: {main_tweet_id}, Replies: {len(posts)}")
                print(f"✅ WORKFLOW RESULT: VERIFIED SUCCESS")
            else:
                logger.error(f"❌ X POSTING FAILED VERIFICATION: {verification_status.get('error', 'Unknown error')}")
                print(f"❌ WORKFLOW RESULT: VERIFICATION FAILED")

        except Exception as api_error:
            logger.error(f"❌ REAL X API ERROR: {api_error}")
            logger.error(f"Failed to post thread with {len(posts)} posts")

            webhook_url = get_notification_webhook_url()
            if webhook_url:
                error_message = f"❌ X POSTING FAILED!\n💥 Error: {str(api_error)[:100]}\n🕒 {datetime.now().strftime('%H:%M:%S')}"
                async with aiohttp.ClientSession() as session:
                    await session.post(webhook_url, json={"content": error_message})

            error_str = str(api_error).lower()
            if "rate limit" in error_str or "429" in error_str:
                logger.error(f"❌ RATE LIMIT HIT ON ACCOUNT {account_num}")
                rate_manager.mark_rate_limited(account_num, duration_minutes=120)
                alternative_client, alt_account_num = get_x_client_with_failover(posting_only=True)
                if alternative_client and alt_account_num != account_num:
                    logger.info(f"🔄 SWITCHING TO ACCOUNT {alt_account_num}")
                    try:
                        main_tweet = await asyncio.to_thread(alternative_client.create_tweet, text=main_post)
                        main_tweet_id = main_tweet.data['id']
                        rate_manager.record_post(alt_account_num)
                        failover_url = f"https://twitter.com/user/status/{main_tweet_id}"
                        logger.info(f"✅ FAILOVER SUCCESS: {failover_url}")
                        previous_tweet_id = main_tweet_id
                        for i, post in enumerate(posts):
                            reply_tweet = await asyncio.to_thread(
                                alternative_client.create_tweet,
                                text=post.get('text', ''),
                                in_reply_to_tweet_id=previous_tweet_id
                            )
                            previous_tweet_id = reply_tweet.data['id']
                            await asyncio.sleep(15)
                        failover_export = {
                            "main_tweet": {"id": main_tweet_id, "url": failover_url},
                            "replies": [{"coin_name": post.get('coin_name', 'Unknown')} for post in posts],
                            "failover_account": alt_account_num,
                            "timestamp": datetime.now().isoformat()
                        }
                        print("=" * 60)
                        print("🔄 X FAILOVER POSTING RESULTS")
                        print("=" * 60)
                        print(f"📍 THREAD URL: {failover_url}")
                        print(f"🔄 FAILOVER ACCOUNT: {alt_account_num}")
                        print("📁 FAILOVER JSON EXPORT:")
                        print(json.dumps(failover_export, indent=2))
                        print("=" * 60)
                    except Exception as failover_error:
                        logger.error(f"❌ FAILOVER ALSO FAILED: {failover_error}")
                else:
                    logger.error("🚫 NO ALTERNATIVE ACCOUNT AVAILABLE")
                    await asyncio.sleep(7200)
            elif "auth" in error_str or "401" in error_str or "403" in error_str:
                logger.error("❌ AUTHENTICATION ERROR - X API credentials invalid!")
                logger.error("🔑 Check your X API secrets: X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET")
                print("❌ X API AUTHENTICATION FAILED - CHECK YOUR SECRETS!")
            elif "duplicate" in error_str:
                logger.warning("Duplicate content detected - continuing with next post")
            else:
                logger.error(f"General API error: {api_error}")
                print(f"❌ X API ERROR: {api_error}")

            _post_queue.task_done()

        except Exception as e:
            logger.error(f"Error in queue worker: {e}")
            await asyncio.sleep(5)

def start_x_queue():
    """Start the X posting queue worker."""
    global _worker_thread, _worker_running
    if not _worker_running:
        _worker_running = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _worker_thread = threading.Thread(target=lambda: loop.run_until_complete(_queue_worker_async()), daemon=True)
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
        'last_post_time': None,
        'next_post_available': True
    }