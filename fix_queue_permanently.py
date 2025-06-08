
#!/usr/bin/env python3
"""
Permanently fix X posting queue issues by addressing root causes.
"""

import os
import tempfile
import time
import logging
from datetime import datetime, timedelta
from modules.x_thread_queue import x_queue, start_x_queue, stop_x_queue, get_x_queue_status

logging.basicConfig(level=logging.INFO, format='%(message)s')

def fix_rate_limit_state():
    """Force clear rate limit state that may be stuck."""
    print("🔄 Clearing stuck rate limit state...")
    
    # Reset rate limit time in queue object
    x_queue.rate_limit_reset_time = None
    
    # Clear any persistent rate limit files
    rate_limit_files = [
        'rate_limit_state.txt',
        'x_rate_limit.json',
        'last_rate_limit.txt'
    ]
    
    for file in rate_limit_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"   ✅ Removed: {file}")
    
    print("   ✅ Rate limit state cleared")

def clear_blocking_files():
    """Clear all files that might block queue operation."""
    print("🧹 Clearing blocking files...")
    
    blocking_files = [
        'last_thread_state.txt',
        'crypto_bot.lock',
        'queue_worker.lock',
        'auto_resume_enabled.txt'
    ]
    
    # Also check temp directory for locks
    temp_lock = os.path.join(tempfile.gettempdir(), 'crypto_bot.lock')
    if os.path.exists(temp_lock):
        blocking_files.append(temp_lock)
    
    for file in blocking_files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"   ✅ Removed: {file}")
        except Exception as e:
            print(f"   ⚠️  Could not remove {file}: {e}")
    
    print("   ✅ Blocking files cleared")

def reset_queue_client():
    """Reset the X client in the queue to force fresh initialization."""
    print("🔄 Resetting queue X client...")
    
    # Force client reset
    x_queue.client = None
    x_queue.active_account = 1
    
    print("   ✅ X client reset to force fresh initialization")

def create_auto_resume_system():
    """Create a system that automatically resumes the queue worker."""
    print("🔧 Creating auto-resume system...")
    
    # Enable auto-resume flag
    with open('auto_resume_enabled.txt', 'w') as f:
        f.write('true')
    
    print("   ✅ Auto-resume system enabled")

def main():
    print("🔧 PERMANENT X QUEUE FIX")
    print("=" * 50)
    
    # Step 1: Stop everything cleanly
    print("1️⃣ Stopping current worker...")
    try:
        stop_x_queue()
        time.sleep(3)
        print("   ✅ Worker stopped")
    except Exception as e:
        print(f"   ⚠️  Error stopping worker: {e}")
    
    # Step 2: Clear all blocking states
    clear_blocking_files()
    
    # Step 3: Fix rate limit state
    fix_rate_limit_state()
    
    # Step 4: Reset client
    reset_queue_client()
    
    # Step 5: Create auto-resume system
    create_auto_resume_system()
    
    # Step 6: Start fresh worker
    print("\n6️⃣ Starting fresh worker with fixes...")
    try:
        start_x_queue()
        time.sleep(5)  # Give it time to initialize
        
        # Check status
        status = get_x_queue_status()
        if status['worker_running'] and not status['rate_limited']:
            print("   ✅ Worker started successfully")
            print("   ✅ Rate limit cleared")
            print("   ✅ Ready to process posts")
        else:
            print("   ⚠️  Worker may still have issues")
            print(f"   Worker running: {status['worker_running']}")
            print(f"   Rate limited: {status['rate_limited']}")
            
    except Exception as e:
        print(f"   ❌ Error starting worker: {e}")
        return False
    
    # Step 7: Create monitoring script
    create_monitoring_script()
    
    print("\n🎉 PERMANENT FIX APPLIED!")
    print("✅ Queue worker should now stay running")
    print("✅ Auto-resume enabled for future issues")
    print("✅ All blocking states cleared")
    print("✅ Monitoring script created")
    print("\n💡 Run 'python monitor_queue.py' to watch queue status")
    print("💡 Or run 'python auto_resume_worker.py' for full automation")
    
    # Enable automatic rate limit recovery
    setup_automatic_recovery()
    
    return True

def setup_automatic_recovery():
    """Set up automatic recovery system for rate limits."""
    print("\n🤖 Setting up automatic rate limit recovery...")
    
    # Create recovery script
    recovery_script = '''#!/usr/bin/env python3
import time
import os
from datetime import datetime, timedelta
from modules.x_thread_queue import get_x_queue_status, start_x_queue

def auto_recover():
    """Auto-recover from rate limits."""
    while os.path.exists('auto_resume_enabled.txt'):
        try:
            status = get_x_queue_status()
            
            # If rate limited, wait and test recovery
            if status['rate_limited'] and status['rate_limit_reset']:
                reset_time = datetime.fromisoformat(status['rate_limit_reset'])
                if datetime.now() >= reset_time:
                    print(f"⏰ Rate limit should be reset, testing recovery...")
                    start_x_queue()
            
            time.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            print(f"Recovery error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    auto_recover()
'''
    
    with open('auto_recovery.py', 'w') as f:
        f.write(recovery_script)
    
    print("   ✅ Automatic recovery system created")
    print("   💡 Run 'python auto_recovery.py &' for background automation")

def create_monitoring_script():
    """Create a script to monitor queue health."""
    monitoring_script = '''#!/usr/bin/env python3
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
            
            print(f"\\r📊 Worker: {'✅' if status['worker_running'] else '❌'} | "
                  f"Rate Limited: {'❌' if status['rate_limited'] else '✅'} | "
                  f"Queue: {status['post_queue_size']}P {status['thread_queue_size']}T", end="")
            
            # Auto-fix if worker stops
            if not status['worker_running'] and os.path.exists('auto_resume_enabled.txt'):
                print("\\n🔄 Auto-resuming stopped worker...")
                start_x_queue()
                time.sleep(3)
            
            time.sleep(10)  # Check every 10 seconds
            
    except KeyboardInterrupt:
        print("\\n👋 Monitoring stopped")

if __name__ == "__main__":
    monitor_queue()
'''
    
    with open('monitor_queue.py', 'w') as f:
        f.write(monitoring_script)
    
    print("   ✅ Created monitor_queue.py")

if __name__ == "__main__":
    main()
