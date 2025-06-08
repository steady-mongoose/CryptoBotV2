
#!/usr/bin/env python3
"""
Check X posting queue status with specific posting capability assessment.
"""

from modules.x_thread_queue import get_x_queue_status
from datetime import datetime
import tweepy
from modules.api_clients import get_x_client

def check_posting_capability():
    """Check if we can actually post to X right now."""
    print("🔍 Checking X Posting Queue Status...")
    print("=" * 40)
    
    # Get queue status
    status = get_x_queue_status()
    
    print("📊 Queue Status:")
    print(f"   • Posts queued: {status['post_queue_size']}")
    print(f"   • Threads queued: {status['thread_queue_size']}")
    print(f"   • Worker running: {'✅' if status['worker_running'] else '❌'}")
    print(f"   • Rate limited: {'✅' if status['rate_limited'] else '❌'}")
    
    # Test actual posting capability
    print(f"\n🧪 Testing X API Posting Capability...")
    can_post_now = False
    
    try:
        client = get_x_client(posting_only=True)
        if client:
            # Try to get user info (minimal API call)
            user_info = client.get_me()
            print(f"✅ X API accessible: @{user_info.data.username}")
            can_post_now = True
        else:
            print("❌ X API client failed to initialize")
    except tweepy.TooManyRequests:
        print("❌ X API rate limited (429 error)")
        can_post_now = False
    except Exception as e:
        print(f"❌ X API error: {e}")
        can_post_now = False
    
    # Final assessment
    print(f"\n🎯 POSTING CAPABILITY ASSESSMENT:")
    print("=" * 40)
    
    if status['worker_running'] and can_post_now:
        print("✅ CAN POST IMMEDIATELY")
        print("   • Queue worker is running")
        print("   • X API is accessible")
        print("   • Posts will be sent instantly")
    elif status['worker_running'] and not can_post_now:
        print("⏳ CAN QUEUE (WILL POST LATER)")
        print("   • Queue worker is running")
        print("   • X API is rate limited")
        print("   • Posts will queue and auto-send when limit resets")
        if status['rate_limited'] and status.get('rate_limit_reset'):
            print(f"   • Estimated reset: {status['rate_limit_reset']}")
        else:
            print("   • Estimated reset: ~15 minutes")
    elif not status['worker_running'] and not can_post_now:
        print("❌ CANNOT POST RIGHT NOW")
        print("   • Queue worker is not running (likely due to rate limits)")
        print("   • X API is rate limited")
        print("   • Wait 15 minutes, then run 'python fix_queue_permanently.py'")
        print("   • OR posts will auto-resume when rate limit resets")
    elif not status['worker_running']:
        print("❌ CANNOT POST")
        print("   • Queue worker is not running")
        print("   • Run 'python fix_queue_permanently.py' to fix")
    else:
        print("❓ UNKNOWN STATUS")
        print("   • Unclear queue/API state")
    
    print(f"\n📭 Queue is {'empty' if status['post_queue_size'] == 0 and status['thread_queue_size'] == 0 else 'not empty'}")
    
    return can_post_now, status['worker_running']

if __name__ == "__main__":
    check_posting_capability()
