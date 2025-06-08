
#!/usr/bin/env python3
"""
Comprehensive diagnostic script to identify why X threads don't mirror Discord data
"""

import asyncio
import logging
import json
import aiohttp
from datetime import datetime
from modules.database import Database
from modules.social_media import fetch_social_metrics
from modules.api_clients import get_youtube_api_key
from googleapiclient.discovery import build
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DiscordXDiagnostic')

# Same coin list as bot_v2.py
COINS = [
    {'name': 'ripple', 'coingecko_id': 'ripple', 'symbol': 'XRP', 'hashtag': '#XRP', 'top_project': 'Binance'},
    {'name': 'hedera hashgraph', 'coingecko_id': 'hedera-hashgraph', 'symbol': 'HBAR', 'hashtag': '#HBAR', 'top_project': 'Binance CEX'},
    {'name': 'stellar', 'coingecko_id': 'stellar', 'symbol': 'XLM', 'hashtag': '#XLM', 'top_project': 'Binance CEX'},
    {'name': 'xdce crowd sale', 'coingecko_id': 'xinfin-network', 'symbol': 'XDC', 'hashtag': '#XDC', 'top_project': 'Gate'},
    {'name': 'sui', 'coingecko_id': 'sui', 'symbol': 'SUI', 'hashtag': '#SUI', 'top_project': 'Binance'},
    {'name': 'ondo finance', 'coingecko_id': 'ondo-finance', 'symbol': 'ONDO', 'hashtag': '#ONDO', 'top_project': 'Upbit'},
    {'name': 'algorand', 'coingecko_id': 'algorand', 'symbol': 'ALGO', 'hashtag': '#ALGO', 'top_project': 'Binance'},
    {'name': 'casper network', 'coingecko_id': 'casper-network', 'symbol': 'CSPR', 'hashtag': '#CSPR', 'top_project': 'Gate'}
]

async def research_top_projects(coingecko_id: str, coin_symbol: str, session: aiohttp.ClientSession):
    """Research function from bot_v2.py"""
    known_projects = {
        'ripple': {
            'name': 'XRP Ledger',
            'url': 'https://xrpl.org/',
            'description': 'A decentralized cryptographic ledger powered by a network of peer-to-peer servers.',
            'type': 'Blockchain'
        },
        'hedera-hashgraph': {
            'name': 'Hashgraph Consensus Service',
            'url': 'https://www.hedera.com/',
            'description': 'An enterprise-grade distributed ledger for building fast, fair and secure applications.',
            'type': 'Blockchain'
        },
        'stellar': {
            'name': 'Stellar DEX',
            'url': 'https://stellar.org/',
            'description': 'A decentralized exchange built on the Stellar network, enabling fast and low-cost asset trading.',
            'type': 'DEX'
        },
        'xinfin-network': {
            'name': 'XinFin Network',
            'url': 'https://xinfin.org/',
            'description': 'A hybrid blockchain platform optimized for international trade and finance.',
            'type': 'Blockchain'
        },
        'sui': {
            'name': 'Sui Blockchain',
            'url': 'https://sui.io/',
            'description': 'A permissionless Layer 1 blockchain designed to enable creators and developers to build experiences that cater for the next billion users in web3.',
            'type': 'Blockchain'
        },
        'ondo-finance': {
            'name': 'Ondo Finance',
            'url': 'https://ondo.finance/',
            'description': 'A decentralized investment bank connecting institutional investors with DeFi.',
            'type': 'DeFi Platform'
        },
        'algorand': {
            'name': 'Algorand DeFi Ecosystem',
            'url': 'https://www.algorand.com/',
            'description': 'A range of decentralized finance (DeFi) applications and protocols built on the Algorand blockchain.',
            'type': 'DeFi Ecosystem'
        },
        'casper-network': {
            'name': 'CasperSwap',
            'url': 'https://casperswap.io/',
            'description': 'A decentralized exchange (DEX) built on the Casper Network blockchain.',
            'type': 'DEX'
        }
    }

    if coingecko_id in known_projects:
        top_project = known_projects[coingecko_id]
        logger.info(f"Top project found for {coin_symbol}: {top_project['name']}")
    else:
        top_project = {}
        logger.warning(f"No top project found for {coin_symbol}. Using default values.")

    return {'top_project': top_project}

async def fetch_youtube_video_diagnostic(coin: str, current_date: str, session: aiohttp.ClientSession = None):
    """Diagnostic version of YouTube video fetching"""
    try:
        youtube_api_key = get_youtube_api_key()
        if not youtube_api_key:
            return {
                "title": f"YouTube API key missing for {coin}",
                "url": f"https://youtube.com/search?q={coin.replace(' ', '+')}+crypto",
                "error": "NO_API_KEY"
            }
        
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        search_query = f"{coin} crypto 2025"
        
        request = youtube.search().list(
            part="snippet",
            q=search_query,
            type="video",
            maxResults=3,
            publishedAfter="2024-01-01T00:00:00Z"
        )
        response = request.execute()
        
        if response.get('items'):
            item = response['items'][0]
            return {
                "title": item['snippet']['title'],
                "url": f"https://youtu.be/{item['id']['videoId']}",
                "channel": item['snippet'].get('channelTitle', ''),
                "published": item['snippet'].get('publishedAt', ''),
                "error": None
            }
        else:
            return {
                "title": f"No videos found for {coin}",
                "url": f"https://youtube.com/search?q={coin.replace(' ', '+')}+crypto",
                "error": "NO_VIDEOS_FOUND"
            }
            
    except Exception as e:
        return {
            "title": f"YouTube error for {coin}",
            "url": f"https://youtube.com/search?q={coin.replace(' ', '+')}+crypto",
            "error": str(e)
        }

def format_discord_post(data):
    """Format data as it would appear in Discord"""
    change_symbol = "📉" if data['price_change_24h'] < 0 else "📈"
    
    # Build project info with URL if available
    top_project_text = f"{data['top_project']}"
    if data.get('top_project_url'):
        top_project_text += f" - {data['top_project_url']}"
    
    return (
        f"{data['coin_name']} ({data['coin_symbol']}): ${data['price']:.2f} ({data['price_change_24h']:.2f}% 24h) {change_symbol}\n"
        f"Predicted: ${data['predicted_price']:.2f} (Linear regression)\n"
        f"Tx Volume: {data['tx_volume']:.2f}M\n"
        f"Top Project: {top_project_text}\n"
        f"{data['hashtag']}\n"
        f"Social: {data['social_metrics']['mentions']} mentions, {data['social_metrics']['sentiment']}\n"
        f"Video: {data['youtube_video']['title']}... {data['youtube_video']['url']}"
    )

def format_x_post(data):
    """Format data as it would appear in X thread"""
    change_symbol = "📉" if data['price_change_24h'] < 0 else "📈"
    
    # Build project info with URL if available  
    top_project_text = f"{data['top_project']}"
    if data.get('top_project_url'):
        top_project_text += f" - {data['top_project_url']}"
    
    post_text = (
        f"2/9 {data['coin_name']} ({data['coin_symbol']}) {change_symbol}\n\n"
        f"💰 Price: ${data['price']:.2f}\n"
        f"📊 24h Change: {data['price_change_24h']:.2f}%\n"
        f"🔮 Predicted: ${data['predicted_price']:.2f}\n"
        f"💹 Volume: {data['tx_volume']:.2f}M\n"
        f"🏢 Top Project: {top_project_text}\n\n"
        f"📱 Social: {data['social_metrics']['mentions']} mentions, {data['social_metrics']['sentiment']}\n\n"
        f"🎥 Latest: {data['youtube_video']['title'][:50]}...\n{data['youtube_video']['url']}\n\n"
        f"{data['hashtag']}"
    )
    return post_text

async def diagnose_content_differences():
    """Main diagnostic function"""
    print("🔍 DISCORD vs X CONTENT DIAGNOSTIC")
    print("=" * 60)
    
    issues_found = []
    diagnostic_data = {}
    
    async with aiohttp.ClientSession() as session:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        print("\n📊 Analyzing data collection for each coin...")
        
        for coin in COINS:
            print(f"\n🔍 Analyzing: {coin['name']} ({coin['symbol']})")
            coin_issues = []
            coin_data = {}
            
            # 1. Check social metrics
            print("  📱 Checking social metrics...")
            try:
                social_metrics = await fetch_social_metrics(coin['coingecko_id'], session, skip_x_api=False)
                coin_data['social_metrics'] = social_metrics
                
                if social_metrics['mentions'] < 5:
                    coin_issues.append("Very low social mentions")
                if social_metrics['sentiment'] == "Neutral":
                    coin_issues.append("No sentiment analysis data")
                if not social_metrics.get('sources'):
                    coin_issues.append("Missing social data sources")
                    
                print(f"    ✅ Social: {social_metrics['mentions']} mentions, {social_metrics['sentiment']}")
                
            except Exception as e:
                coin_issues.append(f"Social metrics error: {e}")
                coin_data['social_metrics'] = {'mentions': 0, 'sentiment': 'Error', 'sources': []}
                print(f"    ❌ Social metrics failed: {e}")
            
            # 2. Check YouTube video content
            print("  🎥 Checking YouTube content...")
            try:
                youtube_video = await fetch_youtube_video_diagnostic(coin['name'], current_date, session)
                coin_data['youtube_video'] = youtube_video
                
                if youtube_video.get('error'):
                    coin_issues.append(f"YouTube error: {youtube_video['error']}")
                if 'youtube.com/search' in youtube_video.get('url', ''):
                    coin_issues.append("Using fallback YouTube search URL instead of actual video")
                    
                print(f"    ✅ Video: {youtube_video['title'][:50]}...")
                if youtube_video.get('error'):
                    print(f"    ⚠️  Video error: {youtube_video['error']}")
                    
            except Exception as e:
                coin_issues.append(f"YouTube error: {e}")
                coin_data['youtube_video'] = {'title': f'Error for {coin["name"]}', 'url': '', 'error': str(e)}
                print(f"    ❌ YouTube failed: {e}")
            
            # 3. Check on-chain project research
            print("  🔗 Checking on-chain project data...")
            try:
                project_research = await research_top_projects(coin['coingecko_id'], coin['symbol'], session)
                top_project_info = project_research.get('top_project', {})
                coin_data['project_research'] = project_research
                coin_data['top_project'] = top_project_info.get('name', coin['top_project'])
                coin_data['top_project_url'] = top_project_info.get('url', '')
                coin_data['top_project_description'] = top_project_info.get('description', '')
                coin_data['top_project_type'] = top_project_info.get('type', 'Exchange')
                
                if not top_project_info.get('url'):
                    coin_issues.append("Missing on-chain project URL")
                if not top_project_info.get('description'):
                    coin_issues.append("Missing project description")
                    
                print(f"    ✅ Project: {coin_data['top_project']}")
                if coin_data['top_project_url']:
                    print(f"    ✅ URL: {coin_data['top_project_url']}")
                else:
                    print(f"    ❌ Missing project URL")
                    
            except Exception as e:
                coin_issues.append(f"Project research error: {e}")
                coin_data['project_research'] = {}
                coin_data['top_project'] = coin['top_project']
                coin_data['top_project_url'] = ''
                print(f"    ❌ Project research failed: {e}")
            
            # Add sample price data for formatting test
            coin_data.update({
                'coin_name': coin['name'],
                'coin_symbol': coin['symbol'],
                'price': 1.50,
                'price_change_24h': 5.2,
                'predicted_price': 1.58,
                'tx_volume': 100.0,
                'hashtag': coin['hashtag']
            })
            
            # 4. Compare Discord vs X formatting
            print("  📝 Comparing Discord vs X formatting...")
            try:
                discord_format = format_discord_post(coin_data)
                x_format = format_x_post(coin_data)
                
                # Check for missing elements in X format
                if coin_data['top_project_url'] and coin_data['top_project_url'] not in x_format:
                    coin_issues.append("Project URL missing from X format")
                if coin_data['social_metrics']['mentions'] and str(coin_data['social_metrics']['mentions']) not in x_format:
                    coin_issues.append("Social mentions missing from X format")
                if coin_data['youtube_video']['url'] and coin_data['youtube_video']['url'] not in x_format:
                    coin_issues.append("Video URL missing from X format")
                    
                print(f"    ✅ Format comparison completed")
                
            except Exception as e:
                coin_issues.append(f"Format comparison error: {e}")
                print(f"    ❌ Format comparison failed: {e}")
            
            if coin_issues:
                issues_found.extend([f"{coin['symbol']}: {issue}" for issue in coin_issues])
                print(f"  ⚠️  Found {len(coin_issues)} issues for {coin['symbol']}")
            else:
                print(f"  ✅ No issues found for {coin['symbol']}")
            
            diagnostic_data[coin['symbol']] = {
                'data': coin_data,
                'issues': coin_issues
            }
    
    # Generate comprehensive report
    print("\n" + "=" * 60)
    print("📋 COMPREHENSIVE DIAGNOSTIC REPORT")
    print("=" * 60)
    
    if issues_found:
        print(f"\n❌ FOUND {len(issues_found)} ISSUES:")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")
        
        print(f"\n🔧 RECOMMENDED FIXES:")
        
        # Social metrics issues
        social_issues = [i for i in issues_found if 'social' in i.lower() or 'mentions' in i.lower()]
        if social_issues:
            print(f"\n📱 Social Metrics Issues ({len(social_issues)}):")
            print(f"   • Check X API search functionality in social_media.py")
            print(f"   • Verify alternative social APIs are working")
            print(f"   • Check social metrics cache validity")
        
        # YouTube/video issues  
        video_issues = [i for i in issues_found if 'youtube' in i.lower() or 'video' in i.lower()]
        if video_issues:
            print(f"\n🎥 Video Content Issues ({len(video_issues)}):")
            print(f"   • Check YouTube API quota and key validity")
            print(f"   • Verify Rumble fallback is working")
            print(f"   • Check if database has unused video tracking")
        
        # Project research issues
        project_issues = [i for i in issues_found if 'project' in i.lower() or 'url' in i.lower()]
        if project_issues:
            print(f"\n🔗 On-Chain Project Issues ({len(project_issues)}):")
            print(f"   • Verify research_top_projects function in bot_v2.py")
            print(f"   • Check known_projects dictionary completeness")
            print(f"   • Ensure project URLs are being included in format functions")
        
        # Format issues
        format_issues = [i for i in issues_found if 'format' in i.lower() or 'missing from' in i.lower()]
        if format_issues:
            print(f"\n📝 Formatting Issues ({len(format_issues)}):")
            print(f"   • Check format_tweet and create_thread_post functions")
            print(f"   • Verify all data fields are being passed to formatting")
            print(f"   • Ensure Discord and X use same data sources")
    
    else:
        print("\n✅ NO ISSUES FOUND!")
        print("Discord and X content should be properly mirrored.")
    
    # Save detailed diagnostic data
    with open('discord_x_diagnostic_report.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'issues_found': issues_found,
            'diagnostic_data': diagnostic_data,
            'summary': {
                'total_issues': len(issues_found),
                'coins_analyzed': len(COINS),
                'issues_by_category': {
                    'social_metrics': len([i for i in issues_found if 'social' in i.lower()]),
                    'video_content': len([i for i in issues_found if 'video' in i.lower() or 'youtube' in i.lower()]),
                    'project_research': len([i for i in issues_found if 'project' in i.lower()]),
                    'formatting': len([i for i in issues_found if 'format' in i.lower()])
                }
            }
        }, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: discord_x_diagnostic_report.json")
    print(f"\n🛠️  Next steps:")
    print(f"   1. Review the issues above")
    print(f"   2. Fix the identified problems")
    print(f"   3. Test with --test-discord to verify Discord posting")
    print(f"   4. Only then test X posting with queue system")

if __name__ == "__main__":
    asyncio.run(diagnose_content_differences())
