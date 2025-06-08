
import aiohttp
import asyncio
import logging
from typing import Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger('CryptoBot')

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import aiohttp

logger = logging.getLogger('CryptoBot')

class AlternativeSocialMetrics:
    """Alternative social metrics when X API is rate limited."""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(hours=4)
    
    async def get_comprehensive_social_data(self, symbol: str, coin_id: str, session: aiohttp.ClientSession) -> Dict:
        """Get social metrics from multiple non-X sources."""
        cache_key = f"{symbol}_{coin_id}"
        
        # Check cache first
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                logger.info(f"Using cached alternative social data for {symbol}")
                return cached_data
        
        total_mentions = 0
        sources_used = []
        sentiment_data = []
        
        # 1. CryptoCompare Social Data
        try:
            mentions = await self._get_cryptocompare_social(symbol, session)
            if mentions > 0:
                total_mentions += mentions
                sources_used.append(f"CryptoCompare ({mentions})")
        except Exception as e:
            logger.error(f"CryptoCompare error for {symbol}: {e}")
        
        # 2. LunarCrush API
        try:
            mentions = await self._get_lunarcrush_data(symbol, session)
            if mentions > 0:
                total_mentions += mentions
                sources_used.append(f"LunarCrush ({mentions})")
        except Exception as e:
            logger.error(f"LunarCrush error for {symbol}: {e}")
        
        # 3. CoinGecko Developer/Community Stats
        try:
            mentions = await self._get_coingecko_community(coin_id, session)
            if mentions > 0:
                total_mentions += mentions
                sources_used.append(f"CoinGecko ({mentions})")
        except Exception as e:
            logger.error(f"CoinGecko community error for {coin_id}: {e}")
        
        # 4. Reddit API
        try:
            mentions = await self._get_reddit_mentions(symbol, session)
            if mentions > 0:
                total_mentions += mentions
                sources_used.append(f"Reddit ({mentions})")
        except Exception as e:
            logger.error(f"Reddit error for {symbol}: {e}")
        
        # 5. GitHub Activity (for development coins)
        try:
            mentions = await self._get_github_activity(symbol, coin_id, session)
            if mentions > 0:
                total_mentions += mentions
                sources_used.append(f"GitHub ({mentions})")
        except Exception as e:
            logger.error(f"GitHub error for {symbol}: {e}")
        
        # Calculate sentiment from available data
        sentiment = self._calculate_sentiment(symbol, total_mentions)
        
        result = {
            "mentions": max(total_mentions, 8),  # Minimum baseline
            "sentiment": sentiment,
            "sources": sources_used,
            "confidence": len(sources_used) >= 2
        }
        
        # Cache the result
        self.cache[cache_key] = (datetime.now(), result)
        
        logger.info(f"Alternative social metrics for {symbol}: {result['mentions']} mentions from {len(sources_used)} sources")
        return result
    
    async def _get_cryptocompare_social(self, symbol: str, session: aiohttp.ClientSession) -> int:
        """Get social data from CryptoCompare."""
        url = f"https://min-api.cryptocompare.com/data/social/coin/general?fsym={symbol}"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('Response') == 'Success':
                    social_data = data.get('Data', {})
                    
                    # Combine multiple social metrics
                    reddit_posts = social_data.get('Reddit', {}).get('Posts', 0)
                    twitter_followers = social_data.get('Twitter', {}).get('followers', 0)
                    
                    # Convert to mention estimate
                    mentions = min(reddit_posts + (twitter_followers // 10000), 25)
                    await asyncio.sleep(1)
                    return mentions
        return 0
    
    async def _get_lunarcrush_data(self, symbol: str, session: aiohttp.ClientSession) -> int:
        """Get data from LunarCrush."""
        url = f"https://api.lunarcrush.com/v2?data=assets&symbol={symbol}"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('data') and len(data['data']) > 0:
                    asset_data = data['data'][0]
                    tweets_24h = asset_data.get('tweets_24h', 0)
                    social_score = asset_data.get('social_score', 0)
                    
                    mentions = min(tweets_24h + (social_score // 10), 30)
                    await asyncio.sleep(1)
                    return mentions
        return 0
    
    async def _get_coingecko_community(self, coin_id: str, session: aiohttp.ClientSession) -> int:
        """Get community data from CoinGecko."""
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=false&community_data=true"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                community_data = data.get('community_data', {})
                
                reddit_subs = community_data.get('reddit_subscribers', 0)
                telegram_users = community_data.get('telegram_channel_user_count', 0)
                
                mentions = min((reddit_subs // 1000) + (telegram_users // 500), 20)
                await asyncio.sleep(2)
                return mentions
        return 0
    
    async def _get_reddit_mentions(self, symbol: str, session: aiohttp.ClientSession) -> int:
        """Get Reddit mentions."""
        url = f"https://www.reddit.com/r/cryptocurrency/search.json?q={symbol}&sort=new&limit=15"
        async with session.get(url, headers={'User-Agent': 'CryptoBot/1.0'}) as response:
            if response.status == 200:
                data = await response.json()
                posts = data.get('data', {}).get('children', [])
                mentions = len(posts)
                await asyncio.sleep(1)
                return mentions
        return 0
    
    async def _get_github_activity(self, symbol: str, coin_id: str, session: aiohttp.ClientSession) -> int:
        """Get GitHub activity as development interest metric."""
        # Map some coins to their GitHub repos
        github_repos = {
            'XRP': 'XRPLF/xrpl-dev-portal',
            'HBAR': 'hashgraph/hedera-services',
            'XLM': 'stellar/stellar-core',
            'ALGO': 'algorand/go-algorand',
            'SUI': 'MystenLabs/sui'
        }
        
        if symbol in github_repos:
            url = f"https://api.github.com/repos/{github_repos[symbol]}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    stars = data.get('stargazers_count', 0)
                    forks = data.get('forks_count', 0)
                    
                    # Convert GitHub activity to social mentions
                    mentions = min((stars // 100) + (forks // 50), 15)
                    await asyncio.sleep(1)
                    return mentions
        return 0
    
    def _calculate_sentiment(self, symbol: str, mentions: int) -> str:
        """Calculate sentiment based on mention volume and coin performance."""
        # Simple sentiment based on mention volume
        if mentions > 30:
            return "Bullish"
        elif mentions < 10:
            return "Bearish"
        else:
            return "Neutral"

# Global instance
alternative_social = AlternativeSocialMetrics()
