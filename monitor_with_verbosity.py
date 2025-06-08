
#!/usr/bin/env python3
"""
Real-time verbose monitoring of all bot systems.
"""

import time
import os
import logging
from datetime import datetime
from modules.x_thread_queue import get_x_queue_status

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('Monitor')

def monitor_everything():
    """Monitor all systems with maximum verbosity."""
    print("📊 REAL-TIME SYSTEM MONITOR")
    print("=" * 50)
    print("Press Ctrl+C to stop monitoring")
    print("")
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Get queue status
            try:
                status = get_x_queue_status()
                
                # Create status line
                worker_status = "🟢 RUNNING" if status['worker_running'] else "🔴 STOPPED"
                rate_status = "🟡 LIMITED" if status['rate_limited'] else "🟢 CLEAR"
                queue_info = f"{status['post_queue_size']}P/{status['thread_queue_size']}T"
                
                # Print status line (overwrites previous)
                print(f"\r[{timestamp}] Worker: {worker_status} | Rate: {rate_status} | Queue: {queue_info} | Check #{iteration}", end="", flush=True)
                
                # Detailed logging every 10 checks
                if iteration % 10 == 0:
                    print()  # New line
                    logger.info(f"Detailed status check #{iteration}:")
                    logger.info(f"  Worker running: {status['worker_running']}")
                    logger.info(f"  Rate limited: {status['rate_limited']}")
                    logger.info(f"  Posts queued: {status['post_queue_size']}")
                    logger.info(f"  Threads queued: {status['thread_queue_size']}")
                    if status.get('rate_limit_reset'):
                        logger.info(f"  Rate limit reset: {status['rate_limit_reset']}")
                    
                    # Check for auto-resume file
                    auto_resume = os.path.exists('auto_resume_enabled.txt')
                    logger.info(f"  Auto-resume enabled: {auto_resume}")
                    print()
                
                # Alert on status changes
                if not status['worker_running']:
                    print("\n🚨 ALERT: Worker stopped!")
                    if os.path.exists('auto_resume_enabled.txt'):
                        print("🔄 Auto-resume is enabled - should restart automatically")
                
            except Exception as e:
                print(f"\n❌ Monitor error: {e}")
            
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped by user")

if __name__ == "__main__":
    monitor_everything()
