import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger('CryptoBot')

class Database:
    def __init__(self, db_path: str):
        """Initialize the database connection and create necessary tables."""
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()
        logger.info(f"Database initialized at {self.db_path}")

    def create_tables(self):
        """Create necessary tables if they don't exist and migrate existing tables."""
        # Create used_videos table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS used_videos (
                video_id TEXT PRIMARY KEY,
                coin_name TEXT NOT NULL
            )
        ''')

        # Check if date_used column exists, and add it if it doesn't
        self.cursor.execute("PRAGMA table_info(used_videos)")
        columns = [col[1] for col in self.cursor.fetchall()]
        if 'date_used' not in columns:
            logger.info("Adding date_used column to used_videos table.")
            self.cursor.execute('ALTER TABLE used_videos ADD COLUMN date_used TEXT')
            self.conn.commit()

        logger.debug("Database tables created successfully.")

    def has_video_been_used(self, video_id: str) -> bool:
        """Check if a YouTube video has been used before."""
        self.cursor.execute("SELECT 1 FROM used_videos WHERE video_id = ?", (video_id,))
        return self.cursor.fetchone() is not None

    def add_used_video(self, coin_name: str, video_id: str, date_used: str):
        """Add a used YouTube video to the database."""
        try:
            self.cursor.execute(
                "INSERT INTO used_videos (video_id, coin_name, date_used) VALUES (?, ?, ?)",
                (video_id, coin_name, date_used)
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error adding used video {video_id} for {coin_name} on {date_used}: {e}")
            raise

    def backup(self):
        """Backup the database to a timestamped file."""
        backup_path = f"{self.db_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        with sqlite3.connect(backup_path) as backup_conn:
            self.conn.backup(backup_conn)
        logger.info(f"Database backed up to {backup_path}")

    def close(self):
        """Close the database connection."""
        self.conn.close()
        logger.info("Database connection closed.")