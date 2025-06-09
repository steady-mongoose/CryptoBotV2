#!/usr/bin/env python3
from modules.x_thread_queue import get_x_queue_status
from modules.api_clients import get_x_client
import tweepy

def main():
    print("📊 Checking X Queue Status...")
    print("=" * 40)

    status = get_x_queue_status()

    print("📊 Queue Status:")
    print(f"   • Threads queued: {status['thread_queue_size']}")
    print(f"   • Worker running: {'✅' if status['worker_running'] else '❌'}")
    print(f"   • Rate limited: {'✅' if status['rate_limited'] else '❌'}")

    # Test X API
    print(f"\n🧪 Testing X API...")
    try:
        client = get_x_client(posting_only=True)
        if client:
            user_info = client.get_me()
            print(f"✅ X API ready: @{user_info.data.username}")
        else:
            print("❌ X API client failed")
    except tweepy.TooManyRequests:
        print("❌ X API rate limited")
    except Exception as e:
        print(f"❌ X API error: {e}")

if __name__ == "__main__":
    main()