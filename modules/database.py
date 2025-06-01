import sqlite3
import logging

logger = logging.getLogger('CryptoBot')

class Database:
    def __init__(self, db_path: str):
        """Initialize the database connection and create necessary tables."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        logger.info(f"Database initialized at {db_path}")

    def create_tables(self):
        """Create the necessary tables if they don't exist."""
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS used_videos (
            coin_name TEXT,
            video_id TEXT,
            date TEXT,
            PRIMARY KEY (coin_name, video_id, date)
        )''')
        self.conn.commit()

    def drop_tables(self):
        """Drop all tables to reset the schema (for testing)."""
        self.cursor.execute("DROP TABLE IF EXISTS used_videos")
        self.conn.commit()
        logger.info("Dropped existing tables to reset schema")
        self.create_tables()

    def get_used_videos(self, coin_name: str, date: str) -> set:
        """Retrieve all video IDs used for a coin on a specific date."""
        self.cursor.execute(
            "SELECT video_id FROM used_videos WHERE coin_name = ? AND date = ?",
            (coin_name, date)
        )
        return {row[0] for row in self.cursor.fetchall()}

    def add_used_video(self, coin_name: str, video_id: str, date: str):
        """Add a used video ID for a coin on a specific date."""
        self.cursor.execute(
            "INSERT INTO used_videos (coin_name, video_id, date) VALUES (?, ?, ?)",
            (coin_name, video_id, date)
        )
        self.conn.commit()
        logger.info(f"Added used video {video_id} for {coin_name} on {date}")

    def close(self):
        """Close the database connection."""
        self.conn.close()
        logger.info("Database connection closed")