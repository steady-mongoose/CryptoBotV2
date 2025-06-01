
import argparse
import asyncio
import logging
import aiohttp
import sqlite3
import aiosqlite
from pycoingecko import CoinGeckoAPI
from datetime import datetime
import numpy as np
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

# Set up logging FIRST, before any other imports that might use it
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CryptoBot')

# Now import modules that might use the logger
from modules.coin_data import (
    symbol_map, fetch_coin_prices, fetch_volume, fetch_top_project
)
from modules.social_media import (
    fetch_social_metrics, fetch_youtube_video, fetch_news
)
from modules.utils import get_date
from modules.posting_utils import post_to_discord, post_to_x
from modules.api_clients import get_x_api_key

# Database configuration
DB_PATH = "data/crypto_bot.db"

# List of coins to track
COIN_IDS = [
    "ripple", "hedera-hashgraph", "stellar", "xdce-crowd-sale",
    "sui", "ondo-finance", "algorand", "casper-network"
]

class DatabaseManager:
    """Optimized database manager for SQLite operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger('CryptoBot.DatabaseManager')
        self._setup_database()

    def _setup_database(self):
        """Initialize database with optimized settings and indexes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA cache_size=16000")  # 64MB cache
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA synchronous=NORMAL")

            # Create tables if they don't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    volume REAL,
                    change_24h REAL,
                    predicted_price REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (coin_id) REFERENCES coins (coin_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS social_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin_id TEXT NOT NULL,
                    mentions INTEGER DEFAULT 0,
                    sentiment TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (coin_id) REFERENCES coins (coin_id)
                )
            """)

            # Create optimized indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_coin_id ON coins (coin_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_coin_timestamp ON price_history (coin_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_coin_timestamp ON social_metrics (coin_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_timestamp ON price_history (timestamp)")

            conn.commit()
            self.logger.info("Database initialized with optimized settings")

        except Exception as e:
            self.logger.error(f"Error setting up database: {e}")
            conn.rollback()
        finally:
            conn.close()

    @asynccontextmanager
    async def get_connection(self):
        """Get optimized async database connection."""
        async with aiosqlite.connect(self.db_path) as db:
            # Set optimizations for this connection
            await db.execute("PRAGMA cache_size=16000")
            await db.execute("PRAGMA temp_store=MEMORY")
            yield db

    async def insert_coins_batch(self, coins_data: List[Dict]):
        """Batch insert coins with conflict resolution."""
        try:
            async with self.get_connection() as db:
                await db.executemany(
                    "INSERT OR IGNORE INTO coins (coin_id, name) VALUES (?, ?)",
                    [(coin['coin_id'], coin['name']) for coin in coins_data]
                )
                await db.commit()
        except Exception as e:
            self.logger.error(f"Error inserting coins batch: {e}")

    async def insert_price_data_batch(self, price_data: List[Dict]):
        """Batch insert price data for better performance."""
        try:
            async with self.get_connection() as db:
                await db.executemany(
                    """INSERT INTO price_history 
                       (coin_id, price, volume, change_24h, predicted_price) 
                       VALUES (?, ?, ?, ?, ?)""",
                    [(data['coin_id'], data['price'], data['volume'], 
                      data['change_24h'], data['predicted_price']) for data in price_data]
                )
                await db.commit()
        except Exception as e:
            self.logger.error(f"Error inserting price data batch: {e}")

    async def insert_social_data_batch(self, social_data: List[Dict]):
        """Batch insert social metrics."""
        try:
            async with self.get_connection() as db:
                await db.executemany(
                    "INSERT INTO social_metrics (coin_id, mentions, sentiment) VALUES (?, ?, ?)",
                    [(data['coin_id'], data['mentions'], data['sentiment']) for data in social_data]
                )
                await db.commit()
        except Exception as e:
            self.logger.error(f"Error inserting social data batch: {e}")

    async def get_recent_prices(self, coin_id: str, limit: int = 100) -> List[Dict]:
        """Get recent price data with optimized query."""
        try:
            async with self.get_connection() as db:
                async with db.execute(
                    """SELECT price, volume, change_24h, predicted_price, timestamp 
                       FROM price_history 
                       WHERE coin_id = ? 
                       ORDER BY timestamp DESC 
                       LIMIT ?""",
                    (coin_id, limit)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        {
                            'price': row[0], 'volume': row[1], 'change_24h': row[2],
                            'predicted_price': row[3], 'timestamp': row[4]
                        }
                        for row in rows
                    ]
        except Exception as e:
            self.logger.error(f"Error getting recent prices for {coin_id}: {e}")
            return []

    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to maintain performance."""
        try:
            async with self.get_connection() as db:
                cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
                await db.execute(
                    "DELETE FROM price_history WHERE timestamp < ?",
                    (cutoff_date,)
                )
                await db.execute(
                    "DELETE FROM social_metrics WHERE timestamp < ?",
                    (cutoff_date,)
                )
                await db.commit()

                # Optimize database after cleanup
                await db.execute("VACUUM")
                await db.execute("ANALYZE")
                self.logger.info(f"Cleaned up data older than {days_to_keep} days")
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")

# Initialize database manager
db_manager = DatabaseManager(DB_PATH)

async def predict_price_with_history(coin_id: str, current_price: float) -> float:
    """Enhanced price prediction using historical data from database."""
    try:
        if not isinstance(current_price, (int, float)) or current_price < 0:
            logger.error("Invalid current_price provided")
            return 0.0

        # Get historical prices from database
        recent_prices = await db_manager.get_recent_prices(coin_id, limit=10)

        if len(recent_prices) > 2:
            # Use actual historical data
            prices = [float(p['price']) for p in recent_prices[::-1]]  # Reverse for chronological order
            prices.append(current_price)
        else:
            # Fallback to mock data
            prices = [current_price * (1 + i * 0.01) for i in range(-5, 0)]
            prices.append(current_price)

        # Prepare data for linear regression
        x = np.array(range(len(prices)))
        y = np.array(prices)

        # Fit a linear regression model
        coefficients = np.polyfit(x, y, 1)
        slope, intercept = coefficients

        # Predict price for the next day
        predicted_price = slope * len(prices) + intercept
        return round(predicted_price, 2)
    except Exception as e:
        logger.error(f"Error in predict_price_with_history: {e}")
        return 0.0

async def fetch_coin_data(coin_id: str, session: aiohttp.ClientSession, cg_client: CoinGeckoAPI) -> Optional[Dict]:
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

        # Predict price using enhanced historical data
        predicted_price = await predict_price_with_history(coin_id, price)

        # Fetch volume
        volume = await fetch_volume(coin_id, session)

        # Fetch top project
        top_project = await fetch_top_project(coin_id, session)

        # Fetch social metrics
        x_api_key = get_x_api_key()
        if not x_api_key:
            logger.warning("X API key not found in environment variables")
            social_metrics = {"mentions": 0, "sentiment": "N/A"}
        else:
            social_metrics = await fetch_social_metrics(coin_id, session, api_key=x_api_key)

        # Fetch YouTube video
        video = await fetch_youtube_video(coin_id, session)

        return {
            "coin_id": coin_id,
            "symbol": symbol_map.get(coin_id, coin_id.split('-')[0].upper()),
            "name": coin_id.replace('-', ' ').title(),
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

async def store_data_to_database(results: List[Dict]):
    """Store fetched data to database using batch operations."""
    try:
        # Prepare data for batch operations
        coins_data = []
        price_data = []
        social_data = []

        for data in results:
            if data is None:
                continue

            coins_data.append({
                'coin_id': data['coin_id'],
                'name': data['name']
            })

            price_data.append({
                'coin_id': data['coin_id'],
                'price': data['price'],
                'volume': data['volume'],
                'change_24h': data['change_24h'],
                'predicted_price': data['predicted_price']
            })

            social_data.append({
                'coin_id': data['coin_id'],
                'mentions': data['social_metrics']['mentions'],
                'sentiment': data['social_metrics']['sentiment']
            })

        # Batch insert all data
        await db_manager.insert_coins_batch(coins_data)
        await db_manager.insert_price_data_batch(price_data)
        await db_manager.insert_social_data_batch(social_data)

        logger.info(f"Successfully stored data for {len(results)} coins")

    except Exception as e:
        logger.error(f"Error storing data to database: {e}")

async def main(test_discord: bool = False):
    """Main function to fetch data and post updates."""
    print("Starting CryptoBotV2...")
    try:
        cg_client = CoinGeckoAPI()
        async with aiohttp.ClientSession() as session:
            print("Fetching coin data...")
            tasks = [fetch_coin_data(coin_id, session, cg_client) for coin_id in COIN_IDS]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out None results and exceptions
            valid_results = [r for r in results if r is not None and not isinstance(r, Exception)]
            print(f"Fetched data for {len(valid_results)} coins.")

            # Store data to database
            if valid_results:
                print("Storing data to database...")
                await store_data_to_database(valid_results)

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
            for idx, data in enumerate(valid_results):
                formatted_data = format_coin_data(data)
                if test_discord:
                    print(f"Posting {data['coin_id']} to Discord...")
                    await post_to_discord(formatted_data, [news_items[idx % len(news_items)]] if news_items else [])
                else:
                    print(f"Posting {data['coin_id']} to X...")
                    await post_to_x(formatted_data, [news_items[idx % len(news_items)]] if news_items else [])

            # Clean up old data periodically
            print("Cleaning up old data...")
            await db_manager.cleanup_old_data(days_to_keep=30)

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
