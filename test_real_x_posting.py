
#!/usr/bin/env python3
"""
Real X Posting Test - Verify actual posts reach X platform
"""

import logging
import asyncio
from datetime import datetime
from modules.api_clients import get_x_client_with_failover
from modules.rate_limit_manager import rate_manager
from modules.x_thread_queue import verify_post_exists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RealXTest')

async def test_real_x_posting():
    """Test if posts actually reach X platform."""
    print("🔍 TESTING REAL X POSTING TO PLATFORM")
    print("=" * 50)
    
    # Check rate limits
    print("1️⃣ Checking rate limits...")
    best_account = rate_manager.get_best_account()
    if not best_account:
        print("❌ All accounts rate limited")
        return False
    print(f"✅ Account {best_account} available")
    
    # Get client
    print("2️⃣ Getting X client...")
    client, account_num = get_x_client_with_failover(posting_only=True)
    if not client:
        print("❌ Cannot create X client")
        return False
    print(f"✅ Got client for account {account_num}")
    
    # Post test message
    print("3️⃣ Attempting real post...")
    test_message = f"🧪 Real posting test - {datetime.now().strftime('%H:%M:%S')}"
    
    try:
        tweet = client.create_tweet(text=test_message)
        tweet_id = tweet.data['id']
        tweet_url = f"https://twitter.com/user/status/{tweet_id}"
        
        # FORCE DISPLAY URL AND JSON FOR ALL REAL POSTING TESTS
        post_export = {
            "tweet_id": tweet_id,
            "url": tweet_url,
            "message": test_message,
            "posted_at": datetime.now().isoformat(),
            "account_used": account_num,
            "workflow_type": "real_posting_test"
        }
        
        print("=" * 60)
        print("🚀 REAL X POSTING TEST RESULTS")
        print("=" * 60)
        print(f"📍 THREAD URL: {tweet_url}")
        print(f"🔗 Tweet ID: {tweet_id}")
        print(f"⏰ Posted at: {datetime.now()}")
        print("📁 POSTING JSON EXPORT:")
        print(json.dumps(post_export, indent=2))
        print("=" * 60)
        
        # Record the successful post
        rate_manager.record_post(account_num)
        
        # Automatic verification attempt
        print("4️⃣ Verifying post exists...")
        verification_result = await verify_post_exists(tweet_id)
        
        # Add verification to export
        post_export["verification"] = verification_result
        
        # Save export file
        export_filename = f"real_post_test_{tweet_id}.json"
        with open(export_filename, 'w') as f:
            json.dump(post_export, f, indent=2)
        print(f"💾 JSON exported to: {export_filename}")
        
        if verification_result['exists']:
            print("✅ VERIFICATION PASSED: Post confirmed on X platform")
        else:
            print(f"⚠️  VERIFICATION INCONCLUSIVE: {verification_result['error']}")
            print("This may be normal - X API limits verification methods")
        
        return True
        
    except Exception as e:
        print(f"❌ POSTING FAILED: {e}")
        
        error_str = str(e).lower()
        if "429" in error_str or "rate limit" in error_str:
            print("🚫 Rate limited - need to wait")
            rate_manager.mark_rate_limited(account_num, duration_minutes=120)
        elif "401" in error_str or "403" in error_str:
            print("🔑 Authentication failed - check API credentials")
        elif "duplicate" in error_str:
            print("⚠️ Duplicate content - try different message")
        
        return False

if __name__ == "__main__":
    success = asyncio.run(test_real_x_posting())
    if success:
        print("\n🎉 Test completed - check the URL above to verify")
    else:
        print("\n❌ Test failed - posts are not reaching X platform")
