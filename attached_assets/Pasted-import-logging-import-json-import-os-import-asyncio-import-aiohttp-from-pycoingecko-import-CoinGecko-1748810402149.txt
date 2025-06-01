import logging
import json
import os
import asyncio
import aiohttp
from pycoingecko import CoinGeckoAPI
from typing import Dict, List

logger = logging.getLogger('CryptoBot')

def get_coinmarketcap_api_key():
    """Get CoinMarketCap API key from environment variables."""
    return os.getenv('COINMARKETCAP_API_KEY')

# Cache file for top projects
TOP_PROJECT_CACHE_FILE = "data/top_projects_cache.json"

# Symbol mapping for different coin IDs to their ticker symbols
symbol_map = {
    "ripple": "XRP",
    "hedera-hashgraph": "HBAR",
    "stellar": "XLM",
    "xdce-crowd-sale": "XDC",
    "sui": "SUI",
    "ondo-finance": "ONDO",
    "algorand": "ALGO",
    "casper-network": "CSPR"
}

coinmarketcap_id_map = {
    "ripple": "52",
    "hedera-hashgraph": "4642",
    "stellar": "512",
    "xdce-crowd-sale": "2634",
    "sui": "20947",
    "ondo-finance": "29187",
    "algorand": "4030",
    "casper-network": "5899"
}

# Cache files
VOLUME_CACHE_FILE = "volume_cache.json"
TOP_PROJECT_CACHE_FILE = "top_project_cache.json"

def load_volume_cache() -> Dict[str, float]:
    """Load cached transaction volumes from a file."""
    try:
        if os.path.exists(VOLUME_CACHE_FILE) and os.access(VOLUME_CACHE_FILE, os.R_OK):
            with open(VOLUME_CACHE_FILE, 'r') as f:
                return json.load(f)
        return {}
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error loading volume cache: {e}")
        return {}

def save_volume_cache(cache: Dict[str, float]):
    """Save transaction volumes to a cache file."""
    try:
        with open(VOLUME_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except IOError as e:
        logger.error(f"Error saving volume cache: {e}")

def load_top_project_cache() -> Dict[str, str]:
    """Load cached top projects from a file."""
    try:
        if os.path.exists(TOP_PROJECT_CACHE_FILE) and os.access(TOP_PROJECT_CACHE_FILE, os.R_OK):
            with open(TOP_PROJECT_CACHE_FILE, 'r') as f:
                return json.load(f)
        return {}
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error loading top project cache: {e}")
        return {}

def save_top_project_cache(cache: Dict[str, str]):
    """Save top projects to a cache file."""
    try:
        with open(TOP_PROJECT_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except IOError as e:
        logger.error(f"Error saving top project cache: {e}")

def fetch_coin_prices(coin_ids: List[str], cg_client: CoinGeckoAPI) -> Dict:
    """Fetch coin prices and 24h change using CoinGecko API."""
    try:
        if not coin_ids:
            logger.error("Empty coin_ids list provided")
            return {}
        prices = cg_client.get_price(
            ids=coin_ids,
            vs_currencies='usd',
            include_24hr_change=True
        )
        return prices
    except Exception as e:
        logger.error(f"Error fetching prices from CoinGecko: {e}")
        raise

async def fetch_volume(coin_id: str, session: aiohttp.ClientSession) -> float:
    """Fetch 24h transaction volume using CoinMarketCap API, with CoinGecko fallback."""
    cache = load_volume_cache()
    if coin_id in cache:
        logger.debug(f"Using cached volume for {coin_id}: {cache[coin_id]}")
        return cache[coin_id]

    coinmarketcap_id = coinmarketcap_id_map.get(coin_id)
    if not coinmarketcap_id:
        logger.error(f"No CoinMarketCap ID found for {coin_id}")
        return 0.0

    # Try CoinMarketCap API
    api_key = get_coinmarketcap_api_key()
    if not api_key:
        logger.error("CoinMarketCap API key not found in environment variables")
        return 0.0

    url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?id={coinmarketcap_id}&convert=USD&CMC_PRO_API_KEY={api_key}"
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            logger.debug(f"CoinMarketCap API response for {coin_id} (ID: {coinmarketcap_id}): {data}")
            if 'data' not in data or coinmarketcap_id not in data['data']:
                logger.error(f"CoinMarketCap API error for {coin_id} (ID: {coinmarketcap_id}): No data returned")
                raise ValueError("No data returned")
            volume = data['data'][coinmarketcap_id]['quote']['USD'].get('volume_24h')
            if volume is None:
                logger.warning(f"No volume data available for {coin_id} (ID: {coinmarketcap_id}) from CoinMarketCap")
                raise ValueError("No volume data")
            volume = volume / 1_000_000  # Convert to millions
            cache[coin_id] = volume
            save_volume_cache(cache)
            return volume
    except (aiohttp.ClientError, ValueError) as e:
        logger.error(f"CoinMarketCap API error for {coin_id} (ID: {coinmarketcap_id}): {e}")

    # Fallback to CoinGecko API
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            logger.debug(f"CoinGecko API response for volume {coin_id}: {data}")
            volume = data.get('market_data', {}).get('total_volume', {}).get('usd', 0)
            if volume == 0:
                logger.warning(f"No volume data available for {coin_id} from CoinGecko")
                return 0.0
            volume = volume / 1_000_000  # Convert to millions
            cache[coin_id] = volume
            save_volume_cache(cache)
            return volume
    except aiohttp.ClientError as e:
        logger.error(f"CoinGecko API error for volume {coin_id}: {e}")
        return 0.0

async def fetch_top_project(coin_id: str, session: aiohttp.ClientSession) -> str:
    """Fetch the top project (exchange) for a coin using CoinGecko API."""
    cache = load_top_project_cache()
    if coin_id in cache:
        logger.debug(f"Using cached top project for {coin_id}: {cache[coin_id]}")
        return cache[coin_id]

    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/tickers"
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            logger.debug(f"CoinGecko API response for top project {coin_id}: {data}")
            if 'tickers' not in data or not data['tickers']:
                logger.warning(f"No tickers found for {coin_id}, using fallback.")
                project_map = {
                    "hedera-hashgraph": "Binance CEX",
                    "stellar": "Binance CEX",
                    "sui": "Binance CEX",
                    "algorand": "Binance CEX",
                    "xdce-crowd-sale": "Gate",
                    "casper-network": "Gate",
                    "ondo-finance": "Binance CEX"
                }
                top_exchange = project_map.get(coin_id, "N/A")
                cache[coin_id] = top_exchange
                save_top_project_cache(cache)
                return top_exchange
            top_ticker = max(data['tickers'], key=lambda x: x.get('volume', 0))
            top_exchange = top_ticker.get('market', {}).get('name', "N/A")
            if top_exchange == "N/A":
                raise ValueError("No exchange name found")
            cache[coin_id] = top_exchange
            save_top_project_cache(cache)
            return top_exchange
    except (aiohttp.ClientError, ValueError) as e:
        logger.error(f"CoinGecko API error for top project {coin_id}: {e}")
        project_map = {
            "hedera-hashgraph": "Binance CEX",
            "stellar": "Binance CEX",
            "sui": "Binance CEX",
            "algorand": "Binance CEX",
            "xdce-crowd-sale": "Gate",
            "casper-network": "Gate",
            "ondo-finance": "Binance CEX"
        }
        top_project = project_map.get(coin_id, "N/A")
        cache[coin_id] = top_project
        save_top_project_cache(cache)
        return top_project