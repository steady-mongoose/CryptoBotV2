#!/usr/bin/env python3
"""
Check X Queue Status
Monitor the current status of the X posting queue system.
"""

import json
from datetime import datetime
from modules.x_thread_queue import get_x_queue_status
from modules.api_clients import get_x_client

def main():
    print("📊 Checking X Queue Status...")
    print("=" * 40)

    try:
        status = get_x_queue_status()

        print("📊 Queue Status:")
        print(f"   • Posts queued: {status['queue_size']}")
        print(f"   • Worker running: {'✅' if status['worker_running'] else '❌'}")
        print(f"   • Can post now: {'✅' if status['next_post_available'] else '❌'}")

        if status['last_post_time']:
            last_post = datetime.fromisoformat(status['last_post_time'])
            time_since = datetime.now() - last_post
            print(f"   • Last post: {time_since.total_seconds():.0f} seconds ago")
        else:
            print(f"   • Last post: Never")

        print(f"\n🧪 Testing X API...")
        try:
            client = get_x_client(posting_only=True)
            if client:
                user_info = client.get_me()
                print(f"✅ X API ready: @{user_info.data.username}")
            else:
                print("❌ X API client failed")
        except Exception as api_error:
            print(f"❌ X API error: {api_error}")

        if status['queue_size'] > 0:
            print("\n🚀 Queue is active - posts will be processed automatically")
        else:
            print("\n💤 Queue is empty - no pending posts")

    except Exception as e:
        print(f"❌ Error checking queue status: {e}")

if __name__ == "__main__":
    main()")

if __name__ == "__main__":
    main()