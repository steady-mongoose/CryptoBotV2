
import argparse
import asyncio
import logging
import aiohttp
import sqlite3
import aiosqlite
from pycoingecko import CoinGeckoAPI
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
import time
import schedule

# Set up logging FIRST, before any other imports that might use it
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CryptoBot')

# Now import modules that might use the logger
import tweepy
from modules.coin_data import (
    symbol_map, fetch_coin_prices, fetch_volume, fetch_top_project,
    fetch_coin_prices_multi_source, track_rate_limit, reset_rate_limit_tracking
)
from modules.social_media import (
    fetch_social_metrics, fetch_youtube_video, fetch_news
)
from modules.utils import get_date
from modules.posting_utils import post_to_discord, post_to_x
from modules.api_clients import get_x_api_key, get_x_client

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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    coins_processed INTEGER DEFAULT 0,
                    error_message TEXT
                )
            """)

            # Create optimized indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_coin_id ON coins (coin_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_coin_timestamp ON price_history (coin_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_social_coin_timestamp ON social_metrics (coin_id, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_timestamp ON price_history (timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bot_runs_timestamp ON bot_runs (run_timestamp)")

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

    async def log_bot_run(self, success: bool, coins_processed: int, error_message: str = None):
        """Log bot run statistics."""
        try:
            async with self.get_connection() as db:
                await db.execute(
                    "INSERT INTO bot_runs (success, coins_processed, error_message) VALUES (?, ?, ?)",
                    (success, coins_processed, error_message)
                )
                await db.commit()
        except Exception as e:
            self.logger.error(f"Error logging bot run: {e}")

    async def get_last_run_time(self) -> Optional[datetime]:
        """Get the timestamp of the last successful bot run."""
        try:
            async with self.get_connection() as db:
                async with db.execute(
                    "SELECT run_timestamp FROM bot_runs WHERE success = 1 ORDER BY run_timestamp DESC LIMIT 1"
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return datetime.fromisoformat(row[0])
                    return None
        except Exception as e:
            self.logger.error(f"Error getting last run time: {e}")
            return None

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
                await db.execute(
                    "DELETE FROM bot_runs WHERE run_timestamp < ?",
                    (datetime.now() - timedelta(days=days_to_keep)).isoformat(),
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

        # Fetch price and 24h change using multi-source with rate limit protection
        prices = await fetch_coin_prices_multi_source([coin_id], cg_client, session)
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
    """Format the coin data into a string optimized for X threading."""
    try:
        if not data or not isinstance(data, dict):
            logger.error("Invalid data provided to format_coin_data")
            return ""

        # Determine arrow emoji based on 24h change
        arrow = "📈" if data["change_24h"] >= 0 else "📉"

        # Format the output - optimized for X's 280 character limit
        output = (
            f"{data['name']} ({data['symbol']}): ${data['price']:.2f} ({data['change_24h']:.2f}% 24h) {arrow}\n"
            f"Predicted: ${data['predicted_price']:.2f}\n"
            f"Volume: {data['volume']:.1f}M | {data['top_project']}\n"
            f"#{data['symbol']} #Crypto"
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

async def validate_x_api():
    """Validate X API credentials before running the bot."""
    try:
        from modules.api_clients import get_x_client
        client = get_x_client()
        
        # Test basic authentication
        me = client.get_me()
        logger.info(f"X API validation successful - connected as @{me.data.username}")
        return True
        
    except tweepy.Unauthorized:
        logger.error("X API validation failed - credentials are invalid")
        return False
    except tweepy.Forbidden:
        logger.error("X API validation failed - account may be restricted or exceed free tier limits")
        return False
    except Exception as e:
        logger.error(f"X API validation failed: {e}")
        return False

async def should_run_today() -> bool:
    """Check if the bot should run today (once every 24 hours)."""
    last_run = await db_manager.get_last_run_time()
    
    if last_run is None:
        logger.info("No previous runs found - running bot")
        return True
    
    time_since_last_run = datetime.now() - last_run
    hours_since_last_run = time_since_last_run.total_seconds() / 3600
    
    if hours_since_last_run >= 24:
        logger.info(f"Last run was {hours_since_last_run:.1f} hours ago - running bot")
        return True
    else:
        hours_remaining = 24 - hours_since_last_run
        logger.info(f"Bot ran {hours_since_last_run:.1f} hours ago - next run in {hours_remaining:.1f} hours")
        return False

async def main_bot_run(test_discord: bool = False):
    """Main function to fetch data and post updates - optimized for X free tier."""
    print("Starting CryptoBotV2 daily run...")
    
    # Check if we should run today
    if not await should_run_today():
        print("⏰ Bot already ran today - skipping execution")
        return
    
    # Validate X API credentials if not testing Discord
    if not test_discord:
        print("Validating X API credentials...")
        if not await validate_x_api():
            print("❌ X API validation failed! Check your credentials in Secrets")
            await db_manager.log_bot_run(False, 0, "X API validation failed")
            return
        print("✅ X API validation successful")
    
    coins_processed = 0
    error_message = None
    
    try:
        cg_client = CoinGeckoAPI()
        async with aiohttp.ClientSession() as session:
            print("Fetching data for all 8 coins...")
            
            # Fetch data for all coins with very conservative delays
            results = []
            for i, coin_id in enumerate(COIN_IDS):
                if i > 0:
                    # Very conservative delays for free tier compliance
                    delay = 90  # 1.5 minutes between each coin
                    print(f"Waiting {delay}s before fetching {coin_id}...")
                    await asyncio.sleep(delay)
                
                try:
                    print(f"Fetching data for {coin_id}...")
                    result = await fetch_coin_data(coin_id, session, cg_client)
                    if result:
                        results.append(result)
                        coins_processed += 1
                        print(f"✅ Successfully fetched {coin_id}")
                    else:
                        print(f"❌ Failed to fetch {coin_id}")
                except Exception as e:
                    logger.error(f"Failed to fetch data for {coin_id}: {e}")
                    print(f"❌ Failed to fetch {coin_id}: {e}")

            print(f"Successfully fetched data for {len(results)} coins.")

            # Store data to database
            if results:
                print("Storing data to database...")
                await store_data_to_database(results)

            # Create thread format for X/Twitter
            current_time = datetime.now().strftime("%Y-%m-%d at %H:%M")
            main_post = f"🚀 Daily Crypto Update ({current_time})!\n📊 8 Top Altcoins Thread:\n#Crypto #Altcoins #DeFi"
            
            if test_discord:
                print("Posting to Discord...")
                await post_to_discord(main_post, [])
                for data in results:
                    formatted_data = format_coin_data(data)
                    await post_to_discord(formatted_data, [])
            else:
                print("Posting thread to X...")
                try:
                    # Post main thread starter
                    main_tweet_id = await post_to_x(main_post)
                    logger.info(f"Posted main thread tweet: {main_tweet_id}")
                    
                    # Wait before posting thread replies
                    await asyncio.sleep(180)  # 3 minute delay
                    
                    # Post each coin as a thread reply with very generous delays for free tier
                    for idx, data in enumerate(results):
                        formatted_data = format_coin_data(data)
                        try:
                            await post_to_x(formatted_data, [], main_tweet_id)
                            logger.info(f"Posted thread reply for {data['coin_id']}")
                            
                            # Very generous delays to respect X free tier (up to 10 minutes between posts)
                            if idx < len(results) - 1:  # Don't wait after the last post
                                delay = min(300 + (idx * 60), 600)  # 5-10 minute delays
                                print(f"Waiting {delay}s before next thread post...")
                                await asyncio.sleep(delay)
                                
                        except tweepy.TooManyRequests as e:
                            logger.error(f"X rate limited at coin {idx+1}/{len(results)}")
                            error_message = f"X rate limited after {idx+1} coins"
                            break
                        except Exception as e:
                            logger.error(f"Failed to post {data['coin_id']}: {e}")
                            continue
                    
                except tweepy.TooManyRequests as e:
                    logger.error("X rate limited on main tweet")
                    error_message = "X rate limited on main tweet"
                except Exception as e:
                    logger.error(f"Failed to post main tweet: {e}")
                    error_message = f"Failed to post main tweet: {e}"

            # Clean up old data
            print("Cleaning up old data...")
            await db_manager.cleanup_old_data(days_to_keep=30)
            
            # Log successful run
            await db_manager.log_bot_run(True, coins_processed, error_message)
            print(f"✅ Daily run completed successfully - processed {coins_processed} coins")

    except Exception as e:
        error_msg = f"Error in main bot run: {e}"
        logger.error(error_msg)
        await db_manager.log_bot_run(False, coins_processed, error_msg)
        print(f"❌ Daily run failed: {e}")

def run_scheduler():
    """Run the scheduler that checks every hour if bot should run."""
    # Schedule to check every hour
    schedule.every().hour.do(lambda: asyncio.create_task(main_bot_run()))
    
    print("🕐 Scheduler started - bot will run once every 24 hours")
    print("⏰ Next check in 1 hour...")
    
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Check every hour

async def main(test_discord: bool = False, run_once: bool = False):
    """Main entry point with scheduler support."""
    if run_once:
        # Run immediately for testing
        await main_bot_run(test_discord)
    else:
        # Run with scheduler
        print("Starting 24-hour scheduler...")
        # Check if we should run immediately on startup
        if await should_run_today():
            print("Running bot immediately on startup...")
            await main_bot_run(test_discord)
        
        # Start the scheduler in a separate thread
        import threading
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        # Keep the main thread alive
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
        except KeyboardInterrupt:
            print("Shutting down...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crypto Market Update Bot - Daily Edition")
    parser.add_argument("--test-discord", action="store_true",
                        help="Test output to Discord instead of posting to X")
    parser.add_argument("--run-once", action="store_true",
                        help="Run once and exit (for testing)")
    args = parser.parse_args()

    # For Cloud Run, start a simple HTTP server alongside the bot
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Daily CryptoBot is running')
            
        def log_message(self, format, *args):
            pass  # Suppress HTTP server logs
    
    # Start HTTP server in background thread
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print("Health check server started on port 8080")
    
    # Run the main function
    asyncio.run(main(test_discord=args.test_discord, run_once=args.run_once))
