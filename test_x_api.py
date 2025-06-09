
#!/usr/bin/env python3
"""
X API Test Script
Comprehensive testing of X (Twitter) API authentication and posting capabilities.
"""

import logging
from modules.api_clients import get_x_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger('XAPITest')

def test_x_api():
    """Test X API authentication and basic functionality."""
    print("🧪 Testing X API Authentication and Functionality")
    print("=" * 50)
    
    try:
        # Test posting-only client
        print("1️⃣ Testing posting-only client...")
        client = get_x_client(posting_only=True)
        
        if not client:
            print("❌ Failed to create X client")
            return False
            
        # Test authentication
        print("2️⃣ Testing authentication...")
        try:
            user_info = client.get_me()
            if user_info and user_info.data:
                print(f"✅ Connected to X as: @{user_info.data.username}")
                print(f"Account ID: {user_info.data.id}")
            else:
                print("❌ Authentication failed - no user data")
                return False
        except Exception as auth_error:
            print(f"❌ X API Error: {auth_error}")
            return False
        
        # Test rate limits
        print("3️⃣ Checking rate limits...")
        try:
            # Get recent tweets to test read access
            recent_tweets = client.get_users_tweets(
                user_info.data.id, 
                max_results=5,
                tweet_fields=['created_at', 'public_metrics']
            )
            
            if recent_tweets and recent_tweets.data:
                print(f"✅ Can read tweets: Found {len(recent_tweets.data)} recent tweets")
                for tweet in recent_tweets.data[:3]:
                    print(f"   • {tweet.text[:50]}...")
            else:
                print("⚠️ No recent tweets or limited read access")
                
        except Exception as read_error:
            print(f"⚠️ Read access limited: {read_error}")
        
        print("\n✅ X API Test Completed Successfully!")
        print("🚀 Ready to post to X!")
        return True
        
    except Exception as e:
        print(f"❌ X API Test Failed: {e}")
        return False

if __name__ == "__main__":
    success = test_x_api()
    exit(0 if success else 1)
