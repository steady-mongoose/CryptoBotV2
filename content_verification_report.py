#!/usr/bin/env python3
"""
Content Verification Report
Test and report on content verification systems.
"""

import asyncio
import logging
from modules.content_verification import verify_all_content
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ContentVerification')

async def generate_verification_report():
    """Generate a comprehensive content verification report."""
    print("🔍 Content Verification Report")
    print("=" * 50)

    # Sample coin data for testing
    test_coins = [
        {
            'coin_name': 'ripple',
            'coin_symbol': 'XRP',
            'price': 2.21,
            'price_change_24h': 5.2,
            'predicted_price': 2.32,
            'tx_volume': 1800.0,
            'hashtag': '#XRP',
            'social_metrics': {'mentions': 150, 'sentiment': 'Bullish'},
            'youtube_video': {'title': 'XRP Analysis', 'url': 'https://youtube.com/watch?v=test', 'platform': 'YouTube'}
        },
        {
            'coin_name': 'hedera hashgraph',
            'coin_symbol': 'HBAR', 
            'price': 0.168,
            'price_change_24h': 3.1,
            'predicted_price': 0.175,
            'tx_volume': 90.0,
            'hashtag': '#HBAR',
            'social_metrics': {'mentions': 85, 'sentiment': 'Positive'},
            'youtube_video': {'title': 'HBAR Enterprise Update', 'url': 'https://youtube.com/watch?v=test2', 'platform': 'YouTube'}
        }
    ]

    print(f"📊 Testing {len(test_coins)} sample coins...")

    for coin_data in test_coins:
        print(f"\n🔍 Verifying {coin_data['coin_symbol']}...")
        try:
            verification_results = await verify_all_content(coin_data)
            should_post = verification_results.get('should_post', False)
            content_score = verification_results.get('content_rating', {}).get('overall_score', 0)

            status = "✅ APPROVED" if should_post else "❌ REJECTED"
            print(f"   {status} - Score: {content_score}/100")

            if verification_results.get('content_rating', {}).get('warnings'):
                for warning in verification_results['content_rating']['warnings']:
                    print(f"   ⚠️ {warning}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print(f"\n✅ Content verification report completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(generate_verification_report())