
#!/usr/bin/env python3
"""
Simple X API test - posts one test tweet to verify credentials work.
"""

import logging
import tweepy
from modules.api_clients import get_x_client

logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    """Test X API with a simple post."""
    print("🧪 Testing X API credentials with simple post...")
    print("=" * 50)
    
    try:
        # Get X client
        client = get_x_client(posting_only=True)
        if not client:
            print("❌ Failed to initialize X API client")
            print("🔑 Check your X API credentials in Secrets:")
            print("  - X_CONSUMER_KEY")
            print("  - X_CONSUMER_SECRET") 
            print("  - X_ACCESS_TOKEN")
            print("  - X_ACCESS_TOKEN_SECRET")
            return False
        
        # Test authentication
        try:
            user_info = client.get_me()
            print(f"✅ Authenticated as: @{user_info.data.username}")
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
        
        # Post test tweet
        from datetime import datetime
        test_text = f"🧪 X API Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} #CryptoBot"
        
        try:
            tweet = client.create_tweet(text=test_text)
            tweet_id = tweet.data['id']
            print(f"✅ Test tweet posted successfully!")
            print(f"🐦 Tweet ID: {tweet_id}")
            print(f"🔗 URL: https://x.com/user/status/{tweet_id}")
            return True
            
        except tweepy.TooManyRequests as e:
            print(f"❌ Rate limited: {e}")
            print("⏳ Your X account has hit the free tier posting limit")
            print("📊 Free tier: 1,500 tweets/month (~50/day)")
            return False
        
        except tweepy.Forbidden as e:
            print(f"❌ Forbidden: {e}")
            print("🚨 Your X account may be restricted or suspended")
            return False
            
        except Exception as e:
            print(f"❌ Error posting test tweet: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 50)
    if success:
        print("🎉 X API is working correctly!")
    else:
        print("🚨 X API test failed - fix issues above")
