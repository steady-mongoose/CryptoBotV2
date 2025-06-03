
import tweepy
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from modules.api_clients import get_x_client

logger = logging.getLogger('CryptoBot')

class XRateLimitChecker:
    """Monitor X API rate limits for free tier compliance."""
    
    def __init__(self):
        self.client = None
        self.last_check = None
        self.rate_limits = {}
    
    async def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status from X API."""
        try:
            if not self.client:
                self.client = get_x_client()
            
            # Get rate limit status
            rate_limit_response = self.client.get_rate_limit_status()
            
            if not rate_limit_response.data:
                logger.error("No rate limit data received from X API")
                return {}
            
            # Extract relevant rate limits for free tier
            resources = rate_limit_response.data.get('resources', {})
            
            rate_limits = {}
            
            # Tweet limits
            if 'statuses' in resources:
                statuses = resources['statuses']
                if '/statuses/update' in statuses:
                    tweet_limit = statuses['/statuses/update']
                    rate_limits['tweets'] = {
                        'limit': tweet_limit.get('limit', 0),
                        'remaining': tweet_limit.get('remaining', 0),
                        'reset': datetime.fromtimestamp(tweet_limit.get('reset', 0))
                    }
            
            # Search limits (often disabled on free tier)
            if 'search' in resources:
                search = resources['search']
                if '/search/tweets' in search:
                    search_limit = search['/search/tweets']
                    rate_limits['search'] = {
                        'limit': search_limit.get('limit', 0),
                        'remaining': search_limit.get('remaining', 0),
                        'reset': datetime.fromtimestamp(search_limit.get('reset', 0))
                    }
            
            # User lookup limits
            if 'users' in resources:
                users = resources['users']
                if '/users/by/username/:username' in users:
                    user_limit = users['/users/by/username/:username']
                    rate_limits['user_lookup'] = {
                        'limit': user_limit.get('limit', 0),
                        'remaining': user_limit.get('remaining', 0),
                        'reset': datetime.fromtimestamp(user_limit.get('reset', 0))
                    }
            
            self.rate_limits = rate_limits
            self.last_check = datetime.now()
            
            return rate_limits
            
        except tweepy.Unauthorized:
            logger.error("X API unauthorized - check credentials")
            return {}
        except tweepy.Forbidden:
            logger.error("X API forbidden - may be free tier limitation")
            return {}
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {}
    
    async def check_daily_usage(self) -> Dict:
        """Check daily usage for free tier (1,500 tweets/month = ~50/day)."""
        rate_limits = await self.get_rate_limit_status()
        
        if not rate_limits:
            return {
                'status': 'unknown',
                'message': 'Could not retrieve rate limit data'
            }
        
        # Free tier monthly limits
        FREE_TIER_MONTHLY_TWEETS = 1500
        FREE_TIER_DAILY_ESTIMATE = FREE_TIER_MONTHLY_TWEETS // 30  # ~50 per day
        
        usage_info = {
            'daily_estimate_limit': FREE_TIER_DAILY_ESTIMATE,
            'monthly_limit': FREE_TIER_MONTHLY_TWEETS,
            'endpoints': {}
        }
        
        # Check tweet limits
        if 'tweets' in rate_limits:
            tweet_data = rate_limits['tweets']
            tweets_used_in_window = tweet_data['limit'] - tweet_data['remaining']
            
            usage_info['endpoints']['tweets'] = {
                'limit_per_window': tweet_data['limit'],
                'remaining_in_window': tweet_data['remaining'],
                'used_in_window': tweets_used_in_window,
                'window_resets_at': tweet_data['reset'].strftime('%Y-%m-%d %H:%M:%S'),
                'percentage_used': (tweets_used_in_window / tweet_data['limit']) * 100 if tweet_data['limit'] > 0 else 0
            }
        
        # Check search limits
        if 'search' in rate_limits:
            search_data = rate_limits['search']
            usage_info['endpoints']['search'] = {
                'limit_per_window': search_data['limit'],
                'remaining_in_window': search_data['remaining'],
                'used_in_window': search_data['limit'] - search_data['remaining'],
                'window_resets_at': search_data['reset'].strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            usage_info['endpoints']['search'] = {
                'status': 'disabled',
                'note': 'Search typically disabled on free tier'
            }
        
        # Determine overall status
        if 'tweets' in usage_info['endpoints']:
            tweet_info = usage_info['endpoints']['tweets']
            if tweet_info['remaining_in_window'] == 0:
                usage_info['status'] = 'rate_limited'
                usage_info['message'] = f"Rate limited until {tweet_info['window_resets_at']}"
            elif tweet_info['percentage_used'] > 80:
                usage_info['status'] = 'warning'
                usage_info['message'] = f"High usage: {tweet_info['percentage_used']:.1f}% of rate limit used"
            else:
                usage_info['status'] = 'ok'
                usage_info['message'] = f"Rate limit OK: {tweet_info['remaining_in_window']} tweets remaining"
        else:
            usage_info['status'] = 'unknown'
            usage_info['message'] = 'Could not determine tweet rate limit status'
        
        return usage_info
    
    def format_usage_report(self, usage_info: Dict) -> str:
        """Format usage information into a readable report."""
        if not usage_info or usage_info.get('status') == 'unknown':
            return "❌ Could not retrieve X API usage information"
        
        report = []
        report.append("📊 X API Free Tier Usage Report")
        report.append("=" * 40)
        
        # Overall status
        status_emoji = {
            'ok': '✅',
            'warning': '⚠️',
            'rate_limited': '🚫',
            'unknown': '❓'
        }
        
        emoji = status_emoji.get(usage_info['status'], '❓')
        report.append(f"{emoji} Status: {usage_info['message']}")
        report.append("")
        
        # Free tier limits
        report.append(f"📅 Free Tier Limits:")
        report.append(f"   • Monthly tweets: {usage_info['monthly_limit']:,}")
        report.append(f"   • Estimated daily: {usage_info['daily_estimate_limit']}")
        report.append("")
        
        # Endpoint details
        if 'endpoints' in usage_info:
            for endpoint, data in usage_info['endpoints'].items():
                if endpoint == 'tweets' and isinstance(data, dict) and 'limit_per_window' in data:
                    report.append(f"🐦 Tweet Endpoint (15-min window):")
                    report.append(f"   • Limit: {data['limit_per_window']}")
                    report.append(f"   • Used: {data['used_in_window']}")
                    report.append(f"   • Remaining: {data['remaining_in_window']}")
                    report.append(f"   • Usage: {data['percentage_used']:.1f}%")
                    report.append(f"   • Resets: {data['window_resets_at']}")
                    report.append("")
                
                elif endpoint == 'search':
                    if data.get('status') == 'disabled':
                        report.append(f"🔍 Search Endpoint: {data['note']}")
                    else:
                        report.append(f"🔍 Search Endpoint:")
                        report.append(f"   • Remaining: {data['remaining_in_window']}")
                        report.append(f"   • Resets: {data['window_resets_at']}")
                    report.append("")
        
        # Recommendations
        report.append("💡 Recommendations:")
        if usage_info['status'] == 'rate_limited':
            report.append("   • Wait for rate limit reset before posting")
            report.append("   • Consider spacing out posts more")
        elif usage_info['status'] == 'warning':
            report.append("   • Reduce posting frequency")
            report.append("   • Consider upgrading to paid tier")
        else:
            report.append("   • Current usage is within safe limits")
            report.append("   • Continue monitoring before major posting")
        
        return "\n".join(report)

# Global instance
rate_limit_checker = XRateLimitChecker()

async def check_x_rate_limits() -> Dict:
    """Convenience function to check X API rate limits."""
    return await rate_limit_checker.check_daily_usage()

async def print_x_usage_report():
    """Print formatted X API usage report."""
    usage_info = await check_x_rate_limits()
    report = rate_limit_checker.format_usage_report(usage_info)
    print(report)
    logger.info("X API usage report generated")
    return usage_info
