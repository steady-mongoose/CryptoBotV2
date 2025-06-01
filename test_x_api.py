
import os
import tweepy
from modules.api_clients import get_x_client

def test_x_credentials():
    """Test X API credentials without posting anything."""
    try:
        # Check if all credentials are present
        required_vars = ['X_CONSUMER_KEY', 'X_CONSUMER_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"❌ Missing environment variables: {missing_vars}")
            return False
            
        print("✅ All required environment variables are set")
        
        # Test API client initialization
        client = get_x_client()
        print("✅ X API client initialized successfully")
        
        # Test API access with a simple call (get own user info)
        me = client.get_me()
        print(f"✅ API test successful! Connected as: @{me.data.username}")
        return True
        
    except tweepy.Unauthorized as e:
        print(f"❌ 401 Unauthorized: {e}")
        print("   - Check that your API keys are correct")
        print("   - Verify your app has Read+Write permissions")
        print("   - Ensure tokens are not expired")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_x_credentials()
