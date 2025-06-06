
#!/usr/bin/env python3
"""
Script to check for duplicate posts and analyze posting patterns
"""

import os
import logging
from datetime import datetime, timedelta
from modules.x_thread_queue import get_x_queue_status

logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    print("🔍 Checking for Duplicate Post Issues...")
    print("=" * 50)
    
    # Check queue status
    try:
        status = get_x_queue_status()
        print(f"📊 Queue Status:")
        print(f"   • Posts queued: {status['post_queue_size']}")
        print(f"   • Threads queued: {status['thread_queue_size']}")
        print(f"   • Worker running: {'✅' if status['worker_running'] else '❌'}")
        print(f"   • Rate limited: {'✅' if status['rate_limited'] else '❌'}")
        print()
    except Exception as e:
        print(f"❌ Could not check queue status: {e}")
        print()
    
    # Check for recent state file
    state_file = "last_thread_state.txt"
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                last_data = f.read().strip().split('|')
                if len(last_data) >= 2:
                    last_hash = last_data[0]
                    last_time_str = last_data[1]
                    last_time = datetime.fromisoformat(last_time_str)
                    
                    time_diff = (datetime.now() - last_time).total_seconds() / 60
                    
                    print(f"📝 Last Posting State:")
                    print(f"   • Content hash: {last_hash}")
                    print(f"   • Posted: {last_time_str}")
                    print(f"   • Time ago: {time_diff:.1f} minutes")
                    
                    if time_diff < 30:
                        print(f"   • Status: ⚠️  Recent post detected")
                    else:
                        print(f"   • Status: ✅ Safe to post")
                    print()
        except Exception as e:
            print(f"❌ Could not read state file: {e}")
            print()
    else:
        print("📝 No previous posting state found")
        print()
    
    # Check for lock file
    import tempfile
    lock_file_path = os.path.join(tempfile.gettempdir(), 'crypto_bot.lock')
    if os.path.exists(lock_file_path):
        try:
            with open(lock_file_path, 'r') as f:
                lock_content = f.read()
                print(f"🔒 Process Lock Found:")
                print(f"   • Lock file: {lock_file_path}")
                print(f"   • Content: {lock_content}")
                print(f"   • Status: ⚠️  Another bot instance may be running")
                print()
        except Exception as e:
            print(f"❌ Could not read lock file: {e}")
            print()
    else:
        print("🔒 No process lock found - safe to run")
        print()
    
    # Check log file for recent duplicates
    log_file = "crypto_bot.log"
    if os.path.exists(log_file):
        print("📋 Checking recent log entries for duplicates...")
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_posts = []
                
                for line in lines[-100:]:  # Check last 100 lines
                    if "Posted main thread tweet:" in line or "Queued X thread" in line:
                        recent_posts.append(line.strip())
                
                if recent_posts:
                    print(f"   • Found {len(recent_posts)} recent posting events:")
                    for post in recent_posts[-5:]:  # Show last 5
                        print(f"     - {post}")
                else:
                    print("   • No recent posting events found")
                print()
        except Exception as e:
            print(f"❌ Could not read log file: {e}")
            print()
    
    print("✅ Duplicate check completed")

if __name__ == "__main__":
    main()
