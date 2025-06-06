
#!/usr/bin/env python3
"""
Test X API failover system - verifies both accounts work.
"""

import logging
from modules.api_clients import get_x_client, get_x_client_with_failover

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_x_failover():
    print("🧪 Testing X Account Failover System")
    print("=" * 50)
    
    # Test Account 1
    print("\n1️⃣ Testing Primary Account (Account 1):")
    client1 = get_x_client(posting_only=True, account_number=1)
    if client1:
        try:
            user1 = client1.get_me()
            print(f"   ✅ Account 1: @{user1.data.username}")
        except Exception as e:
            print(f"   ❌ Account 1 auth failed: {e}")
    else:
        print("   ❌ Account 1: Failed to initialize")
    
    # Test Account 2  
    print("\n2️⃣ Testing Failover Account (Account 2):")
    client2 = get_x_client(posting_only=True, account_number=2)
    if client2:
        try:
            user2 = client2.get_me()
            print(f"   ✅ Account 2: @{user2.data.username}")
        except Exception as e:
            print(f"   ❌ Account 2 auth failed: {e}")
    else:
        print("   ❌ Account 2: Failed to initialize")
    
    # Test Automatic Failover
    print("\n🔄 Testing Automatic Failover:")
    client, account_num = get_x_client_with_failover(posting_only=True)
    if client and account_num:
        try:
            user = client.get_me()
            print(f"   ✅ Failover selected Account {account_num}: @{user.data.username}")
        except Exception as e:
            print(f"   ❌ Failover failed: {e}")
    else:
        print("   ❌ No accounts available for failover")
    
    # Summary
    print("\n📊 Failover System Status:")
    account1_ok = client1 is not None
    account2_ok = client2 is not None
    
    if account1_ok and account2_ok:
        print("   🎉 EXCELLENT: Both accounts ready!")
        print("   📈 Double rate limits: 3,000 tweets/month")
        print("   🔄 Automatic failover: ENABLED")
    elif account1_ok or account2_ok:
        working_account = "Account 1" if account1_ok else "Account 2"
        print(f"   ⚠️  PARTIAL: Only {working_account} working")
        print("   📈 Standard rate limits: 1,500 tweets/month")
        print("   🔄 Failover: LIMITED")
    else:
        print("   ❌ FAILED: No accounts working")
        print("   📉 Cannot post to X")
        print("   🔄 Failover: UNAVAILABLE")
    
    print("\n💡 Next Steps:")
    if not account1_ok:
        print("   - Check Account 1 credentials in Secrets")
    if not account2_ok:
        print("   - Add Account 2 credentials (see SETUP_FAILOVER.md)")
    if account1_ok and account2_ok:
        print("   - Ready to run bot with failover protection!")

if __name__ == "__main__":
    test_x_failover()
