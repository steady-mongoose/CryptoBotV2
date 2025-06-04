import argparse
import asyncio
import logging
import aiohttp
from pycoingecko import CoinGeckoAPI
from datetime import datetime
import tweepy
import time
import requests  # For Discord webhook posting
from modules.api_clients import get_x_client, get_coinmarketcap_api_key, get_cryptocompare_api_key, get_lunarcrush_api_key
import os

# Set up logging with more detailed output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] - %(message)s'
)
logger = logging.getLogger('CryptoBot')

# Updated list of valid coin IDs for Coinbase
COIN_IDS = [
    "XRP", "HBAR", "XLM", "XDC", "SUI", "ONDO", "ALGO", "CSPR"
]

async def validate_coin_ids(coin_ids, session):
    """Validate coin IDs for Coinbase and map unsupported coins to CoinGecko IDs."""
    start_time = time.time()
    logger.debug("Starting coin ID validation")
    valid_ids = []
    coingecko_mapping = {
        "XDC": "xdce-crowd-sale",
        "ONDO": "ondo-finance",
        "CSPR": "casper-network"
    }

    for coin_id in coin_ids:
        coinbase_url = f"https://api.coinbase.com/v2/prices/{coin_id}-USD/spot"
        try:
            logger.debug(f"Validating {coin_id} on Coinbase")
            async with session.get(coinbase_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'data' in data and 'amount' in data['data']:
                        valid_ids.append(coin_id)
                        logger.info(f"Coin ID {coin_id} is valid on Coinbase.")
                    else:
                        logger.warning(f"Coin ID {coin_id} returned 200 but no price data: {data}. Checking other APIs...")
                        correct_id = await get_correct_coin_id(coin_id, session, coingecko_mapping)
                        if correct_id:
                            valid_ids.append(correct_id)
                else:
                    logger.warning(f"Coin ID {coin_id} not supported on Coinbase (status: {response.status}). Checking other APIs...")
                    correct_id = await get_correct_coin_id(coin_id, session, coingecko_mapping)
                    if correct_id:
                        valid_ids.append(correct_id)
        except Exception as e:
            logger.error(f"Error validating {coin_id} on Coinbase: {e}")
            correct_id = await get_correct_coin_id(coin_id, session, coingecko_mapping)
            if correct_id:
                valid_ids.append(correct_id)

        # Add a small delay to avoid rate limiting
        await asyncio.sleep(0.1)

    logger.debug(f"Finished coin ID validation. Time taken: {time.time() - start_time:.2f} seconds")
    logger.info(f"Validated Coin IDs: {valid_ids}")
    return valid_ids

async def get_correct_coin_id(coin_id, session, coingecko_mapping):
    """Attempt to retrieve the correct coin ID from CoinGecko or other APIs if Coinbase fails."""
    start_time = time.time()
    logger.debug(f"Starting alternative validation for {coin_id}")

    # Try CoinGecko first
    cg_client = CoinGeckoAPI()
    try:
        logger.debug(f"Validating {coin_id} on CoinGecko")
        coingecko_id = coingecko_mapping.get(coin_id, coin_id.lower())
        coin_data = cg_client.get_coin_by_id(coingecko_id)
        if coin_data:
            logger.info(f"Coin ID {coin_id} validated on CoinGecko as {coingecko_id}")
            logger.debug(f"Finished alternative validation for {coin_id}. Time taken: {time.time() - start_time:.2f} seconds")
            return coin_id
    except Exception as e:
        logger.error(f"CoinGecko validation failed for {coin_id}: {e}")

    # Check other APIs (CoinMarketCap, CryptoCompare, LunarCrush)
    coinmarketcap_key = get_coinmarketcap_api_key()
    if coinmarketcap_key:
        coinmarketcap_api_url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={coin_id}&convert=USD"
        logger.debug(f"Validating {coin_id} on CoinMarketCap")
        async with session.get(coinmarketcap_api_url, headers={'X-CMC_PRO_API_KEY': coinmarketcap_key}) as response:
            if response.status == 200:
                data = await response.json()
                if data and 'data' in data and coin_id in data['data']:
                    logger.debug(f"Finished alternative validation for {coin_id}. Time taken: {time.time() - start_time:.2f} seconds")
                    return coin_id

    cryptocompare_key = get_cryptocompare_api_key()
    if cryptocompare_key:
        cryptocompare_api_url = f"https://min-api.cryptocompare.com/data/price?fsym={coin_id}&tsyms=USD"
        logger.debug(f"Validating {coin_id} on CryptoCompare")
        async with session.get(cryptocompare_api_url) as response:
            if response.status == 200:
                logger.debug(f"Finished alternative validation for {coin_id}. Time taken: {time.time() - start_time:.2f} seconds")
                return coin_id

    lunarcrush_key = get_lunarcrush_api_key()
    if lunarcrush_key:
        lunarcrush_api_url = f"https://api.lunarcrush.com/v2?data=coins&key={lunarcrush_key}&symbol={coin_id}"
        logger.debug(f"Validating {coin_id} on LunarCrush")
        async with session.get(lunarcrush_api_url) as response:
            if response.status == 200:
                logger.debug(f"Finished alternative validation for {coin_id}. Time taken: {time.time() - start_time:.2f} seconds")
                return coin_id

    logger.error(f"Coin ID '{coin_id}' not found in any API.")
    logger.debug(f"Finished alternative validation for {coin_id}. Time taken: {time.time() - start_time:.2f} seconds")
    return None

async def fetch_data_from_apis(coin_id, session, max_retries=3, rate_limit_delay=10):
    """Fetch data from Coinbase, with fallback to CoinGecko for unsupported coins."""
    start_time = time.time()
    logger.debug(f"Starting data fetch for {coin_id}")

    # Coinbase fetch
    coinbase_api_url = f"https://api.coinbase.com/v2/prices/{coin_id}-USD/spot"
    logger.info(f"Requesting data from URL: {coinbase_api_url}")

    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempt {attempt + 1}/{max_retries} to fetch from Coinbase for {coin_id}")
            async with session.get(coinbase_api_url) as response:
                if response.status == 200:
                    coinbase_data = await response.json()
                    if 'data' in coinbase_data and 'amount' in coinbase_data['data']:
                        price = float(coinbase_data['data']['amount'])
                        logger.info(f"Successfully fetched price for {coin_id} from Coinbase: ${price} USD")
                        logger.debug(f"Finished Coinbase fetch for {coin_id}. Time taken: {time.time() - start_time:.2f} seconds")
                        return {'source': 'coinbase', 'price': price}
                    else:
                        logger.warning(f"Coinbase returned 200 but no price data for {coin_id}: {coinbase_data}")
                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', rate_limit_delay))
                    logger.warning(f"Rate limit hit for Coinbase on {coin_id}. Retrying after {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logger.error(f"Coinbase API error for {coin_id}: {response.status}. Response: {await response.text()}")
        except Exception as e:
            logger.error(f"Coinbase fetch error for {coin_id}: {e}")
            break

    # Fallback to CoinGecko
    coingecko_mapping = {
        "XDC": "xdce-crowd-sale",
        "ONDO": "ondo-finance",
        "CSPR": "casper-network"
    }
    coingecko_id = coingecko_mapping.get(coin_id, coin_id.lower())
    coingecko_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
    logger.info(f"Falling back to CoinGecko for {coin_id}. Requesting data from URL: {coingecko_url}")

    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempt {attempt + 1}/{max_retries} to fetch from CoinGecko for {coin_id}")
            async with session.get(coingecko_url) as response:
                if response.status == 200:
                    coingecko_data = await response.json()
                    if coingecko_id in coingecko_data:
                        price = coingecko_data[coingecko_id]['usd']
                        logger.info(f"Successfully fetched price for {coin_id} from CoinGecko: ${price} USD")
                        logger.debug(f"Finished CoinGecko fetch for {coin_id}. Time taken: {time.time() - start_time:.2f} seconds")
                        return {'source': 'coingecko', 'price': float(price)}
                    else:
                        logger.error(f"CoinGecko data for {coin_id} not found in response: {coingecko_data}")
                elif response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', rate_limit_delay))
                    logger.warning(f"Rate limit hit for CoinGecko on {coin_id}. Retrying after {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logger.error(f"CoinGecko API error for {coin_id}: {response.status}. Response: {await response.text()}")
        except Exception as e:
            logger.error(f"CoinGecko fetch error for {coin_id}: {e}")
            break

    logger.debug(f"Finished data fetch for {coin_id} with no data. Time taken: {time.time() - start_time:.2f} seconds")
    return None

async def main_bot_run(test_discord: bool = False):
    """Main function to run the bot."""
    start_time = time.time()
    logger.info("Starting CryptoBotV2 daily run...")
    logger.debug(f"Test Discord mode: {test_discord}")

    async with aiohttp.ClientSession() as session:
        logger.debug("Created aiohttp ClientSession")
        valid_coin_ids = await validate_coin_ids(COIN_IDS, session)
        logger.info(f"Valid Coin IDs: {valid_coin_ids}")

        results = []
        for coin_id in valid_coin_ids:
            logger.info(f"Fetching data for {coin_id}...")
            data = await fetch_data_from_apis(coin_id, session)
            if data:
                formatted_data = f"{coin_id}: ${data['price']:.3f} USD (Source: {data['source'].capitalize()})"
                results.append({'coin_id': coin_id, 'formatted_data': formatted_data})
            else:
                logger.warning(f"No data fetched for {coin_id}")
            # Add a small delay to avoid rate limiting
            logger.debug(f"Starting 200ms delay after fetching {coin_id}")
            delay_start = time.time()
            await asyncio.sleep(0.2)
            logger.debug(f"Finished 200ms delay after fetching {coin_id}. Actual delay: {time.time() - delay_start:.2f} seconds")

        if results:
            current_time = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
            main_post = f"🚀 Crypto Market Update ({current_time})! 📈 Latest on top altcoins: {', '.join(valid_coin_ids)}. #Crypto #Altcoins"
            
            try:
                if test_discord:
                    # Post to Discord
                    logger.debug("Preparing to post updates to Discord.")
                    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
                    if webhook_url:
                        logger.debug(f"Using Discord webhook URL: {webhook_url}")
                        # Post the main message
                        payload = {
                            "content": main_post,
                            "username": "CryptoBot"
                        }
                        response = requests.post(webhook_url, json=payload)
                        if 200 <= response.status_code < 300:
                            logger.info(f"Successfully posted main update to Discord. Status code: {response.status_code}")
                        else:
                            logger.error(f"Failed to post main update to Discord. Status code: {response.status_code}, Response: {response.text}")
                        
                        # Post individual coin updates
                        for data in results:
                            payload = {
                                "content": data['formatted_data'],
                                "username": "CryptoBot"
                            }
                            response = requests.post(webhook_url, json=payload)
                            if 200 <= response.status_code < 300:
                                logger.info(f"Successfully posted {data['coin_id']} update to Discord. Status code: {response.status_code}")
                            else:
                                logger.error(f"Failed to post {data['coin_id']} update to Discord. Status code: {response.status_code}, Response: {response.text}")
                            # Add a small delay to avoid rate limiting
                            await asyncio.sleep(0.5)
                    else:
                        logger.error("Discord webhook URL is not set. Cannot post to Discord.")
                else:
                    # Post to X
                    logger.debug("Initializing X client")
                    x_client = get_x_client()
                    logger.debug("Starting main tweet posting")
                    post_start = time.time()
                    main_tweet = x_client.create_tweet(text=main_post)
                    logger.info(f"Posted main tweet with ID: {main_tweet.data['id']}. Time taken: {time.time() - post_start:.2f} seconds")
                    main_tweet_id = main_tweet.data['id']

                    for data in results:
                        logger.debug(f"Starting reply tweet for {data['coin_id']}")
                        reply_start = time.time()
                        reply_tweet = x_client.create_tweet(
                            text=data['formatted_data'],
                            in_reply_to_tweet_id=main_tweet_id
                        )
                        logger.info(f"Posted reply for {data['coin_id']} with ID: {reply_tweet.data['id']}. Time taken: {time.time() - reply_start:.2f} seconds")
                        logger.debug(f"Starting 200ms delay after posting reply for {data['coin_id']}")
                        delay_start = time.time()
                        await asyncio.sleep(0.2)
                        logger.debug(f"Finished 200ms delay after posting reply for {data['coin_id']}. Actual delay: {time.time() - delay_start:.2f} seconds")
            except Exception as e:
                logger.error(f"Error posting updates: {e}")
        else:
            logger.warning("No data to post.")

    logger.debug(f"Finished entire bot run. Total time taken: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    start_time = time.time()
    logger.debug("Script execution started")
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-discord", action="store_true", help="Run in test mode for Discord")
    args = parser.parse_args()

    try:
        asyncio.run(main_bot_run(test_discord=args.test_discord))
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
    finally:
        logger.debug(f"Script execution finished. Total runtime: {time.time() - start_time:.2f} seconds")