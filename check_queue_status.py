#!/usr/bin/env python3
"""
Script to check the status of the X posting queue.
"""

import logging
from modules.x_thread_queue import get_x_queue_status

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    """Check and display X queue status."""
    print("🔍 Checking X Posting Queue Status...")
    print("=" * 40)

    try:
        status = get_x_queue_status()

        print(f"📊 Queue Status:")
        print(f"   • Posts queued: {status['post_queue_size']}")
        print(f"   • Threads queued: {status['thread_queue_size']}")
        print(f"   • Worker running: {'✅' if status['worker_running'] else '❌'}")
        print(f"   • Rate limited: {'🚫' if status['rate_limited'] else '✅'}")

        if status['rate_limit_reset']:
            print(f"   • Rate limit resets: {status['rate_limit_reset']}")

        print("\n" + "=" * 40)

        if status['post_queue_size'] > 0 or status['thread_queue_size'] > 0:
            print("📝 Posts are queued and will be posted automatically")
            if status['rate_limited']:
                print("⏳ Waiting for rate limit to reset...")
            else:
                print("🚀 Queue is being processed")
        else:
            print("✅ No posts in queue")

    except Exception as e:
        print(f"❌ Error checking queue status: {e}")

if __name__ == "__main__":
    main()