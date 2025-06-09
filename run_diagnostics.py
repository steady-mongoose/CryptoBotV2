
#!/usr/bin/env python3
"""
Comprehensive Diagnostics Script
Run full system checks before executing any workflows.
"""

import logging
import sys
from datetime import datetime
from modules.error_handler import error_handler, APIError, ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Diagnostics')

def run_comprehensive_diagnostics():
    """Run complete system diagnostics."""
    print("🔍 COMPREHENSIVE SYSTEM DIAGNOSTICS")
    print("=" * 50)
    
    all_checks_passed = True
    
    # 1. System Health Check
    print("1️⃣ System Health Check...")
    health_status = error_handler.check_system_health()
    if health_status["healthy"]:
        print("✅ System health: OK")
    else:
        print("❌ System health: FAILED")
        for error in health_status["errors"]:
            print(f"   💥 {error}")
        all_checks_passed = False
    
    for warning in health_status["warnings"]:
        print(f"⚠️  {warning}")
    
    # 2. API Clients Check
    print("\n2️⃣ API Clients Check...")
    try:
        from modules.api_clients import get_x_client_with_failover, get_discord_webhook_url
        
        # X API Check
        client, account_num = get_x_client_with_failover(posting_only=True)
        if client and account_num:
            print(f"✅ X API client: Ready (Account {account_num})")
        else:
            print("❌ X API client: FAILED")
            all_checks_passed = False
        
        # Discord Check
        webhook_url = get_discord_webhook_url()
        if webhook_url:
            print("✅ Discord webhook: Configured")
        else:
            print("⚠️  Discord webhook: Not configured")
            
    except Exception as e:
        print(f"❌ API client check failed: {e}")
        error_handler.handle_error(e, "API client diagnostics")
        all_checks_passed = False
    
    # 3. Database Check
    print("\n3️⃣ Database Check...")
    try:
        from modules.database import Database
        db = Database('crypto_bot.db')
        print("✅ Database: Connected")
        db.close()
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        error_handler.handle_error(e, "Database diagnostics")
        all_checks_passed = False
    
    # 4. Queue System Check
    print("\n4️⃣ Queue System Check...")
    try:
        from modules.x_thread_queue import get_x_queue_status
        queue_status = get_x_queue_status()
        print(f"✅ Queue status: {queue_status['queue_size']} pending")
        print(f"   Worker: {'Running' if queue_status['worker_running'] else 'Stopped'}")
    except Exception as e:
        print(f"❌ Queue system check failed: {e}")
        error_handler.handle_error(e, "Queue system diagnostics")
        all_checks_passed = False
    
    # 5. Content Verification Check
    print("\n5️⃣ Content Verification Check...")
    try:
        from modules.content_verification import verify_all_content
        import asyncio
        
        test_data = {
            'coin_name': 'ripple',
            'price': 2.21,
            'price_change_24h': 5.2,
            'youtube_video': {'title': 'Test video', 'url': 'https://example.com'}
        }
        
        async def test_verification():
            return await verify_all_content(test_data)
        
        result = asyncio.run(test_verification())
        if result.get('should_post', False):
            print("✅ Content verification: Working")
        else:
            print("⚠️  Content verification: Restrictive settings")
            
    except Exception as e:
        print(f"❌ Content verification check failed: {e}")
        error_handler.handle_error(e, "Content verification diagnostics")
        all_checks_passed = False
    
    # 6. Rate Limit Check
    print("\n6️⃣ Rate Limit Check...")
    try:
        from modules.rate_limit_manager import rate_manager
        best_account = rate_manager.get_best_account()
        if best_account:
            print(f"✅ Rate limits: Account {best_account} available")
        else:
            wait_time = rate_manager.get_wait_time()
            print(f"⚠️  Rate limits: All accounts limited, wait {wait_time//60} minutes")
            
    except Exception as e:
        print(f"❌ Rate limit check failed: {e}")
        error_handler.handle_error(e, "Rate limit diagnostics")
        all_checks_passed = False
    
    # Final Report
    print("\n" + "=" * 50)
    if all_checks_passed:
        print("✅ ALL DIAGNOSTICS PASSED")
        print("🚀 System ready for operation")
        return 0
    else:
        print("❌ SOME DIAGNOSTICS FAILED")
        print("🛠️  Fix issues before running workflows")
        print("📋 Check error_log.json for detailed error history")
        return 1

if __name__ == "__main__":
    exit_code = run_comprehensive_diagnostics()
    sys.exit(exit_code)
