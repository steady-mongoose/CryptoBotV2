
#!/usr/bin/env python3
"""
Standalone script to check X API rate limits and usage.
Run this before running the bot to see your current API status.
"""

import asyncio
import logging
from modules.x_rate_limits import print_x_usage_report

# Set up simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

async def main():
    """Main function to check and display X API limits."""
    print("🔍 Checking X API Rate Limits for Free Tier...")
    print("=" * 50)
    
    try:
        # Check and print usage report
        usage_info = await print_x_usage_report()
        
        print("\n" + "=" * 50)
        
        # Provide actionable advice
        if usage_info.get('status') == 'rate_limited':
            print("🚨 ACTION REQUIRED: You are currently rate limited!")
            print("   • Wait for the rate limit to reset")
            print("   • Do not run the bot until limits reset")
        elif usage_info.get('status') == 'warning':
            print("⚠️  WARNING: High API usage detected!")
            print("   • Consider running the bot less frequently")
            print("   • Monitor usage closely")
        elif usage_info.get('status') == 'ok':
            print("✅ SAFE TO PROCEED: API usage is within limits")
            print("   • Bot can run normally")
            print("   • Continue monitoring usage")
        else:
            print("❓ UNKNOWN STATUS: Could not determine limits")
            print("   • Check your API credentials")
            print("   • Verify internet connection")
        
    except Exception as e:
        print(f"❌ Error checking rate limits: {e}")
        print("   • Verify your X API credentials in Replit Secrets")
        print("   • Check your internet connection")

if __name__ == "__main__":
    asyncio.run(main())
