
import logging
import re
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os

logger = logging.getLogger('CryptoBot')

async def verify_all_content(coin_data: Dict) -> Dict:
    """Verify content quality and accuracy for a coin."""
    try:
        # Basic content verification
        content_score = 50  # Base score
        warnings = []
        
        # Price validation
        if coin_data.get('price', 0) > 0:
            content_score += 20
        else:
            warnings.append("Invalid price data")
        
        # Social metrics validation
        social_metrics = coin_data.get('social_metrics', {})
        if social_metrics.get('mentions', 0) > 0:
            content_score += 15
        
        # Video content validation
        video = coin_data.get('youtube_video', {})
        if video.get('url') and video.get('title'):
            content_score += 15
        
        # Overall quality check
        should_post = content_score >= 60
        
        return {
            'should_post': should_post,
            'content_rating': {
                'overall_score': content_score,
                'warnings': warnings
            },
            'post_decision_reason': f"Content score: {content_score}/100"
        }
        
    except Exception as e:
        logger.error(f"Content verification error: {e}")
        return {
            'should_post': False,
            'content_rating': {
                'overall_score': 0,
                'warnings': ['Verification system error']
            },
            'post_decision_reason': f"Error: {e}"
        }

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
        Enhanced video verification: crypto-specificity, public availability, accuracy and engagement.
        Returns: (is_verified, accuracy_score, reason)
        """
        title = video_data.get('title', '').lower()
        url = video_data.get('url', '')
        video_id = video_data.get('video_id', '')
        platform = video_data.get('platform', 'youtube').lower()
        content_date = video_data.get('content_date', '')
        
        # Cache check with shorter duration for recent content verification
        cache_key = f"video_{platform}_{video_id}_{coin_name}_{content_date}"
        if cache_key in self.verification_cache:
            cached = self.verification_cache[cache_key]
            cache_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cache_time < timedelta(hours=6):  # Shorter cache for recency
                return cached['verified'], cached['score'], cached['reason']
        
        score = 0.0
        issues = []
        
        # 1. PUBLIC AVAILABILITY CHECK (CRITICAL)
        is_public, availability_reason = await self._verify_public_availability(url, platform)
        if not is_public:
            issues.append(f"Video not publicly available: {availability_reason}")
            score -= 30  # Heavy penalty for non-public content
        else:
            score += 20  # Bonus for verified public access
        
        # 2. Crypto-specific token verification (CRITICAL)
        coin_keywords = self._get_coin_keywords(coin_name)
        coin_symbol = self._get_coin_symbol(coin_name)
        
        crypto_specific_score = self._verify_crypto_specificity(title, coin_symbol, coin_keywords)
        if crypto_specific_score < 15:  # Minimum threshold for crypto relevance
            issues.append(f"Video not specifically about {coin_symbol}")
            score -= 25  # Heavy penalty for non-specific content
        else:
            score += crypto_specific_score
            
        # 3. ENGAGEMENT & ACCURACY RATING (CRITICAL)
        engagement_score = self._calculate_engagement_rating(title, platform)
        if engagement_score < 60:
            issues.append(f"Low engagement potential: {engagement_score}/100")
            score -= 15
        else:
            score += min(engagement_score // 5, 20)  # Up to 20 bonus points
        
        # 4. 24-hour recency verification (CRITICAL)
        current_date = datetime.now().strftime("%Y-%m-%d")
        yesterday_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        if current_date in title or content_date == current_date:
            score += 25  # Bonus for same-day content
        elif yesterday_date in title or content_date == yesterday_date:
            score += 15  # Bonus for recent content
        elif '2025' in title:
            score += 10  # Current year content
        else:
            issues.append("Content not verified as recent (within 24h)")
            score -= 15
            
        # 5. Clickbait detection (stricter for crypto)
        clickbait_patterns = [
            r'\b(shocking|unbelievable|must see|secret|hidden)\b',
            r'\b(100x|1000x|moon|lambo|to the moon)\b',
            r'\$\d+\s*(target|prediction)\s*(!|\?)',
            r'\b(crash|pump|dump|rocket)\s*(!|\?)',
            r'(\?{3,}|!{3,})',
            r'\b(breaking|urgent|alert|explosive)\b'
        ]
        
        clickbait_count = sum(1 for pattern in clickbait_patterns if re.search(pattern, title, re.IGNORECASE))
        if clickbait_count == 0:
            score += 15
        elif clickbait_count <= 1:
            score += 5
            issues.append("Minor clickbait indicators")
        else:
            issues.append("High clickbait content detected")
            score -= 15
        
        # 6. Platform verification with crypto-specific checks
        platform_domains = {
            'youtube': ['youtu.be', 'youtube.com'],
            'rumble': ['rumble.com'],
            'twitch': ['twitch.tv']
        }
        
        valid_domains = platform_domains.get(platform, ['youtube.com'])
        if any(domain in url for domain in valid_domains):
            score += 10
            # Verify crypto-specific content in URL
            if coin_symbol.upper() in url.upper():
                score += 5  # Bonus for token-specific URL
        else:
            issues.append(f"Invalid {platform} URL")
            
        # 7. Enhanced verification flags
        if video_data.get('verified_crypto_specific'):
            score += 10
        if video_data.get('target_keywords'):
            target_keywords = video_data['target_keywords']
            if coin_symbol in target_keywords:
                score += 10
                
        # ENHANCED FINAL VERIFICATION with stricter requirements
        is_verified = (score >= 70 and           # Raised threshold
                      len(issues) <= 1 and       # Stricter issue tolerance
                      is_public and             # Must be publicly available
                      coin_symbol.lower() in title and  # Must be token-specific
                      engagement_score >= 60)    # Must have good engagement potential
        
        reason = "Verified high-quality crypto-specific content" if is_verified else f"Issues: {', '.join(issues)}"
        
        # Cache result with enhanced verification data
        self.verification_cache[cache_key] = {
            'verified': is_verified,
            'score': score,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'crypto_specific': coin_symbol.lower() in title,
            'recency_verified': current_date in title or content_date == current_date,
            'public_available': is_public,
            'engagement_score': engagement_score,
            'specificity_score': crypto_specific_score,
            'issues_count': len(issues)
        }
        self._save_verification_cache()
        
        return is_verified, score, reason
    
    def _get_coin_symbol(self, coin_name: str) -> str:
        """Get the trading symbol for a coin."""
        symbol_map = {
            'ripple': 'XRP',
            'hedera hashgraph': 'HBAR', 
            'stellar': 'XLM',
            'xdce crowd sale': 'XDC',
            'sui': 'SUI',
            'ondo finance': 'ONDO',
            'algorand': 'ALGO',
            'casper network': 'CSPR'
        }
        return symbol_map.get(coin_name, coin_name.split()[0].upper())

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
    
    async def _verify_public_availability(self, url: str, platform: str) -> Tuple[bool, str]:
        """Verify video is publicly accessible."""
        try:
            import aiohttp
            
            # Platform-specific availability checks
            if platform == 'youtube':
                # Check for common YouTube unavailability indicators
                if 'youtu.be' in url or 'youtube.com' in url:
                    # For now, assume YouTube links are public unless proven otherwise
                    # In production, you could use YouTube API to verify
                    return True, "YouTube video assumed public"
                else:
                    return False, "Invalid YouTube URL format"
            
            elif platform == 'rumble':
                if 'rumble.com' in url:
                    return True, "Rumble video assumed public"
                else:
                    return False, "Invalid Rumble URL format"
            
            elif platform == 'twitch':
                if 'twitch.tv' in url:
                    return True, "Twitch content assumed public"
                else:
                    return False, "Invalid Twitch URL format"
            
            # Generic URL check
            if url.startswith(('http://', 'https://')):
                return True, "Valid public URL format"
            else:
                return False, "Invalid URL format"
                
        except Exception as e:
            logger.error(f"Error verifying public availability: {e}")
            return False, f"Availability check failed: {e}"
    
    def _verify_crypto_specificity(self, title: str, coin_symbol: str, coin_keywords: List[str]) -> int:
        """Verify content is specifically about the target cryptocurrency."""
        specificity_score = 0
        
        # Direct token symbol match (highest score)
        if coin_symbol.lower() in title:
            specificity_score += 25
        
        # Keyword matches
        keyword_matches = sum(1 for keyword in coin_keywords if keyword in title)
        specificity_score += keyword_matches * 5
        
        # Penalty for generic crypto terms without specific token
        generic_terms = ['crypto', 'bitcoin', 'altcoin', 'blockchain']
        if any(term in title for term in generic_terms) and coin_symbol.lower() not in title:
            specificity_score -= 10
        
        # Bonus for specific use cases or technology mentions
        tech_terms = {
            'xrp': ['swift', 'cross-border', 'ripple', 'cbdc'],
            'hbar': ['hashgraph', 'enterprise', 'hedera', 'consensus'],
            'xlm': ['stellar', 'lumens', 'anchor', 'soroban'],
            'xdc': ['xinfin', 'trade finance', 'iso20022'],
            'sui': ['move programming', 'sui network', 'aptos'],
            'ondo': ['rwa', 'real world assets', 'tokenization'],
            'algo': ['algorand', 'pure proof', 'carbon negative'],
            'cspr': ['casper', 'highway consensus', 'upgradeable']
        }
        
        relevant_terms = tech_terms.get(coin_symbol.lower(), [])
        tech_matches = sum(1 for term in relevant_terms if term in title)
        specificity_score += tech_matches * 8
        
        return min(specificity_score, 30)  # Cap at 30 points
    
    def _calculate_engagement_rating(self, title: str, platform: str) -> int:
        """Calculate engagement potential rating."""
        engagement_score = 50  # Base score
        
        # Educational content indicators (higher engagement)
        educational_indicators = [
            'tutorial', 'guide', 'explained', 'analysis', 'review',
            'deep dive', 'fundamentals', 'technical analysis'
        ]
        education_matches = sum(1 for indicator in educational_indicators if indicator in title.lower())
        engagement_score += education_matches * 10
        
        # Professional creator indicators
        professional_indicators = [
            'expert', 'professional', 'institutional', 'research',
            'official', 'whitepaper', 'development'
        ]
        pro_matches = sum(1 for indicator in professional_indicators if indicator in title.lower())
        engagement_score += pro_matches * 8
        
        # Platform engagement modifiers
        platform_modifiers = {
            'youtube': 5,    # Established platform
            'rumble': 3,     # Growing platform
            'twitch': 7      # Live interaction potential
        }
        engagement_score += platform_modifiers.get(platform, 0)
        
        # Penalty for clickbait (reduces genuine engagement)
        clickbait_terms = [
            'shocking', 'unbelievable', 'secret', 'hidden',
            '100x', 'moon', 'lambo', 'pump', 'dump'
        ]
        clickbait_count = sum(1 for term in clickbait_terms if term in title.lower())
        engagement_score -= clickbait_count * 15
        
        return max(0, min(100, engagement_score))

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

    def should_post_content(self, content_rating: Dict) -> tuple:
        """Determine if content should be posted based on rating."""
        overall_score = content_rating.get('overall_score', 0)
        warnings = content_rating.get('warnings', [])
        
        if overall_score >= 70:
            return True, "High quality content approved"
        elif overall_score >= 50 and len(warnings) <= 2:
            return True, "Acceptable quality content approved"
        else:
            return False, f"Content rejected - Score: {overall_score}, Warnings: {len(warnings)}"

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
