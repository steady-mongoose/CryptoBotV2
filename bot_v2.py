import argparse
import asyncio
import logging
import os
from datetime import datetime
import aiohttp
import numpy as np
from sklearn.linear_model import LinearRegression
from modules.api_clients import get_x_client, get_coingecko_client
from modules.utils import get_timestamp, get_date, format_tweet
from modules.social_media import fetch_social_metrics
from modules.database import Database

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - [%(funcName)s] - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CryptoBot')

# Constants
COINS = {
    "ripple": "XRP",
    "hedera-hashgraph": "HBAR",
    "stellar": "XLM",
    "xdce-crowd-sale": "XDC",
    "sui": "SUI",
    "ondo-finance": "ONDO",
    "algorand": "ALGO",
    "casper-network": "CSPR"
}

async def validate_coin_ids(session: aiohttp.ClientSession) -> dict:
    """Validate coin IDs across Coinbase and fallback to CoinGecko if necessary."""
    logger.debug("Starting coin ID validation")
    start_time = datetime.now()
    validated_coins = {}

    for coingecko_id, coin_symbol in COINS.items():
        try:
            async with session.get(f"https://api.coinbase.com/v2/prices/{coin_symbol}-USD/spot") as response:
                if response.status == 200:
                    logger.info(f"Coin ID {coin_symbol} is valid on Coinbase.")
                    validated_coins[coingecko_id] = coin_symbol
                else:
                    logger.warning(f"Coin ID {coin_symbol} not supported on Coinbase (status: {response.status}). Checking other APIs...")
                    validated_coins[coingecko_id] = await get_correct_coin_id(coingecko_id, coin_symbol, session)
        except Exception as e:
            logger.error(f"Error validating {coin_symbol}: {e}")

    logger.debug(f"Finished coin ID validation. Time taken: {(datetime.now() - start_time).total_seconds():.2f} seconds")
    logger.info(f"Validated Coin IDs: {list(validated_coins.values())}")
    return validated_coins

async def get_correct_coin_id(coingecko_id: str, coin_symbol: str, session: aiohttp.ClientSession) -> str:
    """Fallback validation for coin IDs using CoinGecko."""
    logger.debug(f"Starting alternative validation for {coin_symbol}")
    start_time = datetime.now()

    coingecko = get_coingecko_client()
    try:
        coingecko_data = coingecko.get_coin_by_id(coingecko_id)
        logger.info(f"Coin ID {coin_symbol} validated on CoinGecko as {coingecko_id}")
        logger.debug(f"Finished alternative validation for {coin_symbol}. Time taken: {(datetime.now() - start_time).total_seconds():.2f} seconds")
        return coin_symbol
    except Exception as e:
        logger.error(f"Error validating {coin_symbol} on CoinGecko: {e}")
        raise

async def fetch_data_from_apis(coingecko_id: str, coin_symbol: str, session: aiohttp.ClientSession) -> dict:
    """Fetch price, transaction volume, and historical data for a coin."""
    logger.debug(f"Starting data fetch for {coin_symbol}")
    start_time = datetime.now()

    price = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            url = f"https://api.coinbase.com/v2/prices/{coin_symbol}-USD/spot"
            logger.info(f"Requesting data from URL: {url}")
            logger.debug(f"Attempt {attempt + 1}/{max_retries} to fetch from Coinbase for {coin_symbol}")
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['data']['amount'])
                    logger.info(f"Successfully fetched price for {coin_symbol} from Coinbase: ${price} USD")
                    break
                else:
                    logger.warning(f"Failed to fetch price for {coin_symbol} from Coinbase (status: {response.status})")
        except Exception as e:
            logger.error(f"Error fetching price for {coin_symbol} from Coinbase: {e}")
        await asyncio.sleep(1)

    if price is None:
        logger.warning(f"Could not fetch price for {coin_symbol} from Coinbase after {max_retries} attempts. Falling back to CoinGecko.")
        coingecko = get_coingecko_client()
        try:
            coingecko_data = coingecko.get_price(ids=coingecko_id, vs_currencies='usd')
            price = coingecko_data[coingecko_id]['usd']
            logger.info(f"Successfully fetched price for {coin_symbol} from CoinGecko: ${price} USD")
        except Exception as e:
            logger.error(f"Error fetching price for {coin_symbol} from CoinGecko: {e}")
            price = 0.0

    logger.debug(f"Finished Coinbase fetch for {coin_symbol}. Time taken: {(datetime.now() - start_time).total_seconds():.2f} seconds")

    # Fetch transaction volume and historical data from CoinGecko
    coingecko = get_coingecko_client()
    try:
        market_data = coingecko.get_coin_market_chart_by_id(id=coingecko_id, vs_currency='usd', days='1')
        tx_volume = sum([v[1] for v in market_data['total_volumes']]) / 1_000_000  # Convert to millions
        historical_prices = [p[1] for p in market_data['prices']][-30:]  # Last 30 price points
    except Exception as e:
        logger.error(f"Error fetching market data for {coin_symbol} from CoinGecko: {e}")
        tx_volume = 0.0
        historical_prices = []

    # Fetch price change
    try:
        price_change_24h = coingecko.get_price(ids=coingecko_id, vs_currencies='usd', include_24hr_change=True)[coingecko_id]['usd_24h_change']
    except Exception as e:
        logger.error(f"Error fetching 24h price change for {coin_symbol}: {e}")
        price_change_24h = 0.0

    # Predict price using linear regression
    predicted_price = price
    if historical_prices:
        try:
            X = np.array(range(len(historical_prices))).reshape(-1, 1)
            y = np.array(historical_prices)
            model = LinearRegression()
            model.fit(X, y)
            predicted_price = model.predict([[len(historical_prices)]])[0]
        except Exception as e:
            logger.error(f"Error predicting price for {coin_symbol}: {e}")

    return {
        "price": price,
        "price_change_24h": price_change_24h,
        "tx_volume": tx_volume,
        "predicted_price": predicted_price
    }

async def fetch_youtube_video(coin_name: str, db: Database, current_date: str) -> dict:
    """Fetch a YouTube video for a coin, ensuring it hasn't been used before."""
    from modules.api_clients import get_youtube_api_key
    youtube_api_key = get_youtube_api_key()
    if not youtube_api_key:
        logger.warning("YouTube API key not provided. Skipping YouTube video fetch.")
        return {"title": "N/A", "url": "N/A"}
    # Placeholder; YouTube API integration can be added here if the key is available
    return {"title": "N/A", "url": "N/A"}

async def main_bot_run(test_discord: bool = False):
    """Main function to run the CryptoBotV2 daily update."""
    logger.info("Starting CryptoBotV2 daily run...")
    logger.debug(f"Test Discord mode: {test_discord}")

    async with aiohttp.ClientSession() as session:
        logger.debug("Created aiohttp ClientSession")

        # Validate coin IDs
        validated_coins = await validate_coin_ids(session)
        logger.info(f"Valid Coin IDs: {list(validated_coins.values())}")

        current_date = get_date()
        current_time = get_timestamp()

        # Initialize database
        db = Database("crypto_bot.db")

        # Fetch data for each coin
        results = []
        top_projects = {
            "XRP": "Binance",
            "HBAR": "Binance CEX",
            "XLM": "Binance CEX",
            "XDC": "Gate",
            "SUI": "Binance",
            "ONDO": "Upbit",
            "ALGO": "Binance",
            "CSPR": "Gate"
        }

        for coingecko_id, coin_symbol in validated_coins.items():
            logger.info(f"Fetching data for {coin_symbol}...")

            # Fetch price, transaction volume, and predicted price
            data = await fetch_data_from_apis(coingecko_id, coin_symbol, session)

            # Fetch social metrics with error handling
            try:
                social_metrics = await fetch_social_metrics(coingecko_id, session)
            except Exception as e:
                logger.error(f"Failed to fetch social metrics for {coin_symbol}: {e}. Using default values.")
                social_metrics = {"mentions": 0, "sentiment": "N/A"}

            # Fetch YouTube video
            youtube_video = await fetch_youtube_video(coingecko_id, db, current_date)

            # Prepare coin data
            coin_data = {
                "coin_name": coingecko_id.replace("-", " ").title(),
                "coin_symbol": coin_symbol,
                "price": data["price"],
                "price_change_24h": data["price_change_24h"],
                "tx_volume": data["tx_volume"],
                "predicted_price": data["predicted_price"],
                "top_project": top_projects.get(coin_symbol, "Unknown"),
                "hashtag": f"#{coin_symbol}",
                "social_metrics": social_metrics,
                "youtube_video": youtube_video
            }
            results.append(coin_data)

        # Prepare main post
        main_post = {
            "text": f"🚀 Crypto Market Update ({current_date} at {current_time})! 📈 Latest on top altcoins: {', '.join([coin.replace('-', ' ').title() for coin in validated_coins.keys()])}. #Crypto #Altcoins"
        }

        # Post updates
        if test_discord:
            # Post to Discord
            webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
            if not webhook_url:
                logger.error("DISCORD_WEBHOOK_URL not set. Cannot post to Discord.")
                return

            async with aiohttp.ClientSession() as discord_session:
                # Post main update
                async with discord_session.post(webhook_url, json={"content": main_post["text"]}) as response:
                    if response.status == 204:
                        logger.info("Successfully posted main update to Discord. Status code: 204")
                    else:
                        logger.error(f"Failed to post main update to Discord. Status code: {response.status}")

                # Post coin updates
                for data in results:
                    reply_text = format_tweet(data)
                    async with discord_session.post(webhook_url, json={"content": reply_text}) as response:
                        if response.status == 204:
                            logger.info(f"Successfully posted {data['coin_name']} update to Discord. Status code: 204")
                        else:
                            logger.error(f"Failed to post {data['coin_name']} update to Discord. Status code: {response.status}")
                    await asyncio.sleep(0.5)
        else:
            # Post to X
            logger.debug("Initializing X client")
            x_client = get_x_client()
            logger.debug("Starting main tweet posting")
            main_tweet = x_client.create_tweet(text=main_post['text'])
            logger.info(f"Posted main tweet with ID: {main_tweet.data['id']}.")

            for data in results:
                reply_text = format_tweet(data)
                logger.debug(f"Starting reply tweet for {data['coin_name']}")
                reply_tweet = x_client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=main_tweet.data['id']
                )
                logger.info(f"Posted reply for {data['coin_name']} with ID: {reply_tweet.data['id']}.")
                await asyncio.sleep(0.5)

        # Backup database
        db.backup()
        logger.info("Database backup completed.")

        db.close()

if __name__ == "__main__":
    start_time = datetime.now()
    logger.debug("Script execution started")

    parser = argparse.ArgumentParser(description="CryptoBotV2 - Post daily crypto updates to X or Discord")
    parser.add_argument("--test-discord", action="store_true", help="Test mode: post to Discord instead of X")
    args = parser.parse_args()

    try:
        asyncio.run(main_bot_run(test_discord=args.test_discord))
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        raise
    finally:
        logger.debug(f"Script execution finished. Total runtime: {(datetime.now() - start_time).total_seconds():.2f} seconds")