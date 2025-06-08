
#!/usr/bin/env python3
"""
Auto-resume worker that continuously monitors and restarts the queue system.
This runs independently to ensure maximum automation.
"""

import time
import os
import logging
from datetime import datetime, timedelta
from modules.x_thread_queue import get_x_queue_status, start_x_queue

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('AutoResume')

def main():
    """Main auto-resume loop."""
    logger.info("🔄 Auto-resume worker started")
    logger.info("🎯 This will automatically restart queue worker and handle rate limits")
    
    consecutive_failures = 0
    max_failures = 5
    
    try:
        while True:
            try:
                # Check if auto-resume is enabled
                if not os.path.exists('auto_resume_enabled.txt'):
                    logger.info("Auto-resume disabled, stopping...")
                    break
                
                # Get queue status
                status = get_x_queue_status()
                
                # Auto-restart if worker stopped
                if not status['worker_running']:
                    logger.info("🚨 Queue worker stopped - auto-restarting...")
                    start_x_queue()
                    time.sleep(5)  # Give it time to start
                    
                    # Verify restart
                    new_status = get_x_queue_status()
                    if new_status['worker_running']:
                        logger.info("✅ Queue worker restarted successfully")
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        logger.error(f"❌ Failed to restart worker (attempt {consecutive_failures})")
                        
                        if consecutive_failures >= max_failures:
                            logger.error("Too many restart failures, forcing recovery...")
                            # Force clear all blocking states
                            os.system('python fix_queue_permanently.py')
                            consecutive_failures = 0
                
                # Log status periodically
                if status['rate_limited']:
                    reset_time = status.get('rate_limit_reset')
                    if reset_time:
                        remaining = (datetime.fromisoformat(reset_time) - datetime.now()).total_seconds() / 60
                        logger.info(f"⏳ Rate limited for {remaining:.1f} more minutes")
                    else:
                        logger.info("⏳ Rate limited - waiting for reset")
                else:
                    logger.info(f"✅ Queue active: {status['post_queue_size']}P {status['thread_queue_size']}T")
                
                # Check every 2 minutes
                time.sleep(120)
                
            except KeyboardInterrupt:
                logger.info("👋 Auto-resume worker stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in auto-resume loop: {e}")
                time.sleep(30)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Critical error in auto-resume worker: {e}")

if __name__ == "__main__":
    main()
