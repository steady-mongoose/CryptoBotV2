import sqlite3
conn = sqlite3.connect("C:/CryptoBotV2/data/crypto_bot.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM projects_cache WHERE coin_id = 'ripple'")
print("Projects_cache:", cursor.fetchall())
cursor.execute("SELECT * FROM used_videos WHERE coin_name = 'Ripple'")
print("Used_videos:", cursor.fetchall())
conn.close()