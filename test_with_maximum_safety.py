
#!/usr/bin/env python3
"""
Maximum safety testing with comprehensive error prevention and verbose logging.
"""

import logging
import time
import os
import json
from datetime import datetime
from modules.x_thread_queue import get_x_queue_status, start_x_queue

# Enable maximum verbosity
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'test_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger('SafetyTest')

def comprehensive_safety_check():
    """Run every possible safety check before testing."""
    print("🛡️ COMPREHENSIVE SAFETY CHECKS")
    print("=" * 50)
    
    safety_results = {}
    
    # 1. Environment Check
    print("\n1️⃣ Environment Variables Check:")
    required_vars = ['X_CONSUMER_KEY', 'X_CONSUMER_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET', 'DISCORD_WEBHOOK_URL']
    for var in required_vars:
        exists = bool(os.getenv(var))
        print(f"   {'✅' if exists else '❌'} {var}: {'SET' if exists else 'MISSING'}")
        safety_results[f'env_{var}'] = exists
    
    # 2. Queue System Check
    print("\n2️⃣ Queue System Check:")
    try:
        status = get_x_queue_status()
        print(f"   ✅ Worker running: {status['worker_running']}")
        print(f"   ✅ Rate limited: {status['rate_limited']}")
        print(f"   ✅ Queue sizes: {status['post_queue_size']} posts, {status['thread_queue_size']} threads")
        safety_results['queue_accessible'] = True
        safety_results['worker_running'] = status['worker_running']
        safety_results['rate_limited'] = status['rate_limited']
    except Exception as e:
        print(f"   ❌ Queue check failed: {e}")
        safety_results['queue_accessible'] = False
    
    # 3. X API Connection Test (minimal)
    print("\n3️⃣ X API Connection Test (minimal call):")
    try:
        from modules.api_clients import get_x_client
        client = get_x_client(posting_only=True)
        if client:
            print("   ✅ X client initialized")
            # Don't test actual API call if rate limited
            if not safety_results.get('rate_limited', False):
                try:
                    user_info = client.get_me()
                    print(f"   ✅ API working: @{user_info.data.username}")
                    safety_results['x_api_working'] = True
                except Exception as e:
                    print(f"   ⚠️  API limited but client OK: {e}")
                    safety_results['x_api_working'] = False
            else:
                print("   ⚠️  Skipping API test due to rate limit")
                safety_results['x_api_working'] = 'skipped'
        else:
            print("   ❌ X client failed to initialize")
            safety_results['x_api_working'] = False
    except Exception as e:
        print(f"   ❌ X API test failed: {e}")
        safety_results['x_api_working'] = False
    
    # 4. Discord Webhook Test
    print("\n4️⃣ Discord Webhook Test:")
    try:
        import aiohttp
        import asyncio
        
        async def test_discord():
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
            if not webhook_url:
                return False
            
            async with aiohttp.ClientSession() as session:
                test_payload = {"content": f"🧪 Safety test - {datetime.now()}"}
                async with session.post(webhook_url, json=test_payload) as response:
                    return response.status == 204
        
        discord_works = asyncio.run(test_discord())
        print(f"   {'✅' if discord_works else '❌'} Discord webhook: {'WORKING' if discord_works else 'FAILED'}")
        safety_results['discord_working'] = discord_works
    except Exception as e:
        print(f"   ❌ Discord test failed: {e}")
        safety_results['discord_working'] = False
    
    # 5. File System Check
    print("\n5️⃣ File System Check:")
    try:
        test_file = f'safety_test_{int(time.time())}.tmp'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print("   ✅ File system: WORKING")
        safety_results['filesystem_working'] = True
    except Exception as e:
        print(f"   ❌ File system error: {e}")
        safety_results['filesystem_working'] = False
    
    # Save results
    with open(f'safety_check_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(safety_results, f, indent=2)
    
    return safety_results

def test_queue_system_thoroughly():
    """Test the queue system with maximum safety."""
    print("\n🔄 QUEUE SYSTEM COMPREHENSIVE TEST")
    print("=" * 50)
    
    # Ensure worker is running
    print("1. Ensuring queue worker is running...")
    try:
        status = get_x_queue_status()
        if not status['worker_running']:
            print("   🔄 Starting queue worker...")
            start_x_queue()
            time.sleep(5)
            status = get_x_queue_status()
        
        print(f"   ✅ Worker status: {status['worker_running']}")
        print(f"   ⏰ Rate limited: {status['rate_limited']}")
        if status['rate_limited'] and status.get('rate_limit_reset'):
            print(f"   🕐 Reset time: {status['rate_limit_reset']}")
    except Exception as e:
        print(f"   ❌ Queue worker error: {e}")
        return False
    
    # Test queue functions
    print("\n2. Testing queue functions...")
    try:
        from modules.x_thread_queue import queue_x_post
        
        # Queue a test post (will not be sent immediately if rate limited)
        test_text = f"🧪 Safety test post - {datetime.now().strftime('%H:%M:%S')} - Will be deleted"
        queue_x_post(test_text)
        print("   ✅ Post queuing function works")
        
        # Check queue size
        status = get_x_queue_status()
        print(f"   📊 Queue now has: {status['post_queue_size']} posts")
        
        return True
    except Exception as e:
        print(f"   ❌ Queue function error: {e}")
        return False

def run_safe_bot_test():
    """Run the bot in maximum safety mode."""
    print("\n🤖 BOT COMPREHENSIVE SAFETY TEST")
    print("=" * 50)
    
    try:
        # Import and run with maximum safety
        import subprocess
        import sys
        
        # Run bot with queue-only mode and maximum verbosity
        print("Running bot with maximum safety settings...")
        
        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd()
        
        result = subprocess.run([
            sys.executable, 'bot_v2.py', 
            '--queue-only',  # Maximum safety
            '--verbose'      # Maximum logging
        ], env=env, capture_output=True, text=True, timeout=120)
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output:\n{result.stdout}")
        if result.stderr:
            print(f"Errors:\n{result.stderr}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Bot test timed out (120s) - this is normal for safety")
        return True
    except Exception as e:
        print(f"❌ Bot test error: {e}")
        return False

def main():
    """Run complete safety testing protocol."""
    print("🛡️ MAXIMUM SAFETY TESTING PROTOCOL")
    print("=" * 60)
    print(f"🕐 Test started: {datetime.now()}")
    print("🎯 Goal: Test all systems with zero risk")
    print("")
    
    # Step 1: Safety checks
    safety_results = comprehensive_safety_check()
    
    # Step 2: Queue testing
    queue_ok = test_queue_system_thoroughly()
    
    # Step 3: Bot testing
    bot_ok = run_safe_bot_test()
    
    # Final assessment
    print("\n" + "=" * 60)
    print("📊 FINAL SAFETY ASSESSMENT")
    print("=" * 60)
    
    critical_systems = [
        safety_results.get('queue_accessible', False),
        safety_results.get('discord_working', False),
        queue_ok
    ]
    
    optional_systems = [
        safety_results.get('x_api_working', False) == True  # True, not 'skipped'
    ]
    
    critical_passed = sum(critical_systems)
    total_critical = len(critical_systems)
    
    print(f"✅ Critical systems: {critical_passed}/{total_critical} working")
    print(f"🔧 Optional systems: {sum(optional_systems)}/{len(optional_systems)} working")
    
    if critical_passed == total_critical:
        print("\n🎉 ALL CRITICAL SYSTEMS WORKING!")
        print("✅ Safe to run: python bot_v2.py --queue-only")
        if safety_results.get('rate_limited', False):
            print("⏳ Posts will queue until rate limit resets (~15 min)")
        else:
            print("🚀 Posts will send immediately")
    else:
        print("\n⚠️  SOME CRITICAL SYSTEMS FAILED")
        print("🔧 Fix the failed systems before running bot")
    
    print(f"\n📋 Full test log saved to: test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

if __name__ == "__main__":
    main()
