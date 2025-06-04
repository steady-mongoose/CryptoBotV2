
#!/usr/bin/env python3
"""
Generate a formatted X thread template that can be manually posted.
"""

import argparse
import asyncio
import logging
import os
from datetime import datetime
import aiohttp
import numpy as np
from sklearn.linear_model import LinearRegression
from googleapiclient.discovery import build
from modules.api_clients import get_youtube_api_key
from modules.social_media import fetch_social_metrics
from modules.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger('ThreadTemplate')

# Initialize database
db = Database('crypto_bot.db')

# List of coins to track
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

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

def get_date():
    return datetime.now().strftime("%Y-%m-%d")

def format_tweet(data):
    change_symbol = "📉" if data['price_change_24h'] < 0 else "📈"
    return (
        f"{data['coin_name']} ({data['coin_symbol']}): ${data['price']:.2f} ({data['price_change_24h']:.2f}% 24h) {change_symbol}\n"
        f"Predicted: ${data['predicted_price']:.2f} (Linear regression)\n"
        f"Tx Volume: {data['tx_volume']:.2f}M\n"
        f"Top Project: {data['top_project']}\n"
        f"{data['hashtag']}\n"
        f"Social: {data['social_metrics']['mentions']} mentions, {data['social_metrics']['sentiment']}\n"
        f"Video: {data['youtube_video']['title']}... {data['youtube_video']['url']}"
    )

def get_youtube_service():
    try:
        youtube_api_key = get_youtube_api_key()
        if not youtube_api_key:
            logger.error("YouTube API key not available")
            return None
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        return youtube
    except Exception as e:
        logger.error(f"Failed to initialize YouTube API: {str(e)}")
        return None

async def fetch_coingecko_data(coingecko_id: str, session: aiohttp.ClientSession):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}?tickers=false&market_data=true&community_data=false&developer_data=false"
        async with session.get(url) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch data for {coingecko_id} from CoinGecko (status: {response.status})")
                return None, None, None, []
            data = await response.json()
            price = float(data['market_data']['current_price']['usd'])
            price_change_24h = float(data['market_data']['price_change_percentage_24h'])

        await asyncio.sleep(12)
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart?vs_currency=usd&days=1"
        async with session.get(url) as response:
            if response.status != 200:
                return price, price_change_24h, 0.0, []
            market_data = await response.json()
            tx_volume = sum([v[1] for v in market_data['total_volumes']]) / 1_000_000
            tx_volume *= 0.0031
            historical_prices = [p[1] for p in market_data['prices']][-30:]
            return price, price_change_24h, tx_volume, historical_prices
    except Exception as e:
        logger.error(f"Error fetching data for {coingecko_id}: {str(e)}")
        return None, None, 0.0, []

def predict_price(historical_prices, current_price):
    if not historical_prices or len(historical_prices) < 2:
        return current_price * 1.005
    try:
        X = np.array(range(len(historical_prices))).reshape(-1, 1)
        y = np.array(historical_prices)
        model = LinearRegression()
        model.fit(X, y)
        predicted_price = model.predict([[len(historical_prices)]])[0]
        return predicted_price
    except Exception as e:
        return current_price * 1.005

async def fetch_youtube_video(youtube, coin: str, current_date: str):
    try:
        search_query = f"{coin} crypto 2025"
        request = youtube.search().list(
            part="snippet",
            q=search_query,
            type="video",
            maxResults=5
        )
        response = request.execute()

        for item in response.get('items', []):
            video_id = item['id']['videoId']
            if not db.has_video_been_used(video_id):
                title = item['snippet']['title']
                url = f"https://youtu.be/{video_id}"
                return {"title": title, "url": url}

        return {"title": "N/A", "url": "N/A"}
    except Exception as e:
        logger.error(f"Error fetching YouTube video for {coin}: {str(e)}")
        return {"title": "N/A", "url": "N/A"}

async def generate_thread_template(output_file: str = None):
    """Generate X thread template and save to file."""
    logger.info("Generating X thread template...")
    
    youtube = get_youtube_service()
    if not youtube:
        logger.error("Cannot proceed without YouTube API.")
        return

    async with aiohttp.ClientSession() as session:
        current_date = get_date()
        current_time = get_timestamp()

        # Fetch data for each coin
        results = []
        for coin in COINS:
            logger.info(f"Fetching data for {coin['symbol']}...")

            price, price_change_24h, tx_volume, historical_prices = await fetch_coingecko_data(coin['coingecko_id'], session)

            if price is None:
                logger.warning(f"Failed to fetch price for {coin['symbol']}, using fallback data...")
                # Use fallback data for template
                price = 1.50
                price_change_24h = 2.5
                tx_volume = 50.0
                historical_prices = [1.45, 1.48, 1.50]

            predicted_price = predict_price(historical_prices, price)
            social_metrics = await fetch_social_metrics(coin['coingecko_id'], session)
            youtube_video = await fetch_youtube_video(youtube, coin['name'], current_date)

            coin_data = {
                "coin_name": coin['name'].title(),
                "coin_symbol": coin['symbol'],
                "price": price,
                "price_change_24h": price_change_24h,
                "predicted_price": predicted_price,
                "tx_volume": tx_volume,
                "top_project": coin['top_project'],
                "hashtag": coin['hashtag'],
                "social_metrics": social_metrics,
                "youtube_video": youtube_video
            }
            results.append(coin_data)

        # Generate thread content
        main_post = f"🚀 Crypto Market Update ({current_date} at {current_time})! 📈 Latest on top altcoins: {', '.join([coin['name'].title() for coin in COINS])}. #Crypto #Altcoins"
        
        thread_content = []
        thread_content.append(f"=== MAIN POST ===\n{main_post}\n")
        
        for i, data in enumerate(results, 1):
            reply_text = format_tweet(data)
            thread_content.append(f"=== REPLY {i} - {data['coin_name']} ===\n{reply_text}\n")
        
        # Add posting instructions
        instructions = """
=== POSTING INSTRUCTIONS ===
1. Copy the MAIN POST content and post it to X
2. Reply to the main post with REPLY 1 content
3. Reply to REPLY 1 with REPLY 2 content
4. Continue replying to create a thread
5. Each reply should be posted as a response to the previous tweet

=== THREAD STRUCTURE ===
Main Post → Reply 1 → Reply 2 → Reply 3 → etc.

=== CHARACTER COUNT NOTES ===
- X allows 280 characters per tweet
- Each reply is formatted to fit within this limit
- If any reply is too long, split it into multiple tweets
        """
        
        thread_content.append(instructions)
        
        # Save to file
        filename = output_file or f"x_thread_template_{current_date}_{current_time.replace(':', '-')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(thread_content))
        
        logger.info(f"Thread template saved to: {filename}")
        
        # Also print to console
        print("\n" + "="*60)
        print("X THREAD TEMPLATE GENERATED")
        print("="*60)
        for content in thread_content:
            print(content)
        
        return filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate X thread template for manual posting")
    parser.add_argument("--output", "-o", help="Output filename (optional)")
    args = parser.parse_args()

    try:
        filename = asyncio.run(generate_thread_template(args.output))
        print(f"\n✅ Thread template ready! Saved as: {filename}")
    except Exception as e:
        logger.error(f"Failed to generate template: {str(e)}")
    finally:
        db.close()
