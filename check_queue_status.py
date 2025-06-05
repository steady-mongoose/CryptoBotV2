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
            from datetime import datetime
            reset_time = datetime.fromisoformat(status['rate_limit_reset'])
            remaining = (reset_time - datetime.now()).total_seconds() / 60
            if remaining > 0:
                print(f"   • Rate limit resets in: {remaining:.1f} minutes")
            else:
                print(f"   • Rate limit has expired, should reset soon")

        print("\n" + "=" * 40)

        if status['post_queue_size'] > 0 or status['thread_queue_size'] > 0:
            print("📝 Posts are queued and will be posted automatically")
            if status['rate_limited']:
                print("⏳ Waiting for rate limit to reset...")
                print("💡 Posts will automatically process when limit resets")
            elif not status['worker_running']:
                print("⚠️  Worker not running - queue may need restart")
            else:
                print("🚀 Queue is being processed")
        else:
            print("✅ No posts in queue")

    except Exception as e:
        print(f"❌ Error checking queue status: {e}")

if __name__ == "__main__":
    main()