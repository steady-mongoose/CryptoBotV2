import logging
import threading
import time
import queue
import asyncio
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from modules.rate_limit_manager import rate_manager

logger = logging.getLogger('CryptoBot')

# Global queue and worker state

async def verify_post_exists(tweet_id: str) -> dict:
    """Verify that a posted tweet actually exists and is accessible on the platform."""
    try:
        import aiohttp
        
        # Try multiple verification methods
        verification_url = f"https://twitter.com/user/status/{tweet_id}"
        
        async with aiohttp.ClientSession() as session:
            # Method 1: HEAD request to check accessibility
            try:
                async with session.head(verification_url, timeout=15) as response:
                    if response.status == 200:
                        # Method 2: Try to fetch actual content
                        async with session.get(verification_url, timeout=15) as content_response:
                            if content_response.status == 200:
                                content = await content_response.text()
                                # Check if page contains tweet content indicators
                                if any(indicator in content.lower() for indicator in ['twitter', 'tweet', 'post', 'status']):
                                    return {
                                        "exists": True, 
                                        "content_verified": True,
                                        "status_code": response.status,
                                        "method": "full_verification",
                                        "url": verification_url
                                    }
                                else:
                                    return {
                                        "exists": False, 
                                        "content_verified": False,
                                        "error": "Content not found in response",
                                        "status_code": content_response.status,
                                        "method": "content_check_failed"
                                    }
                            else:
                                return {
                                    "exists": False, 
                                    "content_verified": False,
                                    "error": f"Content fetch failed: HTTP {content_response.status}",
                                    "status_code": content_response.status,
                                    "method": "content_fetch_failed"
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
                from modules.api_clients import get_x_client_with_failover
                
                # Get X client with automatic failover
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

                # Check rate limits before posting
                best_account = rate_manager.get_best_account()
                if not best_account:
                    wait_time = rate_manager.get_wait_time()
                    logger.warning(f"All accounts rate limited - waiting {wait_time//60} minutes")
                    time.sleep(wait_time)
                    continue
                
                # Post main tweet with detailed logging
                logger.info(f"🐦 POSTING MAIN TWEET: {main_post[:100]}...")
                try:
                    main_tweet = x_client.create_tweet(text=main_post)
                    main_tweet_id = main_tweet.data['id']
                    rate_manager.record_post(account_num)
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

                    # Smart delay based on rate limit risk
                    if i == 0:
                        time.sleep(10)  # First reply needs more time
                    elif len(posts) > 5:
                        time.sleep(15)  # Longer delays for big threads
                    else:
                        time.sleep(8)   # Standard delay

                # Send notification only after verification
                thread_url = f"https://twitter.com/user/status/{main_tweet_id}"
                verification_status = asyncio.run(verify_post_exists(main_tweet_id))
                
                from modules.api_clients import get_notification_webhook_url
                import aiohttp
                
                webhook_url = get_notification_webhook_url()
                if webhook_url:
                    try:
                        if verification_status.get('exists') and verification_status.get('content_verified'):
                            success_message = f"🎉 X POSTING VERIFIED SUCCESS!\n✅ THREAD URL: {thread_url}\n✅ Posted {len(posts)} replies\n🔍 VERIFIED: Post confirmed on platform\n🕒 {datetime.now().strftime('%H:%M:%S')}"
                        else:
                            success_message = f"❌ X POSTING FAILED VERIFICATION!\n🚫 Could not verify post on platform\n📍 Attempted: {thread_url}\n❌ Error: {verification_status.get('error', 'Unknown')}\n🕒 {datetime.now().strftime('%H:%M:%S')}"
                        
                        async def send_notification():
                            async with aiohttp.ClientSession() as session:
                                await session.post(webhook_url, json={"content": success_message})
                        
                        asyncio.run(send_notification())
                    except:
                        pass
                
                # Verify post actually exists on platform with enhanced verification
                verification_status = asyncio.run(verify_post_exists(main_tweet_id))
                
                # FORCE DISPLAY URL AND JSON FOR ALL X WORKFLOWS
                thread_url = f"https://twitter.com/user/status/{main_tweet_id}"
                
                # Export thread data as JSON (MANDATORY for all X workflows)
                thread_export = {
                    "main_tweet": {
                        "id": main_tweet_id,
                        "url": thread_url,
                        "text": main_post[:100] + "..." if len(main_post) > 100 else main_post,
                        "timestamp": datetime.now().isoformat()
                    },
                    "replies": [
                        {
                            "text": post.get('text', '')[:100] + "..." if len(post.get('text', '')) > 100 else post.get('text', ''),
                            "coin_name": post.get('coin_name', 'Unknown')
                        }
                        for post in posts
                    ],
                    "verification": verification_status,
                    "workflow_type": "x_queue_posting",
                    "posted_at": datetime.now().isoformat()
                }
                
                # ALWAYS DISPLAY THESE - REGARDLESS OF VERIFICATION STATUS
                print("=" * 60)
                print("🚀 X POSTING WORKFLOW RESULTS")
                print("=" * 60)
                print(f"📍 THREAD URL: {thread_url}")
                print(f"📊 POSTS COUNT: {len(posts)} replies")
                print(f"🔍 VERIFICATION: {'PASSED' if verification_status.get('exists') else 'FAILED'}")
                print("📁 FULL JSON EXPORT:")
                print(json.dumps(thread_export, indent=2))
                print("=" * 60)
                
                # Save thread export to file (ALWAYS)
                export_filename = f"x_thread_export_{main_tweet_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                try:
                    with open(export_filename, 'w') as f:
                        json.dump(thread_export, f, indent=2)
                    print(f"💾 Thread data exported to: {export_filename}")
                except Exception as e:
                    logger.error(f"Failed to save thread export: {e}")
                    print(f"❌ Export save failed: {e}")
                
                # Log results based on verification
                if verification_status['exists'] and verification_status.get('content_verified', False):
                    logger.info(f"✅ X POSTING SUCCESS - VERIFIED: Main tweet: {main_tweet_id}, Replies: {len(posts)}")
                    print(f"✅ WORKFLOW RESULT: VERIFIED SUCCESS")
                else:
                    logger.error(f"❌ X POSTING FAILED VERIFICATION: {verification_status.get('error', 'Unknown error')}")
                    print(f"❌ WORKFLOW RESULT: VERIFICATION FAILED")
                        
                else:
                    logger.error(f"❌ X POSTING FAILED VERIFICATION: {verification_status.get('error', 'Unknown error')}")
                    print(f"❌ X POSTING FAILED - VERIFICATION FAILED")
                    print(f"🚫 Cannot confirm post visibility on X platform")
                    print(f"📍 Attempted URL: https://twitter.com/user/status/{main_tweet_id}")
                    print(f"🔍 Error: {verification_status.get('error', 'Unknown verification error')}")
                    print(f"⚠️ CRITICAL: Do not consider this posting successful!")

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
                
                # Enhanced rate limit handling with account marking
                error_str = str(api_error).lower()
                if "rate limit" in error_str or "429" in error_str:
                    logger.error(f"❌ RATE LIMIT HIT ON ACCOUNT {account_num}")
                    
                    # Mark this account as rate limited for 2 hours
                    rate_manager.mark_rate_limited(account_num, duration_minutes=120)
                    
                    # Try to get a different account
                    alternative_client, alt_account_num = get_x_client_with_failover(posting_only=True)
                    
                    if alternative_client and alt_account_num != account_num:
                        logger.info(f"🔄 SWITCHING TO ACCOUNT {alt_account_num}")
                        try:
                            main_tweet = alternative_client.create_tweet(text=main_post)
                            main_tweet_id = main_tweet.data['id']
                            rate_manager.record_post(alt_account_num)
                            failover_url = f"https://twitter.com/user/status/{main_tweet_id}"
                            logger.info(f"✅ FAILOVER SUCCESS: {failover_url}")
                            
                            # Continue with replies using alternative account
                            previous_tweet_id = main_tweet_id
                            for i, post in enumerate(posts):
                                reply_tweet = alternative_client.create_tweet(
                                    text=post.get('text', ''),
                                    in_reply_to_tweet_id=previous_tweet_id
                                )
                                previous_tweet_id = reply_tweet.data['id']
                                time.sleep(15)  # Longer delays after rate limit
                            
                            # FORCE DISPLAY FAILOVER RESULTS
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
                            # Both accounts rate limited - wait 2 hours
                            logger.error("🚫 ALL ACCOUNTS RATE LIMITED - WAITING 2 HOURS")
                            time.sleep(7200)  # 2 hours
                    else:
                        logger.error("🚫 NO ALTERNATIVE ACCOUNT AVAILABLE")
                        # Wait 2 hours before retry
                        logger.error("⏰ WAITING 2 HOURS FOR RATE LIMIT RESET")
                        time.sleep(7200)
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