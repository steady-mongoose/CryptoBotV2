
#!/usr/bin/env python3
"""
Comprehensive fix for all X posting issues
"""

import os
import time
import tempfile
import json
import logging
from datetime import datetime
from modules.x_thread_queue import x_queue, start_x_queue, stop_x_queue, get_x_queue_status

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    print("🔧 COMPREHENSIVE X POSTING FIX")
    print("=" * 50)
    
    # Step 1: Clear ALL blocking states
    print("1️⃣ Clearing all blocking states...")
    
    # Clear duplicate state file
    state_file = "last_thread_state.txt"
    if os.path.exists(state_file):
        os.remove(state_file)
        print(f"   ✅ Removed: {state_file}")
    
    # Clear process lock
    lock_file_path = os.path.join(tempfile.gettempdir(), 'crypto_bot.lock')
    if os.path.exists(lock_file_path):
        os.remove(lock_file_path)
        print(f"   ✅ Removed: {lock_file_path}")
    
    # Clear social metrics cache (may be causing issues)
    cache_file = "social_metrics_cache.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print(f"   ✅ Removed: {cache_file}")
    
    # Step 2: Force reset queue state
    print("\n2️⃣ Force resetting queue state...")
    
    # Stop any existing worker
    try:
        stop_x_queue()
        print("   ✅ Stopped existing queue worker")
        time.sleep(2)
    except Exception as e:
        print(f"   ⚠️  Error stopping worker: {e}")
    
    # Force clear rate limit state
    x_queue.rate_limit_reset_time = None
    x_queue.client = None  # Force reinit
    print("   ✅ Cleared rate limit state")
    print("   ✅ Reset X client")
    
    # Step 3: Start fresh worker
    print("\n3️⃣ Starting fresh queue worker...")
    try:
        start_x_queue()
        time.sleep(3)  # Give it time to initialize
        
        status = get_x_queue_status()
        if status['worker_running']:
            print("   ✅ Queue worker started successfully")
        else:
            print("   ❌ Queue worker failed to start")
            return False
            
    except Exception as e:
        print(f"   ❌ Error starting worker: {e}")
        return False
    
    # Step 4: Verify final state
    print("\n4️⃣ Final verification...")
    final_status = get_x_queue_status()
    
    print(f"   • Worker running: {'✅' if final_status['worker_running'] else '❌'}")
    print(f"   • Rate limited: {'❌' if final_status['rate_limited'] else '✅'}")
    print(f"   • Queue size: {final_status['post_queue_size']} posts, {final_status['thread_queue_size']} threads")
    
    if final_status['worker_running'] and not final_status['rate_limited']:
        print("\n🎉 SUCCESS: All issues fixed!")
        print("🚀 Ready to post to X")
        return True
    else:
        print("\n❌ Some issues remain - check X API credentials")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n💡 Next step: Run 'python bot_v2.py --queue-only' to test posting")
    else:
        print("\n💡 Check your X API credentials in Secrets")
