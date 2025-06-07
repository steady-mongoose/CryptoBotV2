
import logging
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger('CryptoBot')

class ContentComparison:
    """Compare content between Discord and X posts to identify differences."""
    
    def __init__(self):
        self.differences = []
        
    def compare_posts(self, discord_data: List[Dict], x_data: List[Dict]) -> List[str]:
        """
        Compare Discord and X post data to identify differences.
        
        Args:
            discord_data: List of coin data prepared for Discord
            x_data: List of coin data prepared for X
            
        Returns:
            List of difference descriptions
        """
        differences = []
        
        if len(discord_data) != len(x_data):
            differences.append(f"Different number of posts: Discord({len(discord_data)}) vs X({len(x_data)})")
            return differences
        
        for i, (d_coin, x_coin) in enumerate(zip(discord_data, x_data)):
            coin_name = d_coin.get('coin_name', f'Coin {i+1}')
            
            # Compare social metrics
            d_social = d_coin.get('social_metrics', {})
            x_social = x_coin.get('social_metrics', {})
            
            if d_social.get('mentions', 0) != x_social.get('mentions', 0):
                differences.append(
                    f"{coin_name}: Social mentions differ - "
                    f"Discord({d_social.get('mentions', 0)}) vs X({x_social.get('mentions', 0)})"
                )
            
            if d_social.get('sentiment') != x_social.get('sentiment'):
                differences.append(
                    f"{coin_name}: Sentiment differs - "
                    f"Discord({d_social.get('sentiment', 'N/A')}) vs X({x_social.get('sentiment', 'N/A')})"
                )
            
            # Compare video content
            d_video = d_coin.get('youtube_video', {})
            x_video = x_coin.get('youtube_video', {})
            
            if d_video.get('title', 'N/A')[:20] != x_video.get('title', 'N/A')[:20]:
                differences.append(
                    f"{coin_name}: Video content differs - "
                    f"Discord('{d_video.get('title', 'N/A')[:30]}...') vs "
                    f"X('{x_video.get('title', 'N/A')[:30]}...')"
                )
            
            # Compare price data
            if abs(d_coin.get('price', 0) - x_coin.get('price', 0)) > 0.01:
                differences.append(
                    f"{coin_name}: Price differs - "
                    f"Discord(${d_coin.get('price', 0):.4f}) vs X(${x_coin.get('price', 0):.4f})"
                )
        
        if differences:
            logger.warning(f"Found {len(differences)} content differences between Discord and X")
            for diff in differences:
                logger.warning(f"  • {diff}")
        else:
            logger.info("✅ No content differences found between Discord and X posts")
        
        return differences
    
    def analyze_why_different(self, discord_data: List[Dict], x_data: List[Dict]) -> Dict:
        """
        Analyze why content is different and provide remediation suggestions.
        
        Returns:
            Dict with analysis and suggestions
        """
        differences = self.compare_posts(discord_data, x_data)
        
        if not differences:
            return {
                'status': 'identical',
                'message': 'Content is identical between platforms'
            }
        
        # Categorize differences
        social_issues = [d for d in differences if 'Social' in d]
        video_issues = [d for d in differences if 'Video' in d]
        price_issues = [d for d in differences if 'Price' in d]
        
        analysis = {
            'status': 'different',
            'total_differences': len(differences),
            'categories': {
                'social_metrics': len(social_issues),
                'video_content': len(video_issues),
                'price_data': len(price_issues)
            },
            'suggestions': []
        }
        
        # Generate suggestions
        if social_issues:
            analysis['suggestions'].append(
                "Social metrics differ: Check if X API search is disabled for one platform"
            )
        
        if video_issues:
            analysis['suggestions'].append(
                "Video content differs: Check YouTube API quota or Rumble fallback behavior"
            )
        
        if price_issues:
            analysis['suggestions'].append(
                "Price data differs: Check if different API sources are being used"
            )
        
        return analysis

# Global instance
content_comparison = ContentComparison()
