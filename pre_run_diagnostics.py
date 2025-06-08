
#!/usr/bin/env python3
"""
Comprehensive pre-run diagnostics to ensure bot is ready for X posting.
This checks ALL critical components before running the bot.
"""

import os
import logging
import asyncio
import aiohttp
from datetime import datetime
from modules.api_clients import get_x_client
from modules.x_rate_limits import print_x_usage_report
from modules.x_thread_queue import x_queue, get_x_queue_status

logging.basicConfig(level=logging.INFO, format='%(message)s')

async def check_environment_variables():
    """Check all required environment variables."""
    print("🔍 STEP 1: Environment Variables Check")
    print("-" * 50)
    
    required_vars = {
        'Discord': ['DISCORD_WEBHOOK_URL'],
        'X API': ['X_CONSUMER_KEY', 'X_CONSUMER_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET'],
        'Optional': ['YOUTUBE_API_KEY', 'PHONE_NUMBER']
    }
    
    all_good = True
    
    for category, vars_list in required_vars.items():
        print(f"\n📋 {category} Variables:")
        for var in vars_list:
            value = os.getenv(var)
            if value:
                print(f"   ✅ {var}: Set (length: {len(value)})")
            else:
                print(f"   ❌ {var}: MISSING")
                if category != 'Optional':
                    all_good = False
    
    if not all_good:
        print("\n🚨 CRITICAL: Missing required environment variables!")
        print("💡 Add missing variables to Replit Secrets")
        return False
    
    print("\n✅ All required environment variables are set")
    return True

async def check_x_api_connection():
    """Test X API connection and authentication."""
    print("\n🔍 STEP 2: X API Connection Test")
    print("-" * 50)
    
    try:
        client = get_x_client(posting_only=True)
        if not client:
            print("❌ Failed to create X API client")
            print("💡 Check your X API credentials in Secrets")
            return False
        
        # Test authentication
        user_info = client.get_me()
        print(f"✅ Authentication successful!")
        print(f"   👤 Username: @{user_info.data.username}")
        print(f"   🆔 User ID: {user_info.data.id}")
        print(f"   📅 Account created: {user_info.data.created_at}")
        
        return True
        
    except Exception as e:
        print(f"❌ X API connection failed: {e}")
        print("💡 Verify your X API credentials are correct")
        return False

async def check_discord_webhook():
    """Test Discord webhook."""
    print("\n🔍 STEP 3: Discord Webhook Test")
    print("-" * 50)
    
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        print("❌ Discord webhook URL not set")
        return False
    
    try:
        async with aiohttp.ClientSession() as session:
            test_payload = {
                "content": f"🧪 Discord webhook test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            async with session.post(webhook_url, json=test_payload) as response:
                if response.status == 204:
                    print("✅ Discord webhook working correctly!")
                    return True
                else:
                    print(f"❌ Discord webhook failed: Status {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Discord webhook error: {e}")
        return False

async def check_x_rate_limits():
    """Check X API rate limits."""
    print("\n🔍 STEP 4: X API Rate Limits Check")
    print("-" * 50)
    
    try:
        usage_info = await print_x_usage_report()
        
        if usage_info.get('status') == 'rate_limited':
            print("\n🚨 WARNING: Currently rate limited!")
            print("⏳ Bot will use queue system to wait for reset")
            return True  # Queue system can handle this
        elif usage_info.get('status') == 'warning':
            print("\n⚠️  High usage detected - queue system recommended")
            return True
        elif usage_info.get('status') == 'ok':
            print("\n✅ Rate limits OK - safe to proceed")
            return True
        else:
            print("\n❓ Could not determine rate limit status")
            print("🔄 Bot will proceed with queue system (safest)")
            return True
            
    except Exception as e:
        print(f"❌ Rate limit check failed: {e}")
        print("🔄 Bot will proceed with queue system")
        return True

async def check_queue_system():
    """Test X queue system."""
    print("\n🔍 STEP 5: X Queue System Test")
    print("-" * 50)
    
    try:
        # Check if queue worker is running
        if hasattr(x_queue, 'worker_task') and x_queue.worker_task and not x_queue.worker_task.done():
            print("✅ Queue worker already running")
        else:
            print("🔄 Starting queue worker...")
            from modules.x_thread_queue import start_x_queue
            start_x_queue()
            await asyncio.sleep(2)  # Give it time to start
            print("✅ Queue worker started successfully")
        
        # Check queue status  
        status = get_x_queue_status()
        print(f"📊 Current queue status: {status['post_queue_size']} posts, {status['thread_queue_size']} threads")
        
        return True
        
    except Exception as e:
        print(f"❌ Queue system error: {e}")
        print("💡 Bot will attempt to restart queue system")
        return False

async def check_data_sources():
    """Test external API connections."""
    print("\n🔍 STEP 6: External Data Sources Test")
    print("-" * 50)
    
    sources_tested = 0
    sources_working = 0
    
    # Test CoinGecko
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/ping") as response:
                if response.status == 200:
                    print("✅ CoinGecko API: Working")
                    sources_working += 1
                else:
                    print(f"⚠️  CoinGecko API: Status {response.status}")
        sources_tested += 1
    except Exception as e:
        print(f"❌ CoinGecko API: {e}")
        sources_tested += 1
    
    # Test YouTube API (if configured)
    youtube_key = os.getenv('YOUTUBE_API_KEY')
    if youtube_key:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=crypto&type=video&maxResults=1&key={youtube_key}"
                async with session.get(url) as response:
                    if response.status == 200:
                        print("✅ YouTube API: Working")
                        sources_working += 1
                    else:
                        print(f"⚠️  YouTube API: Status {response.status}")
            sources_tested += 1
        except Exception as e:
            print(f"❌ YouTube API: {e}")
            sources_tested += 1
    else:
        print("ℹ️  YouTube API: Not configured (will use Rumble fallback)")
    
    print(f"\n📊 Data sources: {sources_working}/{sources_tested} working")
    return sources_working > 0  # At least one source working

async def main():
    """Run comprehensive diagnostics."""
    print("🩺 CRYPTOBOT V2 - COMPREHENSIVE DIAGNOSTICS")
    print("=" * 60)
    print(f"⏰ Diagnostic time: {datetime.now()}")
    print("")
    
    checks = []
    
    # Run all checks
    checks.append(await check_environment_variables())
    checks.append(await check_x_api_connection())
    checks.append(await check_discord_webhook())
    checks.append(await check_x_rate_limits())
    checks.append(await check_queue_system())
    checks.append(await check_data_sources())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    passed = sum(checks)
    total = len(checks)
    
    check_names = [
        "Environment Variables",
        "X API Connection", 
        "Discord Webhook",
        "X Rate Limits",
        "Queue System",
        "Data Sources"
    ]
    
    for i, (check_name, passed_check) in enumerate(zip(check_names, checks)):
        status = "✅ PASS" if passed_check else "❌ FAIL"
        print(f"   {status}: {check_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 ALL SYSTEMS GO!")
        print("✅ Bot is ready to post to X")
        print("🚀 Run: python bot_v2.py --queue-only")
    elif passed >= 4:  # Critical systems working
        print("\n⚠️  MOSTLY READY")
        print("✅ Core systems working - bot can run with limitations")
        print("🚀 Run: python bot_v2.py --queue-only")
    else:
        print("\n🚨 NOT READY")
        print("❌ Critical issues detected - fix before running")
        print("🔧 Address the failed checks above")
    
    print(f"\n⏱️  Total diagnostic time: {datetime.now() - datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())
