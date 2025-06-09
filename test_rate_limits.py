
#!/usr/bin/env python3
"""Test rate limit handling and account failover."""

import logging
from modules.api_clients import get_x_client_with_failover
from modules.rate_limit_manager import rate_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RateLimitTest')

def test_rate_limits():
    """Test rate limit handling."""
    print("🧪 Testing Rate Limit Handling")
    print("=" * 40)
    
    # Test account availability
    for account_num in [1, 2]:
        can_post = rate_manager.can_post(account_num)
        print(f"Account {account_num}: {'✅ Available' if can_post else '❌ Rate Limited'}")
    
    # Test best account selection
    best_account = rate_manager.get_best_account()
    print(f"Best account: {best_account}")
    
    # Test client creation with failover
    client, account_num = get_x_client_with_failover(posting_only=True)
    if client:
        print(f"✅ Got client for account {account_num}")
        return True
    else:
        print("❌ No available accounts")
        return False

if __name__ == "__main__":
    test_rate_limits()
