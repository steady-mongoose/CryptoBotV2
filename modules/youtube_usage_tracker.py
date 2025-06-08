
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger('CryptoBot')

YOUTUBE_USAGE_FILE = "youtube_api_usage.json"
YOUTUBE_DAILY_QUOTA = 10000  # Free tier daily quota

class YouTubeUsageTracker:
    def __init__(self):
        self.usage_data = self.load_usage_data()
    
    def load_usage_data(self) -> Dict:
        """Load usage data from file."""
        if os.path.exists(YOUTUBE_USAGE_FILE):
            try:
                with open(YOUTUBE_USAGE_FILE, 'r') as f:
                    data = json.load(f)
                # Check if data is from today
                if data.get('date') == datetime.now().strftime('%Y-%m-%d'):
                    return data
            except Exception as e:
                logger.error(f"Error loading YouTube usage data: {e}")
        
        # Return fresh data for today
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_units_used': 0,
            'calls_made': 0,
            'quota_remaining': YOUTUBE_DAILY_QUOTA,
            'call_log': []
        }
    
    def save_usage_data(self):
        """Save usage data to file."""
        try:
            with open(YOUTUBE_USAGE_FILE, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving YouTube usage data: {e}")
    
    def track_api_call(self, operation: str, units_cost: int = 100, success: bool = True):
        """
        Track a YouTube API call.
        
        Args:
            operation: Type of operation (search, video_details, etc.)
            units_cost: API units consumed (default 100 for search)
            success: Whether the call was successful
        """
        call_info = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'units_cost': units_cost if success else 0,
            'success': success
        }
        
        self.usage_data['call_log'].append(call_info)
        if success:
            self.usage_data['total_units_used'] += units_cost
            self.usage_data['quota_remaining'] = max(0, YOUTUBE_DAILY_QUOTA - self.usage_data['total_units_used'])
        
        self.usage_data['calls_made'] += 1
        self.save_usage_data()
        
        logger.info(f"YouTube API: {operation} - Units: {units_cost}, Remaining: {self.usage_data['quota_remaining']}")
    
    def can_make_call(self, units_needed: int = 100) -> bool:
        """Check if we can make an API call without exceeding quota."""
        return self.usage_data['quota_remaining'] >= units_needed
    
    def get_usage_summary(self) -> Dict:
        """Get current usage summary."""
        percentage_used = (self.usage_data['total_units_used'] / YOUTUBE_DAILY_QUOTA) * 100
        
        return {
            'date': self.usage_data['date'],
            'total_units_used': self.usage_data['total_units_used'],
            'quota_remaining': self.usage_data['quota_remaining'],
            'percentage_used': round(percentage_used, 1),
            'calls_made': self.usage_data['calls_made'],
            'daily_quota': YOUTUBE_DAILY_QUOTA,
            'status': 'OK' if percentage_used < 80 else 'WARNING' if percentage_used < 95 else 'CRITICAL'
        }
    
    def print_usage_report(self):
        """Print a detailed usage report."""
        summary = self.get_usage_summary()
        
        print(f"\n🎥 YOUTUBE API USAGE REPORT - {summary['date']}")
        print("=" * 50)
        print(f"📊 Units Used: {summary['total_units_used']:,} / {summary['daily_quota']:,}")
        print(f"📈 Percentage: {summary['percentage_used']}%")
        print(f"🔢 API Calls: {summary['calls_made']}")
        print(f"⏳ Remaining: {summary['quota_remaining']:,} units")
        
        if summary['status'] == 'CRITICAL':
            print("🚨 CRITICAL: Very close to quota limit!")
        elif summary['status'] == 'WARNING':
            print("⚠️  WARNING: High usage detected")
        else:
            print("✅ Status: Within safe limits")
        
        # Recent calls
        recent_calls = self.usage_data['call_log'][-5:]
        if recent_calls:
            print(f"\n📋 Recent API Calls:")
            for call in recent_calls:
                status = "✅" if call['success'] else "❌"
                time_str = datetime.fromisoformat(call['timestamp']).strftime('%H:%M:%S')
                print(f"  {status} {time_str} - {call['operation']} ({call['units_cost']} units)")

# Global tracker instance
youtube_tracker = YouTubeUsageTracker()
