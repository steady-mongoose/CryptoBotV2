
import os
import aiohttp
import asyncio
from datetime import datetime

async def test_discord_webhook():
    """Simple test for Discord webhook posting"""
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL not set in environment variables")
        return False
    
    test_message = f"🔔 Discord Test Message - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(webhook_url, json={"content": test_message}) as response:
                if response.status == 204:
                    print("✅ Discord webhook test successful!")
                    return True
                else:
                    print(f"❌ Discord webhook failed with status: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Error testing Discord webhook: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(test_discord_webhook())
