
#!/usr/bin/env python3
"""
Force process the X posting queue
"""

import time
import logging
from modules.x_thread_queue import x_queue, start_x_queue, get_x_queue_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("🚀 Force processing X posting queue...")
    
    # Check current status
    status = get_x_queue_status()
    print(f"Current status: {status}")
    
    if status['post_queue_size'] == 0 and status['thread_queue_size'] == 0:
        print("❌ No posts in queue to process")
        return
        
    # Stop current worker if running
    if status['worker_running']:
        print("🛑 Stopping current worker...")
        x_queue.stop_worker()
        time.sleep(2)
    
    # Reset rate limit (force override)
    print("🔄 Resetting rate limit state...")
    x_queue.rate_limit_reset_time = None
    
    # Start fresh worker
    print("▶️ Starting fresh queue worker...")
    start_x_queue()
    
    # Wait a moment and check status
    time.sleep(5)
    final_status = get_x_queue_status()
    print(f"Final status: {final_status}")
    
    if final_status['worker_running']:
        print("✅ Queue worker is now processing posts!")
    else:
        print("❌ Failed to start queue worker")

if __name__ == "__main__":
    main()
