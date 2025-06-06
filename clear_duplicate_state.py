
#!/usr/bin/env python3
"""
Script to clear duplicate prevention state files
"""

import os
import tempfile
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    print("🧹 Clearing Duplicate Prevention State...")
    print("=" * 40)
    
    files_cleared = 0
    
    # Clear thread state file
    state_file = "last_thread_state.txt"
    if os.path.exists(state_file):
        try:
            os.remove(state_file)
            print(f"✅ Removed: {state_file}")
            files_cleared += 1
        except Exception as e:
            print(f"❌ Could not remove {state_file}: {e}")
    else:
        print(f"📝 No state file found: {state_file}")
    
    # Clear process lock file
    lock_file_path = os.path.join(tempfile.gettempdir(), 'crypto_bot.lock')
    if os.path.exists(lock_file_path):
        try:
            os.remove(lock_file_path)
            print(f"✅ Removed: {lock_file_path}")
            files_cleared += 1
        except Exception as e:
            print(f"❌ Could not remove {lock_file_path}: {e}")
    else:
        print(f"🔒 No lock file found: {lock_file_path}")
    
    print()
    if files_cleared > 0:
        print(f"✅ Cleared {files_cleared} state files")
        print("🚀 Bot is now ready to run fresh")
    else:
        print("✅ No state files to clear")
    
    print()
    print("Note: This clears duplicate prevention state.")
    print("Only use this if you're sure no other bot instances are running.")

if __name__ == "__main__":
    main()
