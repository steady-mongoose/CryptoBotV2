
import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger('CryptoBot')

# Cache file for project research
PROJECT_RESEARCH_CACHE_FILE = "project_research_cache.json"

def load_project_research_cache() -> Dict[str, Dict]:
    """Load cached project research from a file."""
    if os.path.exists(PROJECT_RESEARCH_CACHE_FILE):
        try:
            with open(PROJECT_RESEARCH_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading project research cache: {e}")
            return {}
    return {}

def save_project_research_cache(cache: Dict[str, Dict]):
    """Save project research to a file."""
    try:
        with open(PROJECT_RESEARCH_CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=4)
        logger.debug("Project research cache saved successfully.")
    except Exception as e:
        logger.error(f"Error saving project research cache: {e}")

async def fetch_defillama_projects(session: aiohttp.ClientSession, chain_name: str) -> List[Dict]:
    """Fetch projects from DeFiLlama for a specific chain."""
    try:
        url = f"https://api.llama.fi/protocols"
        async with session.get(url) as response:
            if response.status == 200:
                all_protocols = await response.json()
                # Filter protocols for the specific chain
                chain_protocols = [
                    protocol for protocol in all_protocols 
                    if chain_name.lower() in [chain.lower() for chain in protocol.get('chains', [])]
                ]
                
                # Sort by TVL (Total Value Locked) and take top 3
                sorted_protocols = sorted(
                    chain_protocols, 
                    key=lambda x: x.get('tvl', 0), 
                    reverse=True
                )[:3]
                
                logger.info(f"Found {len(sorted_protocols)} top DeFi projects for {chain_name}")
                return sorted_protocols
            
        await asyncio.sleep(1)  # Rate limiting
    except Exception as e:
        logger.error(f"Error fetching DeFiLlama data for {chain_name}: {e}")
    
    return []

async def fetch_github_projects(session: aiohttp.ClientSession, coin_symbol: str) -> List[Dict]:
    """Fetch recent GitHub projects related to the coin."""
    try:
        # Search for recent repositories
        search_query = f"{coin_symbol} blockchain cryptocurrency"
        url = f"https://api.github.com/search/repositories"
        params = {
            'q': f"{search_query} created:>2024-01-01",
            'sort': 'updated',
            'order': 'desc',
            'per_page': 3
        }
        
        headers = {'User-Agent': 'CryptoBot/1.0'}
        async with session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                projects = []
                
                for repo in data.get('items', [])[:3]:
                    projects.append({
                        'name': repo['name'],
                        'description': repo['description'] or 'No description available',
                        'url': repo['html_url'],
                        'stars': repo['stargazers_count'],
                        'updated_at': repo['updated_at'],
                        'language': repo['language']
                    })
                
                logger.info(f"Found {len(projects)} GitHub projects for {coin_symbol}")
                return projects
            
        await asyncio.sleep(1)  # Rate limiting
    except Exception as e:
        logger.error(f"Error fetching GitHub data for {coin_symbol}: {e}")
    
    return []

async def fetch_coingecko_ecosystem(session: aiohttp.ClientSession, coin_id: str) -> Dict:
    """Fetch ecosystem information from CoinGecko."""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'false',
            'community_data': 'false',
            'developer_data': 'true'
        }
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                
                # Extract useful project information
                project_info = {
                    'homepage': data.get('links', {}).get('homepage', []),
                    'blockchain_site': data.get('links', {}).get('blockchain_site', []),
                    'official_forum_url': data.get('links', {}).get('official_forum_url', []),
                    'repos_url': data.get('links', {}).get('repos_url', {}),
                    'developer_data': data.get('developer_data', {})
                }
                
                logger.info(f"Fetched ecosystem data for {coin_id}")
                return project_info
            
        await asyncio.sleep(2)  # CoinGecko rate limiting
    except Exception as e:
        logger.error(f"Error fetching CoinGecko ecosystem data for {coin_id}: {e}")
    
    return {}

async def fetch_dappradar_projects(session: aiohttp.ClientSession, chain_name: str) -> List[Dict]:
    """Fetch trending dApps from DappRadar for a specific chain."""
    try:
        # Map coin names to DappRadar chain names
        chain_mapping = {
            'ethereum': 'ethereum',
            'binance': 'binance-smart-chain',
            'polygon': 'polygon',
            'solana': 'solana',
            'avalanche': 'avalanche',
            'fantom': 'fantom',
            'harmony': 'harmony',
            'xrp': 'xrp',
            'stellar': 'stellar',
            'algorand': 'algorand',
            'hedera': 'hedera',
            'sui': 'sui'
        }
        
        chain_slug = chain_mapping.get(chain_name.lower())
        if not chain_slug:
            return []
        
        # Note: DappRadar API requires API key for full access
        # This is a simplified version that would need proper API integration
        url = f"https://api.dappradar.com/4tsxo4vuhotaojtl/dapps/chain/{chain_slug}"
        headers = {'User-Agent': 'CryptoBot/1.0'}
        
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                # Process the response (this would need adjustment based on actual API response)
                projects = data.get('results', [])[:3] if isinstance(data, dict) else []
                logger.info(f"Found {len(projects)} DappRadar projects for {chain_name}")
                return projects
            
        await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Error fetching DappRadar data for {chain_name}: {e}")
    
    return []

async def research_top_projects(coin_id: str, coin_symbol: str, session: aiohttp.ClientSession) -> Dict:
    """Comprehensive on-chain project research for a coin."""
    cache = load_project_research_cache()
    
    # Check if we have recent cached data (less than 12 hours old)
    if coin_id in cache:
        if "timestamp" in cache[coin_id] and "data" in cache[coin_id]:
            timestamp = cache[coin_id]["timestamp"]
            if isinstance(timestamp, str):
                cached_time = datetime.fromisoformat(timestamp)
            else:
                cached_time = datetime.fromtimestamp(timestamp)
            
            if datetime.now() - cached_time < timedelta(hours=12):
                logger.info(f"Using cached project research for {coin_id}")
                return cache[coin_id]["data"]
    
    logger.info(f"Conducting on-chain research for {coin_symbol} ({coin_id})")
    
    # Map coin IDs to chain names for ecosystem research
    chain_mapping = {
        'ripple': 'xrp',
        'stellar': 'stellar',
        'hedera-hashgraph': 'hedera',
        'algorand': 'algorand',
        'sui': 'sui',
        'ondo-finance': 'ethereum',  # ONDO is primarily on Ethereum
        'xinfin-network': 'xdc',
        'casper-network': 'casper'
    }
    
    chain_name = chain_mapping.get(coin_id, coin_symbol.lower())
    
    # Gather data from multiple sources
    tasks = [
        fetch_defillama_projects(session, chain_name),
        fetch_github_projects(session, coin_symbol),
        fetch_coingecko_ecosystem(session, coin_id),
        fetch_dappradar_projects(session, chain_name)
    ]
    
    try:
        defi_projects, github_projects, ecosystem_data, dapp_projects = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions in the results
        if isinstance(defi_projects, Exception):
            defi_projects = []
        if isinstance(github_projects, Exception):
            github_projects = []
        if isinstance(ecosystem_data, Exception):
            ecosystem_data = {}
        if isinstance(dapp_projects, Exception):
            dapp_projects = []
        
        # Find the most promising project
        top_project = determine_top_project(defi_projects, github_projects, dapp_projects, coin_symbol)
        
        result = {
            "top_project": top_project,
            "defi_projects": defi_projects[:2],  # Top 2 DeFi projects
            "github_projects": github_projects[:2],  # Top 2 GitHub projects
            "ecosystem_links": ecosystem_data,
            "research_timestamp": datetime.now().isoformat(),
            "confidence": len(defi_projects) + len(github_projects) > 0
        }
        
        # Cache the result
        cache[coin_id] = {
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        save_project_research_cache(cache)
        
        logger.info(f"Completed project research for {coin_symbol}")
        return result
        
    except Exception as e:
        logger.error(f"Error in project research for {coin_id}: {e}")
        return {
            "top_project": {"name": "Research Unavailable", "url": "", "description": "Unable to fetch current project data"},
            "defi_projects": [],
            "github_projects": [],
            "ecosystem_links": {},
            "research_timestamp": datetime.now().isoformat(),
            "confidence": False
        }

def determine_top_project(defi_projects: List[Dict], github_projects: List[Dict], dapp_projects: List[Dict], coin_symbol: str) -> Dict:
    """Determine the most promising project from all sources."""
    
    # Priority: DeFi projects with high TVL, then popular GitHub projects, then dApps
    if defi_projects:
        top_defi = defi_projects[0]
        return {
            "name": top_defi.get('name', 'Unknown DeFi Project'),
            "url": top_defi.get('url', f"https://defillama.com/protocol/{top_defi.get('slug', '')}"),
            "description": f"Leading DeFi protocol with ${top_defi.get('tvl', 0):,.0f} TVL",
            "type": "DeFi Protocol",
            "metrics": f"TVL: ${top_defi.get('tvl', 0):,.0f}"
        }
    
    if github_projects:
        top_github = github_projects[0]
        return {
            "name": top_github.get('name', 'Unknown Project'),
            "url": top_github.get('url', ''),
            "description": top_github.get('description', 'Active development project'),
            "type": "Development Project",
            "metrics": f"⭐ {top_github.get('stars', 0)} stars"
        }
    
    if dapp_projects:
        top_dapp = dapp_projects[0]
        return {
            "name": top_dapp.get('name', 'Unknown dApp'),
            "url": top_dapp.get('url', ''),
            "description": top_dapp.get('description', 'Popular decentralized application'),
            "type": "dApp",
            "metrics": "Trending on DappRadar"
        }
    
    # Fallback to traditional exchange/platform
    fallback_projects = {
        'XRP': {"name": "RippleNet", "url": "https://ripple.com/ripplenet/", "description": "Global payments network"},
        'HBAR': {"name": "Hedera Consensus Service", "url": "https://hedera.com/consensus", "description": "Enterprise blockchain platform"},
        'XLM': {"name": "Stellar Development Foundation", "url": "https://stellar.org", "description": "Financial infrastructure platform"},
        'XDC': {"name": "XinFin Network", "url": "https://xinfin.org", "description": "Enterprise blockchain for trade finance"},
        'SUI': {"name": "Sui Ecosystem", "url": "https://sui.io/ecosystem", "description": "Next-generation smart contract platform"},
        'ONDO': {"name": "Ondo Finance", "url": "https://ondo.finance", "description": "Institutional-grade DeFi protocols"},
        'ALGO': {"name": "Algorand Foundation", "url": "https://algorand.org", "description": "Pure proof-of-stake blockchain"},
        'CSPR': {"name": "Casper Association", "url": "https://casper.network", "description": "Enterprise blockchain for developers"}
    }
    
    fallback = fallback_projects.get(coin_symbol, {
        "name": f"{coin_symbol} Ecosystem", 
        "url": "", 
        "description": "Blockchain ecosystem project"
    })
    
    return {
        **fallback,
        "type": "Ecosystem",
        "metrics": "Official project"
    }
