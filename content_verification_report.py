
#!/usr/bin/env python3
"""
Content Verification Report Generator
Shows accuracy scores and verification history
"""

import json
import os
from datetime import datetime, timedelta
from modules.content_verification import ContentVerifier

def generate_verification_report():
    """Generate a comprehensive verification report."""
    print("📊 CONTENT VERIFICATION REPORT")
    print("=" * 50)
    
    verifier = ContentVerifier()
    
    if not os.path.exists('content_verification_cache.json'):
        print("❌ No verification data found")
        return
        
    try:
        with open('content_verification_cache.json', 'r') as f:
            cache_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading verification cache: {e}")
        return
    
    # Analyze YouTube video verifications
    youtube_verifications = {k: v for k, v in cache_data.items() if k.startswith('youtube_')}
    
    if youtube_verifications:
        print("\n🎥 YOUTUBE VIDEO VERIFICATION SUMMARY")
        print("-" * 40)
        
        total_videos = len(youtube_verifications)
        verified_videos = sum(1 for v in youtube_verifications.values() if v.get('verified', False))
        avg_score = sum(v.get('score', 0) for v in youtube_verifications.values()) / total_videos
        
        print(f"Total videos checked: {total_videos}")
        print(f"Verified videos: {verified_videos} ({verified_videos/total_videos*100:.1f}%)")
        print(f"Average quality score: {avg_score:.1f}/100")
        
        # Show recent verifications
        print("\n📋 Recent Video Verifications:")
        recent_verifications = sorted(
            youtube_verifications.items(), 
            key=lambda x: x[1].get('timestamp', ''), 
            reverse=True
        )[:5]
        
        for cache_key, data in recent_verifications:
            coin_name = cache_key.split('_')[-1]
            status = "✅ VERIFIED" if data.get('verified') else "❌ REJECTED"
            score = data.get('score', 0)
            reason = data.get('reason', 'No reason')
            print(f"  {coin_name.upper()}: {status} (Score: {score:.1f}) - {reason}")
    
    # Analyze price verifications
    price_verifications = {k: v for k, v in cache_data.items() if k.startswith('price_')}
    
    if price_verifications:
        print("\n💰 PRICE DATA VERIFICATION SUMMARY")
        print("-" * 40)
        
        for cache_key, data in price_verifications.items():
            coin_name = cache_key.replace('price_', '').upper()
            last_price = data.get('last_price', 0)
            timestamp = data.get('timestamp', '')
            
            if timestamp:
                try:
                    check_time = datetime.fromisoformat(timestamp)
                    time_ago = datetime.now() - check_time
                    time_str = f"{time_ago.days}d ago" if time_ago.days > 0 else f"{time_ago.seconds//3600}h ago"
                except:
                    time_str = "Unknown"
            else:
                time_str = "Unknown"
                
            print(f"  {coin_name}: ${last_price:.4f} (Last verified: {time_str})")
    
    # Content quality recommendations
    print("\n🎯 CONTENT QUALITY RECOMMENDATIONS")
    print("-" * 40)
    
    if youtube_verifications:
        low_quality_videos = [
            (k, v) for k, v in youtube_verifications.items() 
            if v.get('score', 0) < 50
        ]
        
        if low_quality_videos:
            print("⚠️  Low-quality video sources detected:")
            for cache_key, data in low_quality_videos[:3]:
                coin_name = cache_key.split('_')[-1]
                reason = data.get('reason', 'No reason')
                print(f"   • {coin_name.upper()}: {reason}")
            print("   💡 Consider finding better educational content sources")
        else:
            print("✅ All video sources meet quality standards")
    
    # Cache statistics
    print(f"\n📈 VERIFICATION CACHE STATISTICS")
    print("-" * 40)
    print(f"Total entries: {len(cache_data)}")
    print(f"YouTube verifications: {len(youtube_verifications)}")
    print(f"Price verifications: {len(price_verifications)}")
    
    # Recent activity
    recent_entries = []
    for key, data in cache_data.items():
        timestamp = data.get('timestamp', '')
        if timestamp:
            try:
                check_time = datetime.fromisoformat(timestamp)
                if datetime.now() - check_time < timedelta(hours=24):
                    recent_entries.append((key, check_time))
            except:
                pass
    
    print(f"Recent activity (24h): {len(recent_entries)} verifications")
    
    print("\n" + "=" * 50)
    print("Report generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    generate_verification_report()
