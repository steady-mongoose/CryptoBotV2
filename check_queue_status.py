
#!/usr/bin/env python3
"""
Script to check the status of the X posting queue.
"""

import logging
from modules.x_thread_queue import get_x_queue_status

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    """Check and display X queue status."""
    print("🔍 Checking X Posting Queue Status...")
    print("=" * 40)
    
    try:
        status = get_x_queue_status()
        
        print(f"📊 Queue Status:")
        print(f"   • Posts queued: {status['post_queue_size']}")
        print(f"   • Threads queued: {status['thread_queue_size']}")
        print(f"   • Worker running: {'✅' if status['worker_running'] else '❌'}")
        print(f"   • Rate limited: {'🚫' if status['rate_limited'] else '✅'}")
        
        if status['rate_limit_reset']:
            print(f"   • Rate limit resets: {status['rate_limit_reset']}")
        
        print("\n" + "=" * 40)
        
        if status['post_queue_size'] > 0 or status['thread_queue_size'] > 0:
            print("📝 Posts are queued and will be posted automatically")
            if status['rate_limited']:
                print("⏳ Waiting for rate limit to reset...")
            else:
                print("🚀 Queue is being processed")
        else:
            print("✅ No posts in queue")
            
    except Exception as e:
        print(f"❌ Error checking queue status: {e}")

#!/usr/bin/env python3

import logging
from modules.x_thread_queue import get_x_queue_status

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('QueueChecker')

def main():
    """Check the current status of the X posting queue."""
    print("🔍 Checking X posting queue status...")
    
    try:
        status = get_x_queue_status()
        
        print(f"📊 Queue Status:")
        print(f"   Posts in queue: {status['post_queue_size']}")
        print(f"   Threads in queue: {status['thread_queue_size']}")
        print(f"   Worker running: {status['worker_running']}")
        print(f"   Rate limited: {status['rate_limited']}")
        
        if status['rate_limit_reset']:
            print(f"   Rate limit reset: {status['rate_limit_reset']}")
        
        if status['post_queue_size'] > 0 or status['thread_queue_size'] > 0:
            print("✅ Posts are queued for processing")
        else:
            print("ℹ️  No posts currently in queue")
            
        if status['worker_running']:
            print("✅ Background worker is processing posts")
        else:
            print("⚠️  Background worker is not running")
            
    except Exception as e:
        logger.error(f"Error checking queue status: {e}")
        print("❌ Failed to check queue status")

if __name__ == "__main__":
    main()
