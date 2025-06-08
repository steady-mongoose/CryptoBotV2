#!/usr/bin/env python3
"""
Monitor X queue health and auto-fix issues.
"""

import time
import os
from modules.x_thread_queue import get_x_queue_status, start_x_queue

def monitor_queue():
    """Monitor queue and auto-fix issues."""
    print("📊 Queue Health Monitor - Ctrl+C to stop")
    print("=" * 40)
    
    try:
        while True:
            status = get_x_queue_status()
            
            print(f"\r📊 Worker: {'✅' if status['worker_running'] else '❌'} | "
                  f"Rate Limited: {'❌' if status['rate_limited'] else '✅'} | "
                  f"Queue: {status['post_queue_size']}P {status['thread_queue_size']}T", end="")
            
            # Auto-fix if worker stops
            if not status['worker_running'] and os.path.exists('auto_resume_enabled.txt'):
                print("\n🔄 Auto-resuming stopped worker...")
                start_x_queue()
                time.sleep(3)
            
            time.sleep(10)  # Check every 10 seconds
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")

if __name__ == "__main__":
    monitor_queue()
