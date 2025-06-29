
import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger('CryptoBot')

class Database:
    """Database handler for the crypto bot."""

    def __init__(self, db_file: str):
        self.db_file = db_file
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                # Create used_videos table with proper indexes
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS used_videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        coin TEXT NOT NULL,
                        video_id TEXT NOT NULL UNIQUE,
                        date_used TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create index for video_id lookups
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_video_id ON used_videos(video_id)
                ''')

                # Create workflow_history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS workflow_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        workflow_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        data TEXT
                    )
                ''')

                # Create index for workflow lookups
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_workflow_type ON workflow_history(workflow_type, timestamp)
                ''')

                # Add X posting history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS x_post_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tweet_id TEXT UNIQUE,
                        content_preview TEXT,
                        post_type TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT TRUE
                    )
                ''')

                # Additional tables for comprehensive functionality
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS coins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        coingecko_id TEXT NOT NULL
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS coin_data_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        coin_id TEXT NOT NULL,
                        price REAL,
                        price_change_24h REAL,
                        volume REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS news_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        coin TEXT NOT NULL,
                        title TEXT,
                        url TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS price_averages_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        coin TEXT NOT NULL,
                        average_price REAL,
                        period TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS project_sources_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        coin TEXT NOT NULL,
                        source_data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS projects_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        coin TEXT NOT NULL,
                        project_data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS thread_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        thread_id TEXT,
                        post_count INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS youtube_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        coin TEXT NOT NULL,
                        video_data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS youtube_summary_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_id TEXT NOT NULL,
                        summary TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS prices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        coin TEXT NOT NULL,
                        price REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS social_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        coin TEXT NOT NULL,
                        mentions INTEGER,
                        sentiment TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                conn.commit()

                # Verify tables were created
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                logger.info(f"Database initialized successfully with tables: {', '.join(tables)}")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def has_video_been_used(self, video_id: str) -> bool:
        """Check if a video has been used before."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM used_videos WHERE video_id = ?",
                    (video_id,)
                )
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"Error checking video usage: {e}")
            return False

    def add_used_video(self, coin: str, video_id: str, date_used: str):
        """Add a video to the used videos list."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO used_videos (coin, video_id, date_used) VALUES (?, ?, ?)
                ''', (coin, video_id, date_used))
                conn.commit()
                logger.info(f"Added used video: {video_id} for {coin}")
        except Exception as e:
            logger.error(f"Error adding used video: {e}")

    def log_workflow(self, workflow_type: str, status: str, data: str = None):
        """Log workflow execution."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO workflow_history (workflow_type, status, data) VALUES (?, ?, ?)",
                    (workflow_type, status, data)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging workflow: {e}")

    def close(self):
        """Close database connections."""
        # SQLite connections are automatically closed when using context managers
        pass
