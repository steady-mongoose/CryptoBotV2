
#!/usr/bin/env python3
"""
Dual X Account Manager with intelligent rate limit tracking and failover.
Maximizes API usage while strictly respecting free tier limits.
"""

import logging
import tweepy
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
import json
import os
from modules.api_clients import get_x_client

logger = logging.getLogger('CryptoBot')

class XDualAccountManager:
    """
    Manages dual X accounts with intelligent rate limit tracking.
    Automatically switches between accounts and sets timers for rate limit recovery.
    """

    def __init__(self):
        self.account_1_client = None
        self.account_2_client = None
        self.current_account = 1
        self.rate_limit_file = "x_rate_limits_tracking.json"
        self.account_limits = {
            1: {"remaining": 50, "reset_time": None, "available": True},
            2: {"remaining": 50, "reset_time": None, "available": True}
        }
        self.load_rate_limit_tracking()

    def load_rate_limit_tracking(self):
        """Load rate limit tracking from persistent storage."""
        try:
            if os.path.exists(self.rate_limit_file):
                with open(self.rate_limit_file, 'r') as f:
                    data = json.load(f)
                    for account_num in [1, 2]:
                        if str(account_num) in data:
                            account_data = data[str(account_num)]
                            self.account_limits[account_num] = {
                                "remaining": account_data.get("remaining", 50),
                                "reset_time": account_data.get("reset_time"),
                                "available": account_data.get("available", True)
                            }
                            
                            # Check if reset time has passed
                            if account_data.get("reset_time"):
                                reset_time = datetime.fromisoformat(account_data["reset_time"])
                                if datetime.now() > reset_time:
                                    self.account_limits[account_num]["remaining"] = 50
                                    self.account_limits[account_num]["available"] = True
                                    logger.info(f"Account {account_num} rate limit reset - quota restored")
                    
                    logger.info("Rate limit tracking loaded from disk")
        except Exception as e:
            logger.error(f"Error loading rate limit tracking: {e}")

    def save_rate_limit_tracking(self):
        """Save rate limit tracking to persistent storage."""
        try:
            data = {}
            for account_num in [1, 2]:
                data[str(account_num)] = {
                    "remaining": self.account_limits[account_num]["remaining"],
                    "reset_time": self.account_limits[account_num]["reset_time"],
                    "available": self.account_limits[account_num]["available"]
                }
            
            with open(self.rate_limit_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug("Rate limit tracking saved to disk")
        except Exception as e:
            logger.error(f"Error saving rate limit tracking: {e}")

    def get_client_for_account(self, account_number: int) -> Optional[tweepy.Client]:
        """Get X client for specific account number."""
        if account_number == 1:
            if not self.account_1_client:
                self.account_1_client = get_x_client(posting_only=True, account_number=1)
            return self.account_1_client
        elif account_number == 2:
            if not self.account_2_client:
                self.account_2_client = get_x_client(posting_only=True, account_number=2)
            return self.account_2_client
        return None

    def check_account_availability(self, account_number: int) -> bool:
        """Check if account is available (not rate limited)."""
        account_data = self.account_limits[account_number]
        
        # Check if reset time has passed
        if account_data["reset_time"]:
            reset_time = datetime.fromisoformat(account_data["reset_time"])
            if datetime.now() > reset_time:
                # Rate limit has reset
                account_data["remaining"] = 50
                account_data["available"] = True
                account_data["reset_time"] = None
                self.save_rate_limit_tracking()
                logger.info(f"✅ Account {account_number} rate limit automatically reset")
        
        return account_data["available"] and account_data["remaining"] > 0

    def get_best_available_account(self) -> Tuple[int, tweepy.Client]:
        """
        Get the best available account for posting.
        Returns (account_number, client) or raises exception if both rate limited.
        """
        # Try current account first
        if self.check_account_availability(self.current_account):
            client = self.get_client_for_account(self.current_account)
            if client:
                logger.info(f"✅ Using Account {self.current_account} ({self.account_limits[self.current_account]['remaining']} calls remaining)")
                return self.current_account, client

        # Try other account
        other_account = 2 if self.current_account == 1 else 1
        if self.check_account_availability(other_account):
            client = self.get_client_for_account(other_account)
            if client:
                self.current_account = other_account
                logger.info(f"🔄 Switched to Account {other_account} ({self.account_limits[other_account]['remaining']} calls remaining)")
                return other_account, client

        # Both accounts are rate limited
        self.handle_dual_rate_limit()
        raise Exception("Both X accounts are rate limited - waiting for reset")

    def handle_dual_rate_limit(self):
        """Handle scenario where both accounts are rate limited."""
        account_1_reset = self.account_limits[1]["reset_time"]
        account_2_reset = self.account_limits[2]["reset_time"]
        
        # Find earliest reset time
        earliest_reset = None
        earliest_account = None
        
        if account_1_reset:
            reset_1 = datetime.fromisoformat(account_1_reset)
            if not earliest_reset or reset_1 < earliest_reset:
                earliest_reset = reset_1
                earliest_account = 1
        
        if account_2_reset:
            reset_2 = datetime.fromisoformat(account_2_reset)
            if not earliest_reset or reset_2 < earliest_reset:
                earliest_reset = reset_2
                earliest_account = 2
        
        if earliest_reset:
            wait_time = (earliest_reset - datetime.now()).total_seconds()
            if wait_time > 0:
                logger.warning(f"🚫 BOTH X accounts rate limited!")
                logger.warning(f"⏰ Account {earliest_account} resets in {wait_time/60:.1f} minutes")
                logger.warning(f"🕐 Reset time: {earliest_reset.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Set timer and wait if reasonable time
                if wait_time <= 900:  # Wait up to 15 minutes
                    logger.info(f"⏳ Setting timer for {wait_time/60:.1f} minutes...")
                    time.sleep(wait_time + 30)  # Add 30 second buffer
                    
                    # Reset the account
                    self.account_limits[earliest_account]["remaining"] = 50
                    self.account_limits[earliest_account]["available"] = True
                    self.account_limits[earliest_account]["reset_time"] = None
                    self.current_account = earliest_account
                    self.save_rate_limit_tracking()
                    
                    logger.info(f"✅ Account {earliest_account} rate limit reset - ready to post")
                else:
                    logger.warning(f"⏰ Wait time too long ({wait_time/3600:.1f} hours) - using queue system")

    def update_rate_limit(self, account_number: int, remaining_calls: int, reset_time: datetime = None):
        """Update rate limit information for an account."""
        self.account_limits[account_number]["remaining"] = remaining_calls
        
        if remaining_calls <= 0:
            self.account_limits[account_number]["available"] = False
            if reset_time:
                self.account_limits[account_number]["reset_time"] = reset_time.isoformat()
            else:
                # Default 15 minute reset for free tier
                reset_time = datetime.now() + timedelta(minutes=15)
                self.account_limits[account_number]["reset_time"] = reset_time.isoformat()
            
            logger.warning(f"❌ Account {account_number} rate limited - resets at {reset_time.strftime('%H:%M:%S')}")
        
        self.save_rate_limit_tracking()

    def handle_rate_limit_error(self, account_number: int, error: tweepy.TooManyRequests):
        """Handle rate limit error from X API."""
        # Extract reset time from error if possible
        reset_time = datetime.now() + timedelta(minutes=15)  # Default
        
        try:
            if hasattr(error, 'response') and error.response:
                reset_timestamp = error.response.headers.get('x-rate-limit-reset')
                if reset_timestamp:
                    reset_time = datetime.fromtimestamp(int(reset_timestamp))
        except:
            pass
        
        self.update_rate_limit(account_number, 0, reset_time)
        logger.error(f"🚫 Account {account_number} hit rate limit - switching accounts")

    def can_make_api_call(self, account_number: int) -> bool:
        """Check if account can make an API call."""
        return self.check_account_availability(account_number)

    def use_api_call(self, account_number: int):
        """Record usage of an API call."""
        if self.account_limits[account_number]["remaining"] > 0:
            self.account_limits[account_number]["remaining"] -= 1
            self.save_rate_limit_tracking()
            
            remaining = self.account_limits[account_number]["remaining"]
            if remaining <= 5:
                logger.warning(f"⚠️ Account {account_number} low on API calls: {remaining} remaining")
            elif remaining <= 1:
                logger.error(f"🚨 Account {account_number} almost depleted: {remaining} calls left")

    def get_aggressive_posting_strategy(self) -> Dict[str, Any]:
        """
        Get strategy for aggressive but safe API usage.
        Returns recommendations for how many API calls to use.
        """
        total_remaining = sum(acc["remaining"] for acc in self.account_limits.values() if acc["available"])
        
        strategy = {
            "total_calls_available": total_remaining,
            "recommended_usage": "conservative",
            "enhanced_features": False,
            "social_api_calls": 0,
            "video_api_calls": 0
        }
        
        if total_remaining >= 30:
            strategy.update({
                "recommended_usage": "aggressive",
                "enhanced_features": True,
                "social_api_calls": 2,  # Extra social metrics
                "video_api_calls": 2    # Enhanced video search
            })
        elif total_remaining >= 15:
            strategy.update({
                "recommended_usage": "moderate",
                "enhanced_features": True,
                "social_api_calls": 1,
                "video_api_calls": 1
            })
        elif total_remaining >= 5:
            strategy.update({
                "recommended_usage": "conservative",
                "enhanced_features": False,
                "social_api_calls": 0,
                "video_api_calls": 0
            })
        else:
            strategy.update({
                "recommended_usage": "minimal",
                "enhanced_features": False,
                "social_api_calls": 0,
                "video_api_calls": 0
            })
        
        logger.info(f"📊 API Strategy: {strategy['recommended_usage']} (Total calls: {total_remaining})")
        return strategy

    def post_with_failover(self, text: str, in_reply_to_tweet_id: str = None) -> Dict[str, Any]:
        """
        Post to X with automatic account failover.
        Returns posting result with account used.
        """
        max_attempts = 2  # Try both accounts
        attempt = 0
        
        while attempt < max_attempts:
            try:
                account_number, client = self.get_best_available_account()
                
                # Make the post
                if in_reply_to_tweet_id:
                    tweet = client.create_tweet(text=text, in_reply_to_tweet_id=in_reply_to_tweet_id)
                else:
                    tweet = client.create_tweet(text=text)
                
                # Update usage
                self.use_api_call(account_number)
                
                logger.info(f"✅ Posted to X via Account {account_number} (ID: {tweet.data['id']})")
                return {
                    "success": True,
                    "tweet_id": tweet.data['id'],
                    "account_used": account_number,
                    "remaining_calls": self.account_limits[account_number]["remaining"]
                }
                
            except tweepy.TooManyRequests as e:
                self.handle_rate_limit_error(account_number, e)
                attempt += 1
                
                if attempt < max_attempts:
                    logger.info(f"🔄 Attempting failover to other account...")
                    continue
                else:
                    logger.error("🚫 Both accounts rate limited - post failed")
                    return {"success": False, "error": "Both accounts rate limited"}
                    
            except Exception as e:
                logger.error(f"❌ Error posting to Account {account_number}: {e}")
                attempt += 1
                
                if attempt < max_attempts:
                    # Try other account
                    other_account = 2 if account_number == 1 else 1
                    if self.check_account_availability(other_account):
                        self.current_account = other_account
                        continue
                
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "All posting attempts failed"}

    def get_status_report(self) -> str:
        """Get detailed status report of both accounts."""
        report = ["📊 X API Dual Account Status:"]
        
        for account_num in [1, 2]:
            data = self.account_limits[account_num]
            status_emoji = "✅" if data["available"] else "🚫"
            
            report.append(f"{status_emoji} Account {account_num}: {data['remaining']} calls remaining")
            
            if data["reset_time"]:
                reset_time = datetime.fromisoformat(data["reset_time"])
                if reset_time > datetime.now():
                    time_until_reset = (reset_time - datetime.now()).total_seconds() / 60
                    report.append(f"   ⏰ Resets in {time_until_reset:.1f} minutes")
                else:
                    report.append(f"   ✅ Reset time passed - should be available")
        
        total_calls = sum(acc["remaining"] for acc in self.account_limits.values() if acc["available"])
        report.append(f"📈 Total available calls: {total_calls}")
        
        strategy = self.get_aggressive_posting_strategy()
        report.append(f"🎯 Recommended strategy: {strategy['recommended_usage']}")
        
        return "\n".join(report)

# Global instance
x_dual_manager = XDualAccountManager()
