
#!/usr/bin/env python3
"""
Script to restart the X posting queue worker.
Use this if the worker stops due to rate limits or errors.
"""

import logging
from modules.x_thread_queue import stop_x_queue, start_x_queue, get_x_queue_status

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    """Restart the X queue worker."""
    print("🔄 Restarting X Posting Queue Worker...")
    print("=" * 40)

    try:
        # Get current status
        status = get_x_queue_status()
        print(f"📊 Current Status:")
        print(f"   • Posts queued: {status['post_queue_size']}")
        print(f"   • Threads queued: {status['thread_queue_size']}")
        print(f"   • Worker running: {'✅' if status['worker_running'] else '❌'}")
        print(f"   • Rate limited: {'🚫' if status['rate_limited'] else '✅'}")

        print("\n🛑 Stopping current worker...")
        stop_x_queue()

        print("🚀 Starting new worker...")
        start_x_queue()

        # Check new status
        new_status = get_x_queue_status()
        print(f"\n✅ New Status:")
        print(f"   • Worker running: {'✅' if new_status['worker_running'] else '❌'}")
        print(f"   • Posts still queued: {new_status['post_queue_size']}")
        print(f"   • Threads still queued: {new_status['thread_queue_size']}")

        if new_status['worker_running']:
            print("\n🎉 Queue worker successfully restarted!")
            if new_status['rate_limited']:
                print("⏳ Worker will process queued posts when rate limit resets")
            else:
                print("🚀 Worker is processing queued posts now")
        else:
            print("\n❌ Failed to restart worker - check X API credentials")

    except Exception as e:
        print(f"❌ Error restarting queue: {e}")

if __name__ == "__main__":
    main()
