
#!/usr/bin/env python3
"""
Stop all automated processes and clear any scheduled jobs
"""

import os
import logging
import signal
import psutil
from modules.x_thread_queue import stop_x_queue

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('StopAutomation')

def stop_all_automation():
    """Stop all automated processes and clear state files."""
    
    print("🛑 STOPPING ALL AUTOMATED PROCESSES")
    print("=" * 50)
    
    # Stop X queue worker
    try:
        stop_x_queue()
        logger.info("✅ X queue worker stopped")
    except Exception as e:
        logger.warning(f"Queue worker stop error (may not be running): {e}")
    
    # Clear automation state files
    state_files = [
        'auto_resume_enabled.txt',
        'last_thread_state.txt',
        'social_metrics_cache.json'
    ]
    
    for file in state_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                logger.info(f"✅ Cleared state file: {file}")
            except Exception as e:
                logger.error(f"❌ Failed to clear {file}: {e}")
    
    # Kill any running bot processes
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'bot_v2.py' in cmdline and proc.info['pid'] != os.getpid():
                    logger.info(f"🔪 Killing bot process: PID {proc.info['pid']}")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logger.warning(f"Process cleanup warning: {e}")
    
    # Clear lock files
    import tempfile
    lock_file_path = os.path.join(tempfile.gettempdir(), 'crypto_bot.lock')
    if os.path.exists(lock_file_path):
        try:
            os.remove(lock_file_path)
            logger.info("✅ Cleared process lock file")
        except Exception as e:
            logger.error(f"❌ Failed to clear lock file: {e}")
    
    print("\n🛑 ALL AUTOMATION STOPPED")
    print("✅ Manual mode enabled")
    print("✅ No scheduled jobs will run")
    print("✅ Ready for manual diagnostics")

if __name__ == "__main__":
    stop_all_automation()
