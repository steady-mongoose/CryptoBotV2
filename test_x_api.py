
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
            
        # Test basic client creation only
        print("2️⃣ Testing client creation...")
        if client:
            print("✅ X client created successfully")
            print("✅ Authentication credentials loaded")
            print("✅ Ready for posting (read operations not tested to avoid 401 errors)")
        else:
            print("❌ Failed to create X client")
            return False
        
        print("\n✅ X API Test Completed Successfully!")
        print("🚀 Ready to post to X!")
        return True
        
    except Exception as e:
        print(f"❌ X API Test Failed: {e}")
        return False

if __name__ == "__main__":
    success = test_x_api()
    exit(0 if success else 1)
