import sqlite3

conn = sqlite3.connect("C:/CryptoBotV2/data/crypto_bot.db")
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cursor.fetchall())

# Check projects_cache
cursor.execute("SELECT * FROM projects_cache WHERE coin_id = 'ripple'")
print("Projects_cache data:", cursor.fetchall())

# Check used_videos
cursor.execute("SELECT * FROM used_videos")
print("Used_videos data:", cursor.fetchall())

# Check coins
cursor.execute("SELECT * FROM coins")
print("Coins data:", cursor.fetchall())

conn.close()