import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger('CryptoBot')

class Database:
    def __init__(self, db_path: str):
        """Initialize the database and create the used_videos table if it doesn't exist."""
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        logger.info(f"Database initialized at {self.db_path}")

    def create_tables(self):
        """Create the used_videos table if it doesn't exist."""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS used_videos (
                    coin_name TEXT,
                    video_id TEXT,
                    date_used TEXT,
                    PRIMARY KEY (video_id)
                )
            ''')
            self.conn.commit()
            logger.debug("Database tables created successfully.")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def add_used_video(self, coin_name: str, video_id: str, date_used: str):
        """Add a used video ID to the database."""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO used_videos (coin_name, video_id, date_used)
                VALUES (?, ?, ?)
            ''', (coin_name, video_id, date_used))
            self.conn.commit()
            logger.debug(f"Added used video {video_id} for {coin_name} on {date_used}")
        except Exception as e:
            logger.error(f"Error adding used video {video_id} for {coin_name} on {date_used}: {e}")

    def has_video_been_used(self, video_id: str) -> bool:
        """Check if a video ID has been used."""
        try:
            self.cursor.execute('SELECT 1 FROM used_videos WHERE video_id = ?', (video_id,))
            result = self.cursor.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking if video {video_id} has been used: {e}")
            return False

    def backup(self):
        """Create a backup of the database."""
        try:
            backup_path = f"{self.db_path}.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.bak"
            with sqlite3.connect(backup_path) as backup_conn:
                self.conn.backup(backup_conn)
            logger.info(f"Database backed up to {backup_path}")
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")

    def close(self):
        """Close the database connection."""
        try:
            self.conn.close()
            logger.debug("Database connection closed.")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")