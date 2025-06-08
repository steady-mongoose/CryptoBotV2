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

        # Status assessment
        if status['worker_running'] and not status['rate_limited']:
            print("\n✅ Queue system is healthy and ready")
        elif status['worker_running'] and status['rate_limited']:
            print("\n⏳ Queue system running but rate limited")
        elif not status['worker_running']:
            print("\n❌ Queue worker is not running")
            print("💡 Run 'python restart_x_queue.py' to fix")
        
        # Queue recommendations
        total_items = status['post_queue_size'] + status['thread_queue_size']
        if total_items > 10:
            print(f"\n⚠️  Large queue detected ({total_items} items)")
            print("This may indicate a backlog or rate limiting")
        elif total_items > 0:
            print(f"\n📝 Queue has {total_items} items pending")
        else:
            print("\n📭 Queue is empty")

    except Exception as e:
        print(f"❌ Error checking queue status: {e}")
        print("💡 Queue system may not be initialized")

if __name__ == "__main__":
    main()