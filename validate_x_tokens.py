
#!/usr/bin/env python3
"""
Comprehensive X API token validation for both accounts.
This script validates all X API credentials and tests basic functionality.
"""

import os
import logging
import tweepy
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def validate_account_credentials(account_number=1):
    """Validate X API credentials for specified account."""
    print(f"\n🔍 Validating Account {account_number} Credentials")
    print("=" * 50)
    
    # Get credentials based on account number
    if account_number == 1:
        consumer_key = os.getenv('X_CONSUMER_KEY')
        consumer_secret = os.getenv('X_CONSUMER_SECRET')
        access_token = os.getenv('X_ACCESS_TOKEN')
        access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
        bearer_token = os.getenv('X_BEARER_TOKEN')
        account_type = "Primary (Verified)"
        env_prefix = "X_"
    else:
        consumer_key = os.getenv('X2_CONSUMER_KEY')
        consumer_secret = os.getenv('X2_CONSUMER_SECRET')
        access_token = os.getenv('X2_ACCESS_TOKEN')
        access_token_secret = os.getenv('X2_ACCESS_TOKEN_SECRET')
        bearer_token = os.getenv('X2_BEARER_TOKEN')
        account_type = "Secondary (Non-verified)"
        env_prefix = "X2_"
    
    # Check if all required credentials are present
    credentials = {
        f'{env_prefix}CONSUMER_KEY': consumer_key,
        f'{env_prefix}CONSUMER_SECRET': consumer_secret,
        f'{env_prefix}ACCESS_TOKEN': access_token,
        f'{env_prefix}ACCESS_TOKEN_SECRET': access_token_secret,
        f'{env_prefix}BEARER_TOKEN': bearer_token
    }
    
    print(f"📋 {account_type} Credential Status:")
    missing_creds = []
    for key, value in credentials.items():
        if value:
            print(f"   ✅ {key}: Set (length: {len(value)})")
        else:
            print(f"   ❌ {key}: MISSING")
            if key != f'{env_prefix}BEARER_TOKEN':  # Bearer token is optional for posting
                missing_creds.append(key)
    
    if missing_creds:
        print(f"\n❌ Missing required credentials: {', '.join(missing_creds)}")
        print("💡 Add these to your Replit Secrets")
        return False, None
    
    # Test API connection
    print(f"\n🔗 Testing {account_type} API Connection...")
    try:
        # Create posting-only client (no bearer token to avoid rate limits)
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=False
        )
        
        # Test authentication
        user_info = client.get_me()
        print(f"✅ Successfully authenticated!")
        print(f"   Username: @{user_info.data.username}")
        print(f"   User ID: {user_info.data.id}")
        print(f"   Account created: {user_info.data.created_at}")
        
        return True, client
        
    except tweepy.Unauthorized as e:
        print(f"❌ Authentication failed: {e}")
        print("💡 Check if your API credentials are correct")
        return False, None
    except tweepy.Forbidden as e:
        print(f"❌ Access forbidden: {e}")
        print("💡 Your app may need additional permissions")
        return False, None
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False, None

def test_posting_capability(client, account_number):
    """Test if the account can post tweets."""
    print(f"\n🧪 Testing Account {account_number} Posting Capability...")
    
    try:
        # Create a test tweet
        test_text = f"🧪 API Test - Account {account_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} #CryptoBot"
        
        # Check tweet length
        if len(test_text) > 280:
            print(f"❌ Test tweet too long: {len(test_text)} characters")
            return False
        
        # Post test tweet
        tweet = client.create_tweet(text=test_text)
        tweet_id = tweet.data['id']
        
        print(f"✅ Test tweet posted successfully!")
        print(f"   Tweet ID: {tweet_id}")
        print(f"   URL: https://x.com/user/status/{tweet_id}")
        
        # Wait a moment, then delete the test tweet
        import time
        time.sleep(3)
        
        try:
            client.delete_tweet(tweet_id)
            print(f"✅ Test tweet deleted successfully!")
        except Exception as e:
            print(f"⚠️  Could not delete test tweet: {e}")
            print(f"   You may need to manually delete tweet {tweet_id}")
        
        return True
        
    except tweepy.TooManyRequests as e:
        print(f"❌ Rate limited: {e}")
        print("⏳ This account has hit the posting limit")
        print("📊 Free tier: 1,500 tweets/month (~50/day)")
        return False
    except tweepy.Forbidden as e:
        print(f"❌ Posting forbidden: {e}")
        print("🚨 Account may be restricted or app needs write permissions")
        return False
    except Exception as e:
        print(f"❌ Posting failed: {e}")
        return False

def main():
    """Main validation function."""
    print("🔐 X API Token Validation")
    print("=" * 60)
    
    results = {}
    
    # Test both accounts
    for account_num in [1, 2]:
        auth_success, client = validate_account_credentials(account_num)
        results[f'account_{account_num}_auth'] = auth_success
        
        if auth_success and client:
            posting_success = test_posting_capability(client, account_num)
            results[f'account_{account_num}_posting'] = posting_success
        else:
            results[f'account_{account_num}_posting'] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    # Account 1 (Primary)
    print("🔵 Primary Account (Verified):")
    if results['account_1_auth']:
        print("   ✅ Authentication: WORKING")
        if results['account_1_posting']:
            print("   ✅ Posting: WORKING")
        else:
            print("   ❌ Posting: FAILED")
    else:
        print("   ❌ Authentication: FAILED")
        print("   ❌ Posting: NOT TESTED")
    
    # Account 2 (Secondary)
    print("\n🟡 Secondary Account (Non-verified):")
    if results['account_2_auth']:
        print("   ✅ Authentication: WORKING")
        if results['account_2_posting']:
            print("   ✅ Posting: WORKING")
        else:
            print("   ❌ Posting: FAILED")
    else:
        print("   ❌ Authentication: FAILED")
        print("   ❌ Posting: NOT TESTED")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    working_accounts = []
    if results['account_1_auth'] and results['account_1_posting']:
        working_accounts.append("Primary")
    if results['account_2_auth'] and results['account_2_posting']:
        working_accounts.append("Secondary")
    
    if len(working_accounts) == 2:
        print("   🎉 Both accounts working! Failover system ready.")
        print("   ✅ You can run the bot with dual account protection.")
    elif len(working_accounts) == 1:
        print(f"   ⚠️  Only {working_accounts[0]} account working.")
        print("   📝 Fix the other account for full failover protection.")
    else:
        print("   🚨 No accounts working! Check your credentials.")
        print("   🔧 Verify all tokens in Replit Secrets.")
    
    # Next steps
    print("\n🚀 NEXT STEPS:")
    if working_accounts:
        print("   1. Run: python test_x_simple_post.py")
        print("   2. Test bot: Use 'X Only (Safe)' workflow")
        print("   3. Monitor: python check_x_limits.py")
    else:
        print("   1. Double-check all tokens in Replit Secrets")
        print("   2. Verify app permissions on developer.twitter.com")
        print("   3. Re-run this validation script")

if __name__ == "__main__":
    main()
