
#!/usr/bin/env python3
"""
Verbose X Posting Test - Clear YES/NO confirmation
"""

import logging
import time
from datetime import datetime
from modules.api_clients import get_x_client_with_failover
from modules.rate_limit_manager import rate_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('VerbosePostingTest')

def test_verbose_posting():
    """Test X posting with absolute YES/NO confirmation."""
    print("🧪 VERBOSE X POSTING TEST")
    print("=" * 50)
    
    # Check rate limits first
    print("\n1️⃣ CHECKING RATE LIMITS...")
    for account_num in [1, 2]:
        can_post = rate_manager.can_post(account_num)
        status = "✅ AVAILABLE" if can_post else "❌ RATE LIMITED"
        print(f"   Account {account_num}: {status}")
    
    # Get client
    print("\n2️⃣ GETTING X CLIENT...")
    try:
        client, account_num = get_x_client_with_failover(posting_only=True)
        if not client:
            print("❌ NO: Cannot create X client")
            print("🔑 REASON: Missing or invalid API credentials")
            return False
        print(f"✅ Got client for account {account_num}")
    except Exception as e:
        print(f"❌ NO: Client creation failed - {e}")
        return False
    
    # Attempt actual post
    print("\n3️⃣ ATTEMPTING REAL POST...")
    test_message = f"🧪 Verbose Test - {datetime.now().strftime('%H:%M:%S')}"
    
    try:
        tweet = client.create_tweet(text=test_message)
        tweet_id = tweet.data['id']
        tweet_url = f"https://twitter.com/user/status/{tweet_id}"
        
        print(f"✅ YES: POSTING SUCCESS!")
        print(f"📍 Tweet ID: {tweet_id}")
        print(f"🔗 URL: {tweet_url}")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Record the post
        rate_manager.record_post(account_num)
        
        # Clean up test tweet
        try:
            client.delete_tweet(tweet_id)
            print("🗑️ Test tweet deleted")
        except:
            print("⚠️ Could not delete test tweet")
        
        return True
        
    except Exception as post_error:
        error_str = str(post_error)
        print(f"❌ NO: POSTING FAILED")
        print(f"💥 ERROR: {error_str}")
        
        # Detailed error analysis
        if "429" in error_str or "rate limit" in error_str.lower():
            print("🔍 REASON: Rate limit exceeded")
            print("⏰ SOLUTION: Wait 2+ hours or use different account")
        elif "401" in error_str or "403" in error_str:
            print("🔍 REASON: Authentication failure")
            print("🔑 SOLUTION: Check API credentials in Secrets")
        elif "duplicate" in error_str.lower():
            print("🔍 REASON: Duplicate content detected")
            print("✏️ SOLUTION: Change message content")
        else:
            print("🔍 REASON: Unknown API error")
            print("📞 SOLUTION: Check X API status")
        
        return False

if __name__ == "__main__":
    success = test_verbose_posting()
    print("\n" + "=" * 50)
    if success:
        print("🎉 FINAL RESULT: YES - X posting is working")
    else:
        print("💥 FINAL RESULT: NO - X posting is blocked")
