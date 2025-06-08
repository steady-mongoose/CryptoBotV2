
#!/usr/bin/env python3
"""
Definitive check: Can I post to X RIGHT NOW?
This gives a clear YES/NO answer with explicit reasons.
"""

import tweepy
from modules.api_clients import get_x_client
from datetime import datetime

def check_immediate_posting_capability():
    """
    Check if we can post to X immediately RIGHT NOW.
    Returns clear YES/NO with explicit reasons.
    """
    print("🚨 IMMEDIATE X POSTING CAPABILITY CHECK")
    print("=" * 50)
    print(f"🕐 Check time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    can_post = False
    reasons = []
    
    # Test primary account
    print("🔍 Testing Primary X Account (Account 1)...")
    try:
        client = get_x_client(posting_only=True, account_number=1)
        if not client:
            print("❌ Primary account: Failed to create client")
            reasons.append("Primary account credentials invalid")
        else:
            # Test with minimal API call
            user_info = client.get_me()
            print(f"✅ Primary account: READY (@{user_info.data.username})")
            can_post = True
            
    except tweepy.TooManyRequests:
        print("❌ Primary account: RATE LIMITED (429)")
        reasons.append("Primary account rate limited")
        
    except Exception as e:
        print(f"❌ Primary account: ERROR ({e})")
        reasons.append(f"Primary account error: {e}")
    
    # Test secondary account if primary failed
    if not can_post:
        print("\n🔍 Testing Secondary X Account (Account 2)...")
        try:
            client = get_x_client(posting_only=True, account_number=2)
            if not client:
                print("❌ Secondary account: No credentials or failed to create client")
                reasons.append("Secondary account not configured")
            else:
                user_info = client.get_me()
                print(f"✅ Secondary account: READY (@{user_info.data.username})")
                can_post = True
                reasons = []  # Clear primary account issues since secondary works
                
        except tweepy.TooManyRequests:
            print("❌ Secondary account: RATE LIMITED (429)")
            reasons.append("Secondary account also rate limited")
            
        except Exception as e:
            print(f"❌ Secondary account: ERROR ({e})")
            reasons.append(f"Secondary account error: {e}")
    
    # Final verdict
    print("\n" + "=" * 50)
    if can_post:
        print("🎉 VERDICT: YES - YOU CAN POST TO X IMMEDIATELY!")
        print("✅ At least one X account is ready and not rate limited")
        print("\n💡 RECOMMENDED ACTION:")
        print("   • Use 'Test Direct X Posting' workflow to post now")
        print("   • Or use 'Run Bot (Queue Safe)' for maximum safety")
        
    else:
        print("🚫 VERDICT: NO - CANNOT POST TO X RIGHT NOW!")
        print("❌ All X accounts are rate limited or have errors")
        print(f"\n📋 BLOCKING ISSUES:")
        for i, reason in enumerate(reasons, 1):
            print(f"   {i}. {reason}")
        
        print(f"\n💡 RECOMMENDED ACTIONS:")
        print("   • Wait for rate limits to reset (usually 15 minutes)")
        print("   • Use 'Post to Discord Only' workflow instead")
        print("   • Use 'Manual Template Failover' to generate content for later")
        print("   • Check again in 15 minutes with this script")
    
    print("\n" + "=" * 50)
    return can_post

if __name__ == "__main__":
    can_post = check_immediate_posting_capability()
    exit(0 if can_post else 1)
