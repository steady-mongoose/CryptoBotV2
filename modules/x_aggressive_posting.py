
#!/usr/bin/env python3
"""
Aggressive X posting module that maximizes API usage while respecting rate limits.
Dynamically adjusts feature richness based on available API quota.
"""

import logging
from typing import Dict, List, Any
from modules.x_dual_account_manager import x_dual_manager

logger = logging.getLogger('CryptoBot')

class XAggressivePosting:
    """
    Manages aggressive but safe X posting with dynamic feature scaling.
    """

    def __init__(self):
        self.dual_manager = x_dual_manager

    def get_enhanced_posting_strategy(self, num_coins: int) -> Dict[str, Any]:
        """
        Get enhanced posting strategy based on available API quota.
        Scales features up when quota is plentiful, down when limited.
        """
        strategy = self.dual_manager.get_aggressive_posting_strategy()
        total_calls = strategy["total_calls_available"]
        
        # Calculate calls needed for basic posting
        basic_calls_needed = num_coins + 1  # 1 main + replies for each coin
        
        # Enhanced feature allocation
        enhanced_strategy = {
            "basic_posting": True,
            "enhanced_social": False,
            "enhanced_video": False,
            "research_depth": "basic",
            "calls_to_use": basic_calls_needed,
            "feature_level": "minimal"
        }
        
        if total_calls >= basic_calls_needed + 20:
            # Plenty of quota - go aggressive
            enhanced_strategy.update({
                "enhanced_social": True,
                "enhanced_video": True,
                "research_depth": "comprehensive",
                "calls_to_use": basic_calls_needed + 16,  # Extra calls for enhancements
                "feature_level": "maximum",
                "social_sources": ["x_api", "reddit", "cryptocompare", "lunarcrush"],
                "video_sources": ["youtube_premium", "rumble_enhanced"],
                "research_sources": ["defillama", "github", "coingecko_full"]
            })
        elif total_calls >= basic_calls_needed + 10:
            # Moderate quota - selective enhancements
            enhanced_strategy.update({
                "enhanced_social": True,
                "enhanced_video": False,
                "research_depth": "moderate",
                "calls_to_use": basic_calls_needed + 8,
                "feature_level": "enhanced",
                "social_sources": ["x_api", "reddit", "cryptocompare"],
                "video_sources": ["youtube_standard"],
                "research_sources": ["defillama", "coingecko_basic"]
            })
        elif total_calls >= basic_calls_needed + 5:
            # Limited quota - minimal enhancements
            enhanced_strategy.update({
                "enhanced_social": False,
                "enhanced_video": False,
                "research_depth": "basic",
                "calls_to_use": basic_calls_needed + 3,
                "feature_level": "standard",
                "social_sources": ["reddit", "cryptocompare"],
                "video_sources": ["youtube_cached"],
                "research_sources": ["defillama"]
            })
        else:
            # Very limited - absolute minimum
            enhanced_strategy.update({
                "enhanced_social": False,
                "enhanced_video": False,
                "research_depth": "minimal",
                "calls_to_use": basic_calls_needed,
                "feature_level": "minimal",
                "social_sources": ["cached_only"],
                "video_sources": ["cached_only"],
                "research_sources": ["cached_only"]
            })
        
        logger.info(f"🎯 Enhanced Strategy: {enhanced_strategy['feature_level']} ({enhanced_strategy['calls_to_use']} API calls)")
        return enhanced_strategy

    def should_use_enhanced_features(self, feature_type: str) -> bool:
        """Check if enhanced features should be used based on quota."""
        strategy = self.dual_manager.get_aggressive_posting_strategy()
        
        feature_requirements = {
            "enhanced_social": 15,    # Need 15+ calls for enhanced social
            "enhanced_video": 20,     # Need 20+ calls for enhanced video
            "comprehensive_research": 25  # Need 25+ calls for full research
        }
        
        required_calls = feature_requirements.get(feature_type, 10)
        available_calls = strategy["total_calls_available"]
        
        can_use = available_calls >= required_calls
        
        if can_use:
            logger.info(f"✅ Enhanced feature '{feature_type}' enabled ({available_calls} calls available)")
        else:
            logger.info(f"⚠️ Enhanced feature '{feature_type}' disabled (only {available_calls} calls available, need {required_calls})")
        
        return can_use

    def post_thread_with_failover(self, main_post: str, coin_posts: List[str]) -> Dict[str, Any]:
        """
        Post complete thread with dual account failover and quota tracking.
        """
        logger.info("🚀 Starting aggressive thread posting with dual account failover")
        
        # Check strategy
        strategy = self.get_enhanced_posting_strategy(len(coin_posts))
        logger.info(f"📊 Using {strategy['feature_level']} strategy with {strategy['calls_to_use']} API calls")
        
        results = {
            "main_post": None,
            "coin_posts": [],
            "total_posted": 0,
            "account_switches": 0,
            "rate_limits_hit": 0,
            "final_status": "unknown"
        }
        
        try:
            # Post main tweet
            main_result = self.dual_manager.post_with_failover(main_post)
            if main_result["success"]:
                results["main_post"] = main_result["tweet_id"]
                results["total_posted"] += 1
                logger.info(f"✅ Main post successful via Account {main_result['account_used']}")
                
                # Post replies
                previous_tweet_id = main_result["tweet_id"]
                
                for i, coin_post in enumerate(coin_posts):
                    reply_result = self.dual_manager.post_with_failover(
                        coin_post, 
                        in_reply_to_tweet_id=previous_tweet_id
                    )
                    
                    if reply_result["success"]:
                        results["coin_posts"].append({
                            "tweet_id": reply_result["tweet_id"],
                            "account_used": reply_result["account_used"],
                            "coin_index": i
                        })
                        results["total_posted"] += 1
                        previous_tweet_id = reply_result["tweet_id"]
                        logger.info(f"✅ Coin post {i+1} successful via Account {reply_result['account_used']}")
                    else:
                        results["rate_limits_hit"] += 1
                        logger.error(f"❌ Coin post {i+1} failed: {reply_result.get('error', 'Unknown error')}")
                        break
                
                # Final status
                if results["total_posted"] == len(coin_posts) + 1:
                    results["final_status"] = "complete_success"
                    logger.info(f"🎉 COMPLETE SUCCESS: Posted {results['total_posted']} tweets with dual account system")
                else:
                    results["final_status"] = "partial_success"
                    logger.warning(f"⚠️ PARTIAL SUCCESS: Posted {results['total_posted']}/{len(coin_posts) + 1} tweets")
            else:
                results["final_status"] = "main_post_failed"
                logger.error(f"❌ Main post failed: {main_result.get('error', 'Unknown error')}")
        
        except Exception as e:
            results["final_status"] = "error"
            logger.error(f"❌ Critical error in thread posting: {e}")
        
        # Log final status
        status_report = self.dual_manager.get_status_report()
        logger.info(f"\n{status_report}")
        
        return results

    def optimize_for_engagement(self, posts: List[str], strategy: Dict[str, Any]) -> List[str]:
        """
        Optimize posts for engagement based on available API quota.
        Add enhanced features when quota allows.
        """
        if strategy["feature_level"] == "maximum":
            # Add engagement optimizations
            optimized_posts = []
            for post in posts:
                # Add trending hashtags, engagement hooks, etc.
                enhanced_post = self.add_engagement_features(post, "maximum")
                optimized_posts.append(enhanced_post)
            return optimized_posts
        elif strategy["feature_level"] == "enhanced":
            # Moderate optimizations
            return [self.add_engagement_features(post, "moderate") for post in posts]
        else:
            # Minimal changes to preserve quota
            return posts

    def add_engagement_features(self, post: str, level: str) -> str:
        """Add engagement features based on optimization level."""
        if level == "maximum":
            # Add maximum engagement features
            if "🚀" not in post:
                post = "🚀 " + post
            if "#" not in post:
                post += " #CryptoAnalysis #Trading"
        elif level == "moderate":
            # Add moderate engagement features
            if "#" not in post:
                post += " #Crypto"
        
        return post

# Global instance
x_aggressive_posting = XAggressivePosting()
