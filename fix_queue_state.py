
#!/usr/bin/env python3
"""
Diagnose and fix X queue state issues
"""

import logging
import time
from modules.x_thread_queue import stop_x_queue, start_x_queue, get_x_queue_status, x_queue

logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    print("🔧 Fixing X Queue State...")
    print("=" * 40)
    
    # Get current status
    try:
        status = get_x_queue_status()
        print(f"📊 Current Status:")
        print(f"   • Posts queued: {status['post_queue_size']}")
        print(f"   • Threads queued: {status['thread_queue_size']}")
        print(f"   • Worker running: {'✅' if status['worker_running'] else '❌'}")
        print(f"   • Rate limited: {'🚫' if status['rate_limited'] else '✅'}")
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        status = {}
    
    # Clear any stuck state
    print("\n🧹 Clearing any stuck queue state...")
    stop_x_queue()
    time.sleep(2)
    
    # Clear rate limit state
    x_queue.rate_limit_reset_time = None
    print("✅ Cleared rate limit state")
    
    # Clear any remaining queue items if needed
    try:
        while not x_queue.post_queue.empty():
            x_queue.post_queue.get_nowait()
            x_queue.post_queue.task_done()
        while not x_queue.thread_queue.empty():
            x_queue.thread_queue.get_nowait()
            x_queue.thread_queue.task_done()
        print("✅ Cleared any stuck queue items")
    except Exception as e:
        print(f"Note: {e}")
    
    # Start fresh worker
    print("\n🚀 Starting fresh queue worker...")
    start_x_queue()
    time.sleep(3)
    
    # Verify new state
    try:
        new_status = get_x_queue_status()
        print(f"✅ New Status:")
        print(f"   • Worker running: {'✅' if new_status['worker_running'] else '❌'}")
        print(f"   • Rate limited: {'✅' if new_status['rate_limited'] else '❌'}")
        
        print("\n🎉 Queue system is now ready!")
        
    except Exception as e:
        print(f"❌ Error verifying new status: {e}")

if __name__ == "__main__":
    main()
