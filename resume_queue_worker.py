
#!/usr/bin/env python3
"""
Resume the X posting queue worker if it has stopped.
Checks for existing queued posts and restarts processing.
"""

import logging
import time
from modules.x_thread_queue import start_x_queue, get_x_queue_status

logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    """Resume queue worker if needed."""
    print("🔄 Checking X posting queue worker status...")
    print("=" * 50)
    
    try:
        status = get_x_queue_status()
        
        print(f"📊 Current Status:")
        print(f"   • Posts queued: {status['post_queue_size']}")
        print(f"   • Threads queued: {status['thread_queue_size']}")
        print(f"   • Worker running: {'✅' if status['worker_running'] else '❌'}")
        print(f"   • Rate limited: {'🚫' if status['rate_limited'] else '✅'}")
        
        if status['worker_running']:
            print("\n✅ Queue worker is already running")
            if status['post_queue_size'] > 0 or status['thread_queue_size'] > 0:
                if status['rate_limited']:
                    print("⏳ Posts are queued and waiting for rate limit reset")
                else:
                    print("🚀 Posts are being processed")
            else:
                print("📭 No posts in queue")
        else:
            print("\n🔄 Worker stopped - restarting...")
            start_x_queue()
            time.sleep(3)  # Allow startup
            
            # Verify restart
            new_status = get_x_queue_status()
            if new_status['worker_running']:
                print("✅ Queue worker restarted successfully!")
                if new_status['post_queue_size'] > 0 or new_status['thread_queue_size'] > 0:
                    print("🚀 Resuming processing of queued posts")
                else:
                    print("📭 No posts to process")
            else:
                print("❌ Failed to restart queue worker")
                print("🔑 Check X API credentials may be missing")
                
    except Exception as e:
        print(f"❌ Error checking queue status: {e}")

if __name__ == "__main__":
    main()
