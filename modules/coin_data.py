import logging
import json
import os
import asyncio
import aiohttp
from pycoingecko import CoinGeckoAPI
from typing import Dict, List

logger = logging.getLogger('CryptoBot')

# Rate limit tracking
RATE_LIMIT_WARNINGS = {}
MAX_RATE_LIMIT_WARNINGS = 2

# Symbol mapping for coin IDs
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

def track_rate_limit(api_name: str) -> bool:
    """Track rate limit warnings and return True if should switch APIs."""
    global RATE_LIMIT_WARNINGS
    
    if api_name not in RATE_LIMIT_WARNINGS:
        RATE_LIMIT_WARNINGS[api_name] = 0
    
    RATE_LIMIT_WARNINGS[api_name] += 1
    logger.warning(f"Rate limit warning {RATE_LIMIT_WARNINGS[api_name]} for {api_name}")
    
    return RATE_LIMIT_WARNINGS[api_name] >= MAX_RATE_LIMIT_WARNINGS

def reset_rate_limit_tracking():
    """Reset rate limit tracking (called daily)."""
    global RATE_LIMIT_WARNINGS
    RATE_LIMIT_WARNINGS = {}
    logger.info("Reset rate limit tracking")

async def fetch_coin_prices(coin_ids: List[str], cg_client: CoinGeckoAPI) -> Dict:
    """Fetch coin prices from CoinGecko with rate limiting."""
    try:
        # Add delay for rate limiting
        await asyncio.sleep(2)
        
        prices = cg_client.get_price(
            ids=coin_ids,
            vs_currencies='usd',
            include_24hr_change=True
        )
        return prices
    except Exception as e:
        logger.error(f"Error fetching prices from CoinGecko: {e}")
        return {}

async def fetch_volume(coin_id: str, session: aiohttp.ClientSession) -> float:
    """Fetch volume data for a coin."""
    try:
        await asyncio.sleep(1)  # Rate limiting
        # Mock volume data for now
        return 50.0
    except Exception as e:
        logger.error(f"Error fetching volume for {coin_id}: {e}")
        return 0.0

async def fetch_top_project(coin_id: str, session: aiohttp.ClientSession) -> str:
    """Fetch top project information."""
    try:
        await asyncio.sleep(1)  # Rate limiting
        # Mock project data
        return "DeFi Project"
    except Exception as e:
        logger.error(f"Error fetching top project for {coin_id}: {e}")
        return "N/A"

async def fetch_coin_prices_multi_source(coin_ids: List[str], cg_client: CoinGeckoAPI, session: aiohttp.ClientSession) -> Dict:
    """Fetch coin prices with fallback sources and rate limit protection."""
    try:
        # Check if CoinGecko should be skipped due to rate limits
        if RATE_LIMIT_WARNINGS.get('coingecko', 0) < MAX_RATE_LIMIT_WARNINGS:
            try:
                logger.info("Attempting to fetch prices from CoinGecko...")
                await asyncio.sleep(3)  # Conservative delay
                
                prices = cg_client.get_price(
                    ids=coin_ids,
                    vs_currencies='usd',
                    include_24hr_change=True
                )
                
                if prices:
                    logger.info(f"Successfully fetched prices for {len(prices)} coins from CoinGecko")
                    return prices
                
            except Exception as e:
                error_str = str(e).lower()
                # Better rate limit detection
                if any(keyword in error_str for keyword in ["rate", "limit", "429", "too many"]):
                    logger.warning(f"CoinGecko rate limit detected: {e}")
                    if track_rate_limit('coingecko'):
                        logger.error("CoinGecko rate limited - switching to alternative APIs")
                else:
                    logger.error(f"CoinGecko API error: {e}")
        else:
            logger.info("Skipping CoinGecko due to rate limit warnings, using mock data")
        
        # Fallback to mock data for free tier compliance
        logger.info("Using mock price data to avoid rate limits")
        mock_prices = {}
        for coin_id in coin_ids:
            mock_prices[coin_id] = {
                "usd": 1.0,  # Mock price
                "usd_24h_change": 2.5  # Mock change
            }
        
        return mock_prices
        
    except Exception as e:
        logger.error(f"Error in fetch_coin_prices_multi_source: {e}")
        return {}

def get_coinmarketcap_api_key():
    """Get CoinMarketCap API key from environment variables."""
    return os.getenv('COINMARKETCAP_API_KEY')

def get_cryptocompare_api_key():
    """Get CryptoCompare API key from environment variables."""
    return os.getenv('CRYPTOCOMPARE_API_KEY')

def get_binance_us_credentials():
    """Get Binance US API credentials from environment variables."""
    return {
        'api_key': os.getenv('BINANCE_US_API_KEY'),
        'api_secret': os.getenv('BINANCE_US_API_SECRET')
    }

def get_coinbase_credentials():
    """Get Coinbase API credentials from environment variables."""
    return {
        'api_key': os.getenv('COINBASE_API_KEY'),
        'api_secret': os.getenv('COINBASE_API_SECRET')
    }

async def fetch_coinbase_price(symbol: str, session: aiohttp.ClientSession) -> Dict:
    """Fetch price data from Coinbase Advanced Trade API."""
    try:
        # Coinbase uses product format like XRP-USD
        product_id = f"{symbol}-USD"
        
        # Use public API endpoint (no auth required for price data)
        url = f"https://api.coinbase.com/api/v3/brokerage/market/products/{product_id}"
        
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                price = float(data.get('price', 0))
                
                # Get 24h stats for change calculation
                stats_url = f"https://api.coinbase.com/api/v3/brokerage/market/products/{product_id}/ticker"
                async with session.get(stats_url) as stats_response:
                    if stats_response.status == 200:
                        stats_data = await stats_response.json()
                        change_24h = float(stats_data.get('price_percent_chg_24h', 0))
                        volume = float(stats_data.get('volume', 0))
                        return {
                            'price': price,
                            'change_24h': change_24h,
                            'volume': volume
                        }
                
                return {'price': price, 'change_24h': 0, 'volume': 0}
            return {}
    except Exception as e:
        logger.error(f"Error fetching Coinbase data for {symbol}: {e}")
        return {}

def track_rate_limit(api_name: str) -> bool:
    """Track rate limit warnings for an API and return True if should switch APIs."""
    global RATE_LIMIT_WARNINGS
    
    if api_name not in RATE_LIMIT_WARNINGS:
        RATE_LIMIT_WARNINGS[api_name] = 0
    
    RATE_LIMIT_WARNINGS[api_name] += 1
    
    logger.warning(f"Rate limit warning #{RATE_LIMIT_WARNINGS[api_name]} for {api_name}")
    
    if RATE_LIMIT_WARNINGS[api_name] >= MAX_RATE_LIMIT_WARNINGS:
        logger.error(f"Switching away from {api_name} after {MAX_RATE_LIMIT_WARNINGS} rate limit warnings")
        return True
    
    return False

def reset_rate_limit_tracking():
    """Reset rate limit tracking (call periodically or after successful requests)."""
    global RATE_LIMIT_WARNINGS
    RATE_LIMIT_WARNINGS.clear()
    logger.info("Reset rate limit tracking for all APIs")

async def fetch_binance_us_price(symbol: str, session: aiohttp.ClientSession) -> Dict:
    """Fetch price data from Binance US API."""
    try:
        # Binance US uses different symbol format (e.g., XRPUSD instead of XRP/USD)
        binance_symbol = f"{symbol}USD"
        
        # Use public API endpoint (no auth required for price data)
        url = f"https://api.binance.us/api/v3/ticker/24hr"
        params = {'symbol': binance_symbol}
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'price': float(data.get('lastPrice', 0)),
                    'change_24h': float(data.get('priceChangePercent', 0)),
                    'volume': float(data.get('volume', 0))
                }
            return {}
    except Exception as e:
        logger.error(f"Error fetching Binance US data for {symbol}: {e}")
        return {}

async def fetch_cryptocompare_price(coin_symbol: str, session: aiohttp.ClientSession) -> Dict:
    """Fetch price data from CryptoCompare API."""
    api_key = get_cryptocompare_api_key()
    if not api_key:
        logger.warning("CryptoCompare API key not found")
        return {}
    
    try:
        url = f"https://min-api.cryptocompare.com/data/pricemultifull"
        params = {
            'fsyms': coin_symbol.upper(),
            'tsyms': 'USD',
            'api_key': api_key
        }
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if 'RAW' in data and coin_symbol.upper() in data['RAW']:
                    coin_data = data['RAW'][coin_symbol.upper()]['USD']
                    return {
                        'price': coin_data.get('PRICE', 0),
                        'change_24h': coin_data.get('CHANGEPCT24HOUR', 0),
                        'volume': coin_data.get('VOLUME24HOUR', 0)
                    }
            return {}
    except Exception as e:
        logger.error(f"Error fetching CryptoCompare data for {coin_symbol}: {e}")
        return {}

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

# Coinbase symbol mapping (some may not be available on Coinbase)
coinbase_symbol_map = {
    "ripple": "XRP",
    "stellar": "XLM",
    "sui": "SUI",
    "algorand": "ALGO"
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

async def fetch_with_exponential_backoff(session, url, coin_id, retries=3):
    """Fetch data with exponential backoff for rate limiting."""
    for attempt in range(retries):
        try:
            async with session.get(url) as response:
                if response.status == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited for {coin_id}, waiting {wait_time}s before retry {attempt + 1}")
                    await asyncio.sleep(wait_time)
                    if attempt == retries - 1:
                        raise aiohttp.ClientResponseError(None, None, status=429, message="Rate limited after retries")
                    continue
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            if attempt == retries - 1:
                raise
            wait_time = 2 ** attempt
            logger.warning(f"API error for {coin_id}, waiting {wait_time}s before retry {attempt + 1}")
            await asyncio.sleep(wait_time)
    
    raise Exception(f"Failed to fetch data for {coin_id} after {retries} retries")

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

async def fetch_coin_prices_multi_source(coin_ids: List[str], cg_client: CoinGeckoAPI, session: aiohttp.ClientSession) -> Dict[str, Dict[str, float]]:
    """
    Fetch current prices and 24h change for a list of coins using multiple APIs.
    Priority: CoinGecko -> Coinbase -> CoinMarketCap -> CryptoCompare -> Binance US
    Implements rate limit tracking and automatic API switching.
    """
    prices = {}
    failed_coins = []
    
    # Check if CoinGecko should be skipped due to rate limits
    skip_coingecko = RATE_LIMIT_WARNINGS.get('coingecko', 0) >= MAX_RATE_LIMIT_WARNINGS

    # Try CoinGecko first (unless rate limited)
    if not skip_coingecko:
        try:
            cg_data = cg_client.get_price(
                ids=coin_ids,
                vs_currencies=['usd'],
                include_24hr_change=True
            )
            for coin_id in coin_ids:
                if coin_id in cg_data:
                    prices[coin_id] = cg_data[coin_id]
                else:
                    failed_coins.append(coin_id)
                    logger.warning(f"CoinGecko: No data for {coin_id}")
            
            # Reset rate limit tracking on successful request
            if coin_ids and prices:
                RATE_LIMIT_WARNINGS.pop('coingecko', None)
                
        except Exception as e:
            error_str = str(e).lower()
            # Better rate limit detection
            if any(keyword in error_str for keyword in ["rate", "limit", "429", "too many"]):
                logger.warning(f"CoinGecko rate limit detected: {e}")
                if track_rate_limit('coingecko'):
                    logger.error("CoinGecko rate limited - switching to alternative APIs")
            else:
                logger.error(f"CoinGecko API error: {e}")
            failed_coins = coin_ids  # All coins failed, try fallbacks
    else:
        logger.info("Skipping CoinGecko due to rate limit warnings, using alternative APIs")
        failed_coins = coin_ids

    # Try Coinbase for failed coins
    coinbase_failed = []
    if failed_coins:
        for coin_id in failed_coins:
            symbol = symbol_map.get(coin_id, coin_id.split('-')[0].upper())
            try:
                coinbase_data = await fetch_coinbase_price(symbol, session)
                if coinbase_data and coinbase_data['price'] > 0:
                    prices[coin_id] = {
                        "usd": coinbase_data['price'],
                        "usd_24h_change": coinbase_data['change_24h']
                    }
                    logger.info(f"Coinbase: Got data for {coin_id}")
                else:
                    coinbase_failed.append(coin_id)
            except Exception as e:
                logger.error(f"Coinbase failed for {coin_id}: {e}")
                coinbase_failed.append(coin_id)

    # Try CoinMarketCap for remaining failed coins
    coinmarketcap_api_key = os.getenv("COINMARKETCAP_API_KEY")
    remaining_failed = []
    if coinbase_failed and coinmarketcap_api_key:
        try:
            cmc_data = fetch_coinmarketcap_prices(coinbase_failed)
            for coin_id in coinbase_failed:
                if coin_id in cmc_data:
                    prices[coin_id] = cmc_data[coin_id]
                else:
                    remaining_failed.append(coin_id)
        except Exception as e:
            logger.error(f"CoinMarketCap fallback failed: {e}")
            remaining_failed = coinbase_failed
    else:
        remaining_failed = coinbase_failed

    # Try CryptoCompare for remaining failed coins
    still_failed = []
    if remaining_failed:
        for coin_id in remaining_failed:
            symbol = symbol_map.get(coin_id, coin_id.split('-')[0].upper())
            try:
                cc_data = await fetch_cryptocompare_price(symbol, session)
                if cc_data:
                    prices[coin_id] = {
                        "usd": cc_data['price'],
                        "usd_24h_change": cc_data['change_24h']
                    }
                    logger.info(f"CryptoCompare: Got data for {coin_id}")
                else:
                    still_failed.append(coin_id)
            except Exception as e:
                logger.error(f"CryptoCompare failed for {coin_id}: {e}")
                still_failed.append(coin_id)

    # Try Binance US for still failed coins
    if still_failed:
        for coin_id in still_failed:
            symbol = symbol_map.get(coin_id, coin_id.split('-')[0].upper())
            try:
                binance_data = await fetch_binance_us_price(symbol, session)
                if binance_data:
                    prices[coin_id] = {
                        "usd": binance_data['price'],
                        "usd_24h_change": binance_data['change_24h']
                    }
                    logger.info(f"Binance US: Got data for {coin_id}")
                else:
                    # Final fallback to mock data
                    prices[coin_id] = {"usd": 0.0, "usd_24h_change": 0.0}
                    logger.warning(f"Using mock data for {coin_id}")
            except Exception as e:
                logger.error(f"Binance US failed for {coin_id}: {e}")
                prices[coin_id] = {"usd": 0.0, "usd_24h_change": 0.0}

    return prices

def fetch_coin_prices(coin_ids: List[str], cg_client: CoinGeckoAPI) -> Dict[str, Dict[str, float]]:
    """
    Fetch current prices and 24h change for a list of coins using CoinGecko.
    Falls back to CoinMarketCap if CoinGecko fails.
    """
    prices = {}
    failed_coins = []

    # Try CoinGecko first
    try:
        cg_data = cg_client.get_price(
            ids=coin_ids,
            vs_currencies=['usd'],
            include_24hr_change=True
        )
        for coin_id in coin_ids:
            if coin_id in cg_data:
                prices[coin_id] = cg_data[coin_id]
            else:
                failed_coins.append(coin_id)
                logger.warning(f"CoinGecko: No data for {coin_id}")
    except Exception as e:
        logger.error(f"CoinGecko API error: {e}")
        failed_coins = coin_ids  # All coins failed, try CoinMarketCap

    # Try CoinMarketCap for failed coins (only if API key exists)
    coinmarketcap_api_key = os.getenv("COINMARKETCAP_API_KEY")
    if failed_coins and coinmarketcap_api_key:
        try:
            cmc_data = fetch_coinmarketcap_prices(failed_coins)
            prices.update(cmc_data)
        except Exception as e:
            logger.error(f"CoinMarketCap fallback failed: {e}")
    elif failed_coins and not coinmarketcap_api_key:
        logger.warning("CoinMarketCap API key not found, skipping fallback")
        # Provide mock data for failed coins to prevent crashes
        for coin_id in failed_coins:
            prices[coin_id] = {"usd": 0.0, "usd_24h_change": 0.0}
            logger.warning(f"Using mock data for {coin_id}")

    return prices

async def fetch_volume(coin_id: str, session: aiohttp.ClientSession) -> float:
    """Fetch 24h volume for a coin from CoinGecko API with aggressive rate limiting protection."""
    import asyncio

    # Check if we should skip CoinGecko due to rate limits
    skip_coingecko = RATE_LIMIT_WARNINGS.get('coingecko', 0) >= MAX_RATE_LIMIT_WARNINGS
    if skip_coingecko:
        logger.info(f"Skipping volume fetch for {coin_id} due to CoinGecko rate limits")
        return 0.0

    max_retries = 2  # Reduced retries to avoid hitting limits
    retry_delay = 30  # Much longer delays

    for attempt in range(max_retries):
        try:
            # Add delay before each request
            if attempt > 0:
                await asyncio.sleep(retry_delay)
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    volume = data.get("market_data", {}).get("total_volume", {}).get("usd", 0)
                    return round(volume / 1_000_000, 2)  # Convert to millions
                elif response.status == 429:  # Rate limited
                    logger.warning(f"CoinGecko rate limited for volume {coin_id}")
                    if track_rate_limit('coingecko'):
                        logger.error("Switching away from CoinGecko for volume fetches")
                    return 0.0
                else:
                    error_text = await response.text()
                    logger.error(f"CoinGecko API error for volume {coin_id}: {response.status}")
                    return 0.0
        except Exception as e:
            logger.error(f"Error fetching volume for {coin_id}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            return 0.0

    return 0.0

async def fetch_top_project(coin_id: str, session: aiohttp.ClientSession) -> str:
    """Fetch the top project (exchange) for a coin using CoinGecko API with rate limit protection."""
    cache = load_top_project_cache()
    if coin_id in cache:
        logger.debug(f"Using cached top project for {coin_id}: {cache[coin_id]}")
        return cache[coin_id]

    # Check if we should skip CoinGecko due to rate limits
    skip_coingecko = RATE_LIMIT_WARNINGS.get('coingecko', 0) >= MAX_RATE_LIMIT_WARNINGS
    if skip_coingecko:
        logger.info(f"Skipping top project fetch for {coin_id} due to CoinGecko rate limits, using fallback")
        project_map = {
            "hedera-hashgraph": "Binance CEX",
            "stellar": "Binance CEX", 
            "sui": "Binance CEX",
            "algorand": "Binance CEX",
            "xdce-crowd-sale": "Gate",
            "casper-network": "Gate",
            "ondo-finance": "Binance CEX",
            "ripple": "Binance CEX"
        }
        top_project = project_map.get(coin_id, "N/A")
        cache[coin_id] = top_project
        save_top_project_cache(cache)
        return top_project

    try:
        # Add delay before API call
        await asyncio.sleep(5)
        
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/tickers"
        async with session.get(url) as response:
            if response.status == 429:
                logger.warning(f"CoinGecko rate limited for top project {coin_id}")
                if track_rate_limit('coingecko'):
                    logger.error("Switching away from CoinGecko for top project fetches")
                raise aiohttp.ClientResponseError(None, None, status=429, message="Rate limited")
            response.raise_for_status()
            data = await response.json()
            
            if 'tickers' not in data or not data['tickers']:
                logger.warning(f"No tickers found for {coin_id}, using fallback.")
                raise ValueError("No tickers found")
                
            top_ticker = max(data['tickers'], key=lambda x: x.get('volume', 0))
            top_exchange = top_ticker.get('market', {}).get('name', "N/A")
            if top_exchange == "N/A":
                raise ValueError("No exchange name found")
            cache[coin_id] = top_exchange
            save_top_project_cache(cache)
            return top_exchange
            
    except (aiohttp.ClientError, ValueError) as e:
        logger.warning(f"CoinGecko API error for top project {coin_id}: {e}, using fallback")
        project_map = {
            "hedera-hashgraph": "Binance CEX",
            "stellar": "Binance CEX",
            "sui": "Binance CEX", 
            "algorand": "Binance CEX",
            "xdce-crowd-sale": "Gate",
            "casper-network": "Gate",
            "ondo-finance": "Binance CEX",
            "ripple": "Binance CEX"
        }
        top_project = project_map.get(coin_id, "N/A")
        cache[coin_id] = top_project
        save_top_project_cache(cache)
        return top_project