
#!/usr/bin/env python3
"""
Check YouTube API usage and quota remaining.
"""

from modules.youtube_usage_tracker import youtube_tracker

def main():
    print("🎥 CHECKING YOUTUBE API USAGE")
    print("=" * 40)
    
    youtube_tracker.print_usage_report()
    
    summary = youtube_tracker.get_usage_summary()
    
    print(f"\n💡 RECOMMENDATIONS:")
    if summary['status'] == 'CRITICAL':
        print("   • STOP making YouTube API calls immediately")
        print("   • Use Rumble-only mode for today")
        print("   • Quota resets at midnight Pacific Time")
    elif summary['status'] == 'WARNING':
        print("   • Limit YouTube API calls for rest of day")
        print("   • Consider using Rumble fallback more often")
    else:
        print("   • YouTube API usage is within safe limits")
        print("   • Continue normal operation")
    
    print(f"\n🔄 QUOTA RESET: Daily quota resets at midnight Pacific Time")
    print(f"📅 Next reset: Tomorrow at 12:00 AM PT")

if __name__ == "__main__":
    main()
