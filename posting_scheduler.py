
import time
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('CryptoBot')

class PostingScheduler:
    """Optimize posting times for maximum engagement and monetization."""
    
    def __init__(self):
        # Peak engagement times (EST/PST optimized)
        self.peak_times = [
            {'hour': 7, 'minute': 30, 'engagement_multiplier': 1.4},   # Morning commute
            {'hour': 12, 'minute': 0, 'engagement_multiplier': 1.3},   # Lunch break
            {'hour': 17, 'minute': 30, 'engagement_multiplier': 1.5},  # After work
            {'hour': 20, 'minute': 0, 'engagement_multiplier': 1.2},   # Evening
        ]
    
    def get_optimal_posting_time(self):
        """Get next optimal posting time for maximum engagement."""
        now = datetime.now()
        
        # Find next peak time
        for peak in self.peak_times:
            next_peak = now.replace(hour=peak['hour'], minute=peak['minute'], second=0, microsecond=0)
            
            # If today's peak has passed, try tomorrow
            if next_peak <= now:
                next_peak += timedelta(days=1)
            else:
                return next_peak, peak['engagement_multiplier']
        
        # Default to next morning if no peaks today
        next_morning = (now + timedelta(days=1)).replace(hour=7, minute=30, second=0, microsecond=0)
        return next_morning, 1.4
    
    def should_post_now(self):
        """Check if current time is optimal for posting."""
        now = datetime.now()
        
        for peak in self.peak_times:
            peak_time = now.replace(hour=peak['hour'], minute=peak['minute'], second=0, microsecond=0)
            
            # Allow 30-minute window around peak times
            window_start = peak_time - timedelta(minutes=15)
            window_end = peak_time + timedelta(minutes=15)
            
            if window_start <= now <= window_end:
                logger.info(f"✅ Optimal posting time detected: {peak['engagement_multiplier']}x engagement expected")
                return True, peak['engagement_multiplier']
        
        return False, 1.0
    
    def get_hashtag_strategy(self, hour):
        """Get trending hashtags based on time of day."""
        if 6 <= hour <= 10:
            return "#MorningCrypto #CoffeeAndCoins #TradingView"
        elif 11 <= hour <= 14:
            return "#LunchBreakTrading #CryptoNews #MarketUpdate"
        elif 15 <= hour <= 19:
            return "#AfterHoursTrading #CryptoGains #TradingSignals"
        else:
            return "#EveningAnalysis #CryptoNight #TomorrowsPlays"

# Global scheduler instance
posting_scheduler = PostingScheduler()
