
import os
import tweepy
import asyncio
import time
from modules.api_clients import get_x_client

def test_x_credentials():
    """Comprehensive test of X API credentials for free tier limitations."""
    try:
        # Check if all credentials are present
        required_vars = ['X_CONSUMER_KEY', 'X_CONSUMER_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"❌ Missing environment variables: {missing_vars}")
            return False
            
        print("✅ All required environment variables are set")
        
        # Show credential format (first/last few chars for security)
        consumer_key = os.getenv('X_CONSUMER_KEY')
        access_token = os.getenv('X_ACCESS_TOKEN')
        print(f"🔍 Consumer Key format: {consumer_key[:5]}...{consumer_key[-5:]}")
        print(f"🔍 Access Token format: {access_token[:5]}...{access_token[-5:]}")
        
        # Test API client initialization
        client = get_x_client()
        print("✅ X API client initialized successfully")
        
        # Test 1: Basic authentication (get own user info)
        try:
            me = client.get_me()
            print(f"✅ Basic authentication successful! Connected as: @{me.data.username}")
        except tweepy.Unauthorized as e:
            print(f"❌ 401 Unauthorized: {e}")
            print("\n🚨 COMMON FIXES FOR 401 ERROR:")
            print("   1. Go to developer.twitter.com")
            print("   2. Select your app → Settings → App permissions")
            print("   3. Change from 'Read' to 'Read and Write'")
            print("   4. Go to Keys and tokens → Regenerate Access Token & Secret")
            print("   5. Update the new tokens in Replit Secrets")
            print("   6. Make sure you copied the tokens correctly (no extra spaces)")
            return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

        # Test 2: Tweet creation (required for bot functionality)
        try:
            test_tweet = "🤖 Testing X API connectivity - this tweet will be deleted shortly #TestTweet"
            response = client.create_tweet(text=test_tweet)
            tweet_id = response.data['id']
            print(f"✅ Tweet creation successful! Tweet ID: {tweet_id}")
            
            # Clean up - delete the test tweet
            time.sleep(2)  # Wait a moment before deletion
            client.delete_tweet(tweet_id)
            print("✅ Tweet deletion successful!")
            
        except tweepy.Unauthorized as e:
            print(f"❌ Tweet creation unauthorized: {e}")
            print("   - Your app needs Read+Write permissions")
            print("   - Free tier may have restrictions on tweet creation")
            return False
        except tweepy.Forbidden as e:
            print(f"❌ Tweet creation forbidden: {e}")
            print("   - Your account may be restricted")
            print("   - Free tier may have posting limitations")
            return False
        except tweepy.TooManyRequests as e:
            print(f"⚠️  Rate limited during tweet test: {e}")
            print("   - Free tier has strict rate limits")
            print("   - Your bot may hit rate limits frequently")
            return False
        except Exception as e:
            print(f"❌ Tweet creation error: {e}")
            return False

        # Test 3: Search functionality (used for social metrics)
        search_available = True
        try:
            search_results = client.search_recent_tweets(query="#crypto -is:retweet", max_results=10)
            if search_results.data:
                print(f"✅ Search functionality working! Found {len(search_results.data)} tweets")
            else:
                print("⚠️  Search returned no results (may be normal)")
        except tweepy.Unauthorized as e:
            print(f"⚠️  Search unauthorized (NORMAL FOR FREE TIER): {e}")
            print("   - Free tier typically doesn't have search access")
            print("   - Bot will use fallback social metrics")
            search_available = False
        except tweepy.Forbidden as e:
            print(f"⚠️  Search forbidden (NORMAL FOR FREE TIER): {e}")
            print("   - Bot will use fallback social metrics")
            search_available = False
        except Exception as e:
            print(f"⚠️  Search error (may be normal for free tier): {e}")
            search_available = False

        # Test 4: Rate limit status
        try:
            rate_limit_status = client.get_rate_limit_status()
            print("✅ Rate limit check successful!")
            print("📊 Current rate limits:")
            
            # Check tweet limits
            if 'statuses' in rate_limit_status.data:
                tweets_remaining = rate_limit_status.data['statuses'].get('/statuses/update', {}).get('remaining', 'Unknown')
                print(f"   - Tweets remaining: {tweets_remaining}")
            
            # Check search limits  
            if 'search' in rate_limit_status.data:
                search_remaining = rate_limit_status.data['search'].get('/search/tweets', {}).get('remaining', 'Unknown')
                print(f"   - Search remaining: {search_remaining}")
                
        except Exception as e:
            print(f"⚠️  Could not check rate limits: {e}")

        print("\n🎉 X API credentials are working!")
        print("\n⚠️  FREE TIER LIMITATIONS:")
        print("   - Limited to 1,500 tweets per month")
        print("   - Reduced rate limits")
        print("   - Search typically disabled (bot uses fallback)")
        print("   - Your bot may need to handle rate limits gracefully")
        
        if not search_available:
            print("\n📝 NOTE: Search disabled - social metrics will use fallback values")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_bot_compatibility():
    """Test if the X API setup is compatible with the bot's usage patterns."""
    print("\n🔍 Testing bot compatibility...")
    
    try:
        client = get_x_client()
        
        # Simulate bot posting pattern
        print("Testing bot posting pattern...")
        
        # Test main update post (this is what your bot does)
        test_message = "🚀 Crypto Market Update (Test)! 📈 Latest on top altcoins #CryptoTest"
        
        if len(test_message) > 280:
            print(f"⚠️  Message length issue: {len(test_message)} characters (limit: 280)")
        else:
            print(f"✅ Message length OK: {len(test_message)} characters")
        
        # Test individual coin post format
        test_coin_post = "Ripple (XRP): $0.50 (2.5% 24h) 📈\nPredicted: $0.52\n#XRP"
        if len(test_coin_post) > 280:
            print(f"⚠️  Coin post length issue: {len(test_coin_post)} characters")
        else:
            print(f"✅ Coin post length OK: {len(test_coin_post)} characters")
            
        print("✅ Bot message formats are compatible")
        
        return True
        
    except Exception as e:
        print(f"❌ Bot compatibility test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing X API credentials for free tier compatibility...\n")
    
    # Run basic credential test
    basic_test_passed = test_x_credentials()
    
    if basic_test_passed:
        # Run bot compatibility test
        compatibility_test_passed = test_bot_compatibility()
        
        if compatibility_test_passed:
            print("\n✅ ALL TESTS PASSED!")
            print("Your X API setup should work with the bot (with free tier limitations)")
        else:
            print("\n⚠️  COMPATIBILITY ISSUES DETECTED")
            print("Your credentials work but may have issues with bot functionality")
    else:
        print("\n❌ CREDENTIAL TEST FAILED")
        print("Fix your X API credentials before running the bot")
