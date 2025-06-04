import logging
from pycoingecko import CoinGeckoAPI
import os
import aiohttp

logger = logging.getLogger('CryptoBot')

async def fetch_coin_prices_multi_source(coin_ids, cg_client, coinbase_client):
    """Fetch coin prices from multiple sources asynchronously."""
    prices = {}
    try:
        # Fetch from CoinGecko
        coingecko_data = cg_client.get_price(ids=','.join(coin_ids), vs_currencies='usd')
        for coin_id in coin_ids:
            prices[coin_id] = {'usd': coingecko_data.get(coin_id, {}).get('usd', 0)}

        # Fetch from Coinbase
        async with aiohttp.ClientSession() as session:
            for coin_id in coin_ids:
                coinbase_api_url = f"https://api.coinbase.com/v2/prices/{coin_id}-USD/spot"
                async with session.get(coinbase_api_url) as response:
                    if response.status == 429:  # Rate limit exceeded
                        logger.warning("Rate limit warning from Coinbase.")
                        return None
                    elif response.status == 200:
                        coinbase_data = await response.json()
                        prices[coin_id]['coinbase_usd'] = coinbase_data['data']['amount']
                    # Implement failover logic here if needed

        logger.info("Coin prices fetched successfully from all sources.")
    except Exception as e:
        logger.error(f"Error fetching coin prices: {e}")
    return prices