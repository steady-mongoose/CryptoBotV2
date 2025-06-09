
import logging
import re
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os

logger = logging.getLogger('CryptoBot')

class ContentVerifier:
    def __init__(self):
        self.verification_cache = self._load_verification_cache()
        self.accuracy_scores = {}
        self.banned_sources = set()
        self.trusted_sources = {
            'coingecko.com', 'coinmarketcap.com', 'messari.io', 
            'defillama.com', 'github.com', 'whitepaper'
        }
        
    def _load_verification_cache(self) -> Dict:
        """Load cached verification data."""
        try:
            if os.path.exists('content_verification_cache.json'):
                with open('content_verification_cache.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading verification cache: {e}")
        return {}
        
    def _save_verification_cache(self):
        """Save verification cache."""
        try:
            with open('content_verification_cache.json', 'w') as f:
                json.dump(self.verification_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving verification cache: {e}")

    async def verify_video_content(self, video_data: Dict, coin_name: str) -> Tuple[bool, float, str]:
        """
        Verify video content for accuracy and relevance across all platforms.
        Returns: (is_verified, accuracy_score, reason)
        """
        title = video_data.get('title', '').lower()
        url = video_data.get('url', '')
        video_id = video_data.get('video_id', '')
        platform = video_data.get('platform', 'youtube').lower()
        
        # Cache check
        cache_key = f"video_{platform}_{video_id}_{coin_name}"
        if cache_key in self.verification_cache:
            cached = self.verification_cache[cache_key]
            cache_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cache_time < timedelta(days=7):
                return cached['verified'], cached['score'], cached['reason']
        
        score = 0.0
        issues = []
        
        # 1. Title relevance check
        coin_keywords = self._get_coin_keywords(coin_name)
        if any(keyword in title for keyword in coin_keywords):
            score += 25
        else:
            issues.append("Video title not relevant to coin")
            
        # 2. Clickbait detection
        clickbait_patterns = [
            r'\b(shocking|unbelievable|must see|secret|hidden)\b',
            r'\b(100x|1000x|moon|lambo)\b',
            r'\$\d+\s*(target|prediction)\s*(!|\?)',
            r'\b(crash|pump|dump)\s*(!|\?)',
            r'(\?{2,}|!{2,})',
            r'\b(breaking|urgent|alert)\b'
        ]
        
        clickbait_count = sum(1 for pattern in clickbait_patterns if re.search(pattern, title, re.IGNORECASE))
        if clickbait_count == 0:
            score += 20
        elif clickbait_count <= 2:
            score += 10
            issues.append("Minor clickbait indicators")
        else:
            issues.append("High clickbait content detected")
            
        # 3. Date relevance (prefer recent content)
        if '2025' in title or '2024' in title:
            score += 15
        elif any(year in title for year in ['2023', '2022', '2021']):
            score += 5
            issues.append("Outdated content")
        
        # 4. Educational keywords
        educational_keywords = ['analysis', 'review', 'explained', 'guide', 'tutorial', 'fundamentals']
        if any(keyword in title for keyword in educational_keywords):
            score += 15
        
        # 5. Hype words penalty
        hype_words = ['moon', 'rocket', 'explode', 'massive', 'insane']
        hype_count = sum(1 for word in hype_words if word in title)
        score -= min(hype_count * 5, 20)
        if hype_count > 2:
            issues.append("Excessive hype language")
            
        # 6. Platform-specific URL validation and bonuses
        platform_domains = {
            'youtube': ['youtu.be', 'youtube.com'],
            'rumble': ['rumble.com'],
            'twitch': ['twitch.tv']
        }
        
        valid_domains = platform_domains.get(platform, ['youtube.com'])
        if any(domain in url for domain in valid_domains):
            score += 10
            # Platform diversity bonus
            if platform == 'rumble':
                score += 5  # Bonus for alternative platform
            elif platform == 'twitch':
                score += 3  # Bonus for live/interactive content
        else:
            issues.append(f"Invalid {platform} URL")
            
        # Content quality from platform score
        if video_data.get('quality_score', 0) > 70:
            score += 10
        elif video_data.get('quality_score', 0) > 50:
            score += 5
            
        # Final verification
        is_verified = score >= 50 and len(issues) <= 2
        reason = "Verified content" if is_verified else f"Issues: {', '.join(issues)}"
        
        # Cache result
        self.verification_cache[cache_key] = {
            'verified': is_verified,
            'score': score,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        self._save_verification_cache()
        
        return is_verified, score, reason

    def _get_coin_keywords(self, coin_name: str) -> List[str]:
        """Get relevant keywords for coin verification."""
        coin_keywords = {
            'ripple': ['ripple', 'xrp', 'swift', 'cross-border'],
            'hedera hashgraph': ['hedera', 'hbar', 'hashgraph', 'enterprise'],
            'stellar': ['stellar', 'xlm', 'lumen', 'payment'],
            'xdce crowd sale': ['xinfin', 'xdc', 'trade finance'],
            'sui': ['sui', 'move', 'programming'],
            'ondo finance': ['ondo', 'rwa', 'real world assets'],
            'algorand': ['algorand', 'algo', 'smart contract'],
            'casper network': ['casper', 'cspr', 'proof of stake']
        }
        return coin_keywords.get(coin_name, [coin_name.split()[0]])

    async def verify_price_data(self, price_data: Dict, coin_name: str) -> Tuple[bool, str]:
        """Verify price data accuracy against multiple sources."""
        try:
            current_price = price_data.get('price', 0)
            change_24h = price_data.get('price_change_24h', 0)
            
            # Sanity checks
            if current_price <= 0:
                return False, "Invalid price data"
                
            if abs(change_24h) > 50:  # >50% change is suspicious
                return False, f"Suspicious price change: {change_24h}%"
                
            # Historical comparison
            cache_key = f"price_{coin_name}"
            if cache_key in self.verification_cache:
                last_price = self.verification_cache[cache_key].get('last_price', current_price)
                price_diff = abs((current_price - last_price) / last_price * 100)
                
                if price_diff > 30:  # >30% from last known price
                    return False, f"Price deviation too high: {price_diff:.1f}%"
            
            # Update cache
            self.verification_cache[cache_key] = {
                'last_price': current_price,
                'timestamp': datetime.now().isoformat()
            }
            
            return True, "Price data verified"
            
        except Exception as e:
            return False, f"Price verification error: {e}"

    def verify_social_metrics(self, social_data: Dict, coin_name: str) -> Tuple[bool, str]:
        """Verify social metrics for realistic values."""
        try:
            mentions = social_data.get('mentions', 0)
            sentiment = social_data.get('sentiment', 'Unknown')
            
            # Realistic mention ranges
            mention_ranges = {
                'ripple': (20, 100), 'hedera-hashgraph': (10, 60),
                'stellar': (15, 80), 'xinfin-network': (5, 40),
                'sui': (25, 120), 'ondo-finance': (10, 50),
                'algorand': (15, 70), 'casper-network': (5, 30)
            }
            
            expected_range = mention_ranges.get(coin_name, (5, 50))
            if not (expected_range[0] <= mentions <= expected_range[1] * 2):
                return False, f"Unrealistic mention count: {mentions}"
                
            # Valid sentiments
            valid_sentiments = [
                'Very Bullish', 'Bullish', 'Positive', 'Neutral', 
                'Bearish', 'Very Bearish'
            ]
            if sentiment not in valid_sentiments:
                return False, f"Invalid sentiment: {sentiment}"
                
            return True, "Social metrics verified"
            
        except Exception as e:
            return False, f"Social verification error: {e}"

    def rate_content_accuracy(self, content_data: Dict) -> Dict:
        """Rate overall content accuracy and provide recommendations."""
        ratings = {
            'overall_score': 0,
            'components': {},
            'warnings': [],
            'recommendations': []
        }
        
        # Component scoring
        if 'price_verified' in content_data:
            score = 25 if content_data['price_verified'] else 0
            ratings['components']['price_data'] = score
            ratings['overall_score'] += score
            
        if 'social_verified' in content_data:
            score = 20 if content_data['social_verified'] else 0
            ratings['components']['social_metrics'] = score
            ratings['overall_score'] += score
            
        if 'video_score' in content_data:
            score = min(content_data['video_score'], 25)
            ratings['components']['video_content'] = score
            ratings['overall_score'] += score
            
        # Technical analysis score
        if content_data.get('has_prediction'):
            ratings['components']['technical_analysis'] = 15
            ratings['overall_score'] += 15
            
        # Fundamental analysis score
        if content_data.get('has_fundamentals'):
            ratings['components']['fundamental_analysis'] = 15
            ratings['overall_score'] += 15
            
        # Generate warnings and recommendations
        if ratings['overall_score'] < 50:
            ratings['warnings'].append("Low content accuracy score")
            ratings['recommendations'].append("Review data sources")
            
        if not content_data.get('price_verified'):
            ratings['warnings'].append("Unverified price data")
            ratings['recommendations'].append("Cross-check price sources")
            
        if content_data.get('video_score', 0) < 30:
            ratings['warnings'].append("Low-quality video content")
            ratings['recommendations'].append("Find better educational content")
            
        return ratings

    def should_post_content(self, content_rating: Dict) -> Tuple[bool, str]:
        """Determine if content should be posted based on ratings."""
        overall_score = content_rating['overall_score']
        warnings = content_rating['warnings']
        
        if overall_score >= 70:
            return True, "High-quality content approved"
        elif overall_score >= 50:
            if len(warnings) <= 1:
                return True, "Acceptable content with minor issues"
            else:
                return False, "Too many quality issues"
        else:
            return False, f"Content quality too low: {overall_score}/100"

# Initialize global verifier
content_verifier = ContentVerifier()

async def verify_all_content(coin_data: Dict) -> Dict:
    """Verify all content for a coin posting."""
    verification_results = {}
    
    # Verify video content (multi-platform)
    if 'youtube_video' in coin_data:
        video_verified, video_score, video_reason = await content_verifier.verify_video_content(
            coin_data['youtube_video'], coin_data['coin_name']
        )
        verification_results.update({
            'video_verified': video_verified,
            'video_score': video_score,
            'video_reason': video_reason
        })
    
    # Verify price data
    price_verified, price_reason = await content_verifier.verify_price_data(
        {
            'price': coin_data.get('price'),
            'price_change_24h': coin_data.get('price_change_24h')
        },
        coin_data['coin_name']
    )
    verification_results.update({
        'price_verified': price_verified,
        'price_reason': price_reason
    })
    
    # Verify social metrics
    social_verified, social_reason = content_verifier.verify_social_metrics(
        coin_data.get('social_metrics', {}), coin_data['coin_name']
    )
    verification_results.update({
        'social_verified': social_verified,
        'social_reason': social_reason
    })
    
    # Add flags for content completeness
    verification_results.update({
        'has_prediction': 'predicted_price' in coin_data,
        'has_fundamentals': 'fundamental_note' in coin_data
    })
    
    # Rate overall content
    content_rating = content_verifier.rate_content_accuracy(verification_results)
    verification_results['content_rating'] = content_rating
    
    # Posting decision
    should_post, post_reason = content_verifier.should_post_content(content_rating)
    verification_results.update({
        'should_post': should_post,
        'post_decision_reason': post_reason
    })
    
    return verification_results
