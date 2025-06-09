
import logging
import asyncio
from modules.api_clients import get_x_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('XTest')

def test_x_posting():
    """Test actual X posting capability."""
    print("🧪 TESTING REAL X API POSTING")
    print("=" * 40)
    
    try:
        # Get X client
        client = get_x_client(posting_only=True)
        if not client:
            print("❌ FAILED: Cannot create X client")
            print("🔑 Check your X API credentials in Secrets")
            return False
        
        print("✅ X client created successfully")
        
        # Try a simple test post
        test_message = f"🧪 API Test - {datetime.now().strftime('%H:%M:%S')}"
        
        try:
            tweet = client.create_tweet(text=test_message)
            tweet_id = tweet.data['id']
            print(f"🎉 SUCCESS! Posted test tweet: https://twitter.com/user/status/{tweet_id}")
            
            # Delete the test tweet
            try:
                client.delete_tweet(tweet_id)
                print("🗑️ Test tweet deleted")
            except:
                print("⚠️ Could not delete test tweet (might need additional permissions)")
            
            return True
            
        except Exception as post_error:
            print(f"❌ POSTING FAILED: {post_error}")
            
            if "401" in str(post_error) or "403" in str(post_error):
                print("🔑 AUTHENTICATION ERROR - Check your X API credentials!")
            elif "duplicate" in str(post_error).lower():
                print("✅ Duplicate detection (API works, just duplicate content)")
                return True
            
            return False
            
    except Exception as e:
        print(f"❌ X API Test Error: {e}")
        return False

if __name__ == "__main__":
    from datetime import datetime
    success = test_x_posting()
    if success:
        print("\n🚀 X API is working! Your bot should be able to post.")
    else:
        print("\n💥 X API test failed - fix credentials before posting.")
