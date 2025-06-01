import sqlite3

conn = sqlite3.connect("C:/CryptoBotV2/data/crypto_bot.db")
cursor = conn.cursor()

# Create missing tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS coin_data_cache (
    coin_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    last_updated REAL NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS news_cache (
    query TEXT PRIMARY KEY,
    result TEXT NOT NULL,
    date TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS price_averages_cache (
    coin_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    last_updated REAL NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS project_sources_cache (
    coin_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    last_updated REAL NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS projects_cache (
    coin_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    last_updated REAL NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS thread_history (
    timestamp REAL PRIMARY KEY,
    post_hashes TEXT,
    influencers TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS youtube_cache (
    query TEXT PRIMARY KEY,
    result TEXT NOT NULL,
    last_updated REAL NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS youtube_summary_cache (
    query TEXT PRIMARY KEY,
    result TEXT NOT NULL,
    last_updated REAL NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY,
    coin TEXT,
    price REAL
)
""")

# Insert sample data
cursor.execute("""
INSERT OR REPLACE INTO projects_cache (coin_id, data, last_updated)
VALUES ('ripple', '[["Sologenic", "Tokenizes assets like stocks on XRPL", "https://sologenic.org"], ["XRPL Labs", "Building Xumm wallet for XRPL", "https://xrpl-labs.com"]]', 1747006214.83643)
""")

conn.commit()
conn.close()
print("Schema and sample data applied.")