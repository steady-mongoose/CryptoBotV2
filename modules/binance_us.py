
import aiohttp
import logging
from typing import Dict, Optional
import asyncio

logger = logging.getLogger('CryptoBot')

class BinanceUSAPI:
    def __init__(self):
        self.base_url = "https://api.binance.us/api/v3"
        
    async def get_ticker_price(self, symbol: str, session: aiohttp.ClientSession) -> Optional[float]:
        """Get current price for a symbol from Binance US"""
        try:
            url = f"{self.base_url}/ticker/price?symbol={symbol}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['price'])
                    logger.debug(f"Binance US price for {symbol}: ${price:.4f}")
                    return price
                else:
                    logger.warning(f"Binance US API error for {symbol}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching Binance US price for {symbol}: {str(e)}")
            return None
    
    async def get_24hr_ticker(self, symbol: str, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Get 24hr ticker statistics from Binance US"""
        try:
            url = f"{self.base_url}/ticker/24hr?symbol={symbol}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'price': float(data['lastPrice']),
                        'change_24h': float(data['priceChangePercent']),
                        'volume': float(data['volume']),
                        'high': float(data['highPrice']),
                        'low': float(data['lowPrice'])
                    }
                else:
                    logger.warning(f"Binance US 24hr ticker error for {symbol}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching Binance US 24hr ticker for {symbol}: {str(e)}")
            return None
    
    async def get_exchange_info(self, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Get exchange information including available symbols"""
        try:
            url = f"{self.base_url}/exchangeInfo"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.warning(f"Binance US exchange info error: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching Binance US exchange info: {str(e)}")
            return None

# Global instance
binance_us_api = BinanceUSAPI()
