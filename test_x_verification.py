
#!/usr/bin/env python3
"""
X Posting Verification Test - Only report success with proof
"""

import logging
import asyncio
import json
from datetime import datetime
from modules.api_clients import get_x_client_with_failover
from modules.x_thread_queue import verify_post_exists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('XVerificationTest')

async def test_x_posting_with_verification():
    """Test X posting with strict verification requirements."""
    print("🔍 X POSTING VERIFICATION TEST")
    print("=" * 50)
    print("⚠️  RULE: No success claims without URL proof and verification!")
    print()
    
    # Get client
    print("1️⃣ Getting X client...")
    client, account_num = get_x_client_with_failover(posting_only=True)
    if not client:
        print("❌ FAILED: Cannot create X client - check API credentials")
        return False
    print(f"✅ Got client for account {account_num}")
    
    # Post test message
    test_message = f"🧪 Verification Test - {datetime.now().strftime('%H:%M:%S')}"
    print(f"\n2️⃣ Posting test message...")
    print(f"📝 Message: {test_message}")
    
    try:
        tweet = client.create_tweet(text=test_message)
        tweet_id = tweet.data['id']
        tweet_url = f"https://twitter.com/user/status/{tweet_id}"
        
        print(f"📍 Tweet created with ID: {tweet_id}")
        print(f"🔗 URL: {tweet_url}")
        
        # NOW THE CRITICAL PART - VERIFICATION
        print(f"\n3️⃣ CRITICAL: Verifying post actually exists...")
        verification_result = await verify_post_exists(tweet_id)
        
        if verification_result.get('exists') and verification_result.get('content_verified'):
            # Create JSON export as proof
            proof_export = {
                "tweet_id": tweet_id,
                "url": tweet_url,
                "message": test_message,
                "posted_at": datetime.now().isoformat(),
                "verification": verification_result,
                "account_used": account_num
            }
            
            print("✅ VERIFIED SUCCESS - POST CONFIRMED ON X PLATFORM!")
            print(f"📍 VERIFIED URL: {tweet_url}")
            print(f"🔍 Verification method: {verification_result.get('method')}")
            print(f"📊 Status code: {verification_result.get('status_code')}")
            print("\n📁 PROOF EXPORT (JSON):")
            print(json.dumps(proof_export, indent=2))
            
            # Save proof to file
            proof_filename = f"x_post_proof_{tweet_id}.json"
            with open(proof_filename, 'w') as f:
                json.dump(proof_export, f, indent=2)
            print(f"\n💾 Proof saved to: {proof_filename}")
            
            return True
            
        else:
            print("❌ VERIFICATION FAILED - CANNOT CONFIRM POST EXISTS!")
            print(f"🚫 Error: {verification_result.get('error')}")
            print(f"📍 Attempted URL: {tweet_url}")
            print("⚠️  CRITICAL: This is NOT a successful post!")
            return False
            
    except Exception as e:
        print(f"❌ POSTING FAILED: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_x_posting_with_verification())
    print("\n" + "=" * 50)
    if success:
        print("🎉 RESULT: SUCCESS WITH VERIFICATION PROOF")
        print("✅ Post confirmed accessible on X platform")
    else:
        print("💥 RESULT: FAILED OR UNVERIFIED")
        print("❌ Cannot confirm post exists on X platform")
    print("=" * 50)
