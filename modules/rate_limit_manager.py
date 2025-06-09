
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger('CryptoBot')

class RateLimitManager:
    """Manages X API rate limits across multiple accounts."""
    
    def __init__(self):
        self.account_limits = {
            1: {'last_post': None, 'posts_in_window': 0, 'window_start': None},
            2: {'last_post': None, 'posts_in_window': 0, 'window_start': None}
        }
        self.posts_per_15min = 25  # Conservative limit
        
    def can_post(self, account_num: int) -> bool:
        """Check if account can post without hitting rate limits."""
        now = datetime.now()
        account = self.account_limits[account_num]
        
        # Reset window if 15 minutes passed
        if account['window_start'] and (now - account['window_start']) > timedelta(minutes=15):
            account['posts_in_window'] = 0
            account['window_start'] = now
        
        # Check if we're under the limit
        return account['posts_in_window'] < self.posts_per_15min
    
    def get_best_account(self) -> int:
        """Get the account with the most remaining capacity."""
        for account_num in [1, 2]:
            if self.can_post(account_num):
                return account_num
        return None  # All accounts rate limited
    
    def record_post(self, account_num: int):
        """Record a successful post."""
        now = datetime.now()
        account = self.account_limits[account_num]
        
        if not account['window_start']:
            account['window_start'] = now
            
        account['last_post'] = now
        account['posts_in_window'] += 1
        
    def get_wait_time(self) -> int:
        """Get recommended wait time before next attempt."""
        now = datetime.now()
        min_wait = float('inf')
        
        for account in self.account_limits.values():
            if account['window_start']:
                window_end = account['window_start'] + timedelta(minutes=15)
                wait_time = (window_end - now).total_seconds()
                min_wait = min(min_wait, max(0, wait_time))
        
        return int(min_wait) if min_wait != float('inf') else 900  # Default 15 min

# Global instance
rate_manager = RateLimitManager()
