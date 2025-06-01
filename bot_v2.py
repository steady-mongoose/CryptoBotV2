import argparse
import asyncio
import logging
import aiohttp
from pycoingecko import CoinGeckoAPI
from datetime import datetime
import numpy as np
from typing import Dict, List
from modules.coin_data import (
    symbol_map, fetch_coin_prices, fetch_volume, fetch_top_project
)
from modules.social_media import (
    fetch_social_metrics, fetch_youtube_video, fetch_news
)
from modules.utils import get_date
from modules.posting_utils import post_to_discord, post_to_x
from modules.api_clients import get_x_api_key

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CryptoBot')

# List of coins to track
COIN_IDS = [
    "ripple", "hedera-hashgraph", "stellar", "xdce-crowd-sale",
    "sui", "ondo-finance", "algorand", "casper-network"
]

# Simple linear regression for price prediction (mock implementation)
def predict_price(current_price: float) -> float:
    """Predict next day's price using a simple linear regression model."""
    try:
        if not isinstance(current_price, (int, float)) or current_price < 0:
            logger.error("Invalid current_price provided")
            return 0.0
        # Mock historical prices (last 5 days, for demo purposes)
        historical_prices = [current_price * (1 + i * 0.01) for i in range(-5, 0)]
        historical_prices.append(current_price)

        # Prepare data for linear regression
        x = np.array(range(len(historical_prices)))
        y = np.array(historical_prices)

        # Fit a linear regression model
        coefficients = np.polyfit(x, y, 1)
        slope, intercept = coefficients

        # Predict price for the next day
        predicted_price = slope * len(historical_prices) + intercept
        return round(predicted_price, 2)
    except Exception as e:
        logger.error(f"Error in predict_price: {e}")
        return 0.0

async def fetch_coin_data(coin_id: str, session: aiohttp.ClientSession, cg_client: CoinGeckoAPI) -> Dict:
    """Fetch all data for a single coin."""
    try:
        if not coin_id or not isinstance(coin_id, str):
            logger.error("Invalid coin_id provided")
            return None

        # Fetch price and 24h change
        prices = fetch_coin_prices([coin_id], cg_client)
        if coin_id not in prices:
            logger.error(f"No price data returned for {coin_id}")
            return None
        price = prices[coin_id]["usd"]
        change_24h = prices[coin_id]["usd_24h_change"]

        # Predict price using linear regression
        predicted_price = predict_price(price)

        # Fetch volume
        volume = await fetch_volume(coin_id, session)

        # Fetch top project
        top_project = await fetch_top_project(coin_id, session)

        # Fetch social metrics
        x_api_key = get_x_api_key()
        if not x_api_key:
            logger.error("X API key not found in environment variables")
            social_metrics = {"mentions": 0, "sentiment": "N/A"}
        else:
            social_metrics = await fetch_social_metrics(coin_id, session, api_key=x_api_key)

        # Fetch YouTube video
        video = await fetch_youtube_video(coin_id, session)

        return {
            "coin_id": coin_id,
            "symbol": symbol_map.get(coin_id, coin_id.split('-')[0].upper()),
            "price": price,
            "change_24h": change_24h,
            "predicted_price": predicted_price,
            "volume": volume,
            "top_project": top_project,
            "social_metrics": social_metrics,
            "video": video
        }
    except Exception as e:
        logger.error(f"Error fetching data for {coin_id}: {e}")
        return None

def format_coin_data(data: Dict) -> str:
    """Format the coin data into a string similar to Currency Gator's X posts."""
    try:
        if not data or not isinstance(data, dict):
            logger.error("Invalid data provided to format_coin_data")
            return ""

        # Determine arrow emoji based on 24h change
        arrow = "📈" if data["change_24h"] >= 0 else "📉"

        # Format the output
        output = (
            f"{data['coin_id'].replace('-', ' ')} ({data['symbol']}): ${data['price']:.2f} ({data['change_24h']:.2f}% 24h) {arrow}\n"
            f"Predicted: ${data['predicted_price']:.2f} (Linear regression)\n"
            f"Tx Volume: {data['volume']:.2f}M\n"
            f"Top Project: {data['top_project']}\n"
            f"#{data['symbol']}\n"
            f"Social: {data['social_metrics']['mentions']} mentions, {data['social_metrics']['sentiment']}\n"
            f"Video: {data['video']['title']}... {data['video']['url']}\n"
        )
        return output
    except Exception as e:
        logger.error(f"Error formatting coin data: {e}")
        return ""

async def main(test_discord: bool = False):
    """Main function to fetch data and post updates."""
    print("Starting CryptoBotV2...")
    try:
        cg_client = CoinGeckoAPI()
        async with aiohttp.ClientSession() as session:
            print("Fetching coin data...")
            tasks = [fetch_coin_data(coin_id, session, cg_client) for coin_id in COIN_IDS]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            print(f"Fetched data for {len(results)} coins.")

            # Fetch news for all coins
            print("Fetching news data...")
            news_items = await fetch_news(COIN_IDS, session)
            print(f"Fetched {len(news_items)} news items.")

            # Format the main post
            current_time = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
            main_post = f"🚀 Crypto Market Update ({current_time})! 📈 Latest on top altcoins: Ripple, Hedera Hashgraph, Stellar, XDC Network, Sui, Ondo, Algorand, Casper. #Crypto #Altcoins\n"
            print("Posting main update...")
            if test_discord:
                print("Posting main update to Discord...")
                await post_to_discord(main_post, news_items)
            else:
                print("Posting main update to X...")
                await post_to_x(main_post, news_items)

            # Format and post individual coin updates
            print("Posting individual coin updates...")
            for idx, data in enumerate(results):
                if data is None:
                    print(f"Skipping {COIN_IDS[idx]} due to missing data.")
                    continue
                formatted_data = format_coin_data(data)
                if test_discord:
                    print(f"Posting {data['coin_id']} to Discord...")
                    await post_to_discord(formatted_data, [news_items[idx % len(news_items)]])
                else:
                    print(f"Posting {data['coin_id']} to X...")
                    await post_to_x(formatted_data, [news_items[idx % len(news_items)]])
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crypto Market Update Bot")
    parser.add_argument("--test-discord", action="store_true",
                        help="Test output to Discord instead of posting to X")
    args = parser.parse_args()

    # Run the main function
    asyncio.run(main(test_discord=args.test_discord))