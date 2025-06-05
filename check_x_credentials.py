
#!/usr/bin/env python3
"""
Diagnostic script to check X API credentials and connection.
"""

import os
import logging
from modules.api_clients import get_x_client

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    """Check X API credentials and connection."""
    print("🔍 X API Credentials Diagnostic")
    print("=" * 40)
    
    # Check if credentials are set
    credentials = {
        'X_CONSUMER_KEY': os.getenv('X_CONSUMER_KEY'),
        'X_CONSUMER_SECRET': os.getenv('X_CONSUMER_SECRET'),
        'X_ACCESS_TOKEN': os.getenv('X_ACCESS_TOKEN'),
        'X_ACCESS_TOKEN_SECRET': os.getenv('X_ACCESS_TOKEN_SECRET')
    }
    
    print("📋 Credential Status:")
    missing_creds = []
    for key, value in credentials.items():
        if value:
            print(f"   ✅ {key}: Set (length: {len(value)})")
        else:
            print(f"   ❌ {key}: MISSING")
            missing_creds.append(key)
    
    if missing_creds:
        print(f"\n❌ Missing credentials: {', '.join(missing_creds)}")
        print("💡 Add these to your Secrets in Replit")
        return False
    
    print("\n🔗 Testing X API Connection...")
    try:
        client = get_x_client(posting_only=True)
        if not client:
            print("❌ Failed to create X client")
            return False
            
        # Test authentication
        user_info = client.get_me()
        print(f"✅ Successfully authenticated as: @{user_info.data.username}")
        print(f"   User ID: {user_info.data.id}")
        print(f"   Account created: {user_info.data.created_at}")
        
        return True
        
    except Exception as e:
        print(f"❌ X API connection failed: {e}")
        print("💡 Check if your API credentials are valid and have posting permissions")
        return False

if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 40)
    if success:
        print("🎉 X API is ready for posting!")
    else:
        print("🚨 Fix the issues above before attempting to post to X")
