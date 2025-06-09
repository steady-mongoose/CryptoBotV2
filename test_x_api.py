
#!/usr/bin/env python3
"""
X API Test Script
Free tier compliant testing of X (Twitter) API client creation.
"""

import logging
from modules.api_clients import get_x_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger('XAPITest')

def test_x_api():
    """Test X API client creation (free tier compliant)."""
    print("🧪 Testing X API Client Creation (Free Tier)")
    print("=" * 50)
    
    try:
        # Test posting-only client creation
        print("1️⃣ Creating X posting client...")
        client = get_x_client(posting_only=True)
        
        if not client:
            print("❌ Failed to create X client")
            print("⚠️ Check your X API credentials in Secrets")
            return False
            
        print("✅ X client created successfully")
        print("✅ Authentication credentials loaded")
        print("✅ Ready for posting")
        print("ℹ️ Note: Free tier - no read operations tested")
        
        print("\n✅ X API Test Completed Successfully!")
        print("🚀 Ready to post to X!")
        return True
        
    except Exception as e:
        print(f"❌ X API Test Failed: {e}")
        return False

if __name__ == "__main__":
    success = test_x_api()
    exit(0 if success else 1)
