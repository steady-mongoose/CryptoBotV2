
#!/usr/bin/env python3
"""
Fix duplicate run issues and prevent multiple bot instances.
"""

import os
import sys
import fcntl
import tempfile
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DuplicateFixer')

def check_and_clear_locks():
    """Check for existing locks and clear them if safe."""
    lock_file_path = os.path.join(tempfile.gettempdir(), 'crypto_bot.lock')
    
    print("🔍 Checking for duplicate run issues...")
    
    if os.path.exists(lock_file_path):
        try:
            # Try to read the lock file
            with open(lock_file_path, 'r') as f:
                content = f.read()
            
            print(f"📄 Found existing lock file:")
            print(f"   Content: {content}")
            
            # Check if the process is still running
            try:
                lines = content.strip().split('\n')
                if len(lines) >= 2 and 'PID:' in lines[1]:
                    pid = int(lines[1].split('PID:')[1].strip())
                    
                    # Check if process is still running
                    try:
                        os.kill(pid, 0)  # Signal 0 checks if process exists
                        print(f"⚠️  Process {pid} is still running")
                        print("   Wait for it to complete or manually kill it")
                        return False
                    except OSError:
                        print(f"✅ Process {pid} is no longer running, safe to clear lock")
                        os.remove(lock_file_path)
                        print("🗑️  Lock file removed")
                        return True
            except (ValueError, IndexError):
                print("⚠️  Could not parse PID from lock file")
                # Ask user if they want to force clear
                response = input("Force clear the lock file? (y/N): ")
                if response.lower() == 'y':
                    os.remove(lock_file_path)
                    print("🗑️  Lock file forcefully removed")
                    return True
                return False
                
        except Exception as e:
            print(f"❌ Error reading lock file: {e}")
            return False
    else:
        print("✅ No lock file found - no duplicate runs detected")
        return True

def check_queue_state():
    """Check and optionally clear queue state."""
    from modules.x_thread_queue import get_x_queue_status
    
    try:
        status = get_x_queue_status()
        print(f"\n📊 Queue Status:")
        print(f"   • Posts queued: {status['post_queue_size']}")
        print(f"   • Threads queued: {status['thread_queue_size']}")
        print(f"   • Worker running: {'✅' if status['worker_running'] else '❌'}")
        print(f"   • Rate limited: {'✅' if status['rate_limited'] else '❌'}")
        
        if status['post_queue_size'] > 10 or status['thread_queue_size'] > 3:
            print("⚠️  Large queue detected - possible duplicate runs")
            response = input("Clear the queue? (y/N): ")
            if response.lower() == 'y':
                # This would need to be implemented in the queue module
                print("🗑️  Queue clearing would be implemented here")
        
    except Exception as e:
        print(f"❌ Could not check queue status: {e}")

def check_last_run_state():
    """Check last run state for duplicates."""
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
                    
                    print(f"\n📝 Last Run State:")
                    print(f"   • Content hash: {last_hash}")
                    print(f"   • Time ago: {time_diff:.1f} minutes")
                    
                    if time_diff < 5:
                        print("⚠️  Very recent run detected - possible duplicate")
                        response = input("Clear last run state? (y/N): ")
                        if response.lower() == 'y':
                            os.remove(state_file)
                            print("🗑️  Last run state cleared")
        except Exception as e:
            print(f"❌ Error reading last run state: {e}")

def main():
    print("🔧 CryptoBot Duplicate Run Fixer")
    print("=" * 40)
    
    # Check and fix locks
    locks_clear = check_and_clear_locks()
    
    # Check queue state
    check_queue_state()
    
    # Check last run state
    check_last_run_state()
    
    print("\n" + "=" * 40)
    if locks_clear:
        print("✅ System is ready for bot execution")
        print("   No duplicate run issues detected")
    else:
        print("⚠️  Please resolve the issues above before running the bot")
    
    return locks_clear

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
