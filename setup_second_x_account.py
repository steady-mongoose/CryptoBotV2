
#!/usr/bin/env python3
"""
Setup guide for second X account to handle rate limits.
"""

import os

def main():
    print("🔧 Second X Account Setup Guide")
    print("=" * 40)
    print()
    
    print("📋 Required Secrets for Second Account:")
    print("   Add these in Replit Secrets (Tools → Secrets)")
    print()
    
    secrets_needed = [
        "X2_CONSUMER_KEY",
        "X2_CONSUMER_SECRET", 
        "X2_ACCESS_TOKEN",
        "X2_ACCESS_TOKEN_SECRET",
        "X2_BEARER_TOKEN"
    ]
    
    for secret in secrets_needed:
        current_value = os.getenv(secret, "NOT SET")
        status = "✅" if current_value != "NOT SET" else "❌"
        print(f"   {status} {secret}: {'[SET]' if current_value != 'NOT SET' else '[MISSING]'}")
    
    print()
    print("📝 Steps to get second account credentials:")
    print("   1. Create new X account (non-verified)")
    print("   2. Go to https://developer.twitter.com/")
    print("   3. Apply for API access with new account")
    print("   4. Create new app in X Developer Portal")
    print("   5. Generate API keys and tokens")
    print("   6. Add all credentials to Replit Secrets with X2_ prefix")
    print()
    
    print("⚠️  Second Account Limitations:")
    print("   • Non-verified accounts have lower rate limits")
    print("   • Use as backup only when primary is rate limited")
    print("   • Still subject to 1,500 tweets/month limit")
    print()
    
    print("✅ Automatic Failover:")
    print("   • Bot will try primary account first")
    print("   • If rate limited, switches to secondary")
    print("   • Prevents posting interruptions")
    
    # Check if notification system is configured
    print()
    print("📱 Optional: Notification Setup")
    print("   Add these secrets for completion alerts:")
    
    notification_secrets = [
        ("NOTIFICATION_WEBHOOK_URL", "Discord webhook for notifications"),
        ("NOTIFICATIONS_ENABLED", "Set to 'true' to enable"),
        ("SIGNAL_PHONE_NUMBER", "Future: Signal notifications"),
        ("SMS_PHONE_NUMBER", "Future: SMS notifications")
    ]
    
    for secret, description in notification_secrets:
        current_value = os.getenv(secret, "NOT SET")
        status = "✅" if current_value != "NOT SET" else "❌"
        print(f"   {status} {secret}: {description}")

if __name__ == "__main__":
    main()
