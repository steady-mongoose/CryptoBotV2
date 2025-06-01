import sqlite3

conn = sqlite3.connect("C:/CryptoBotV2/data/crypto_bot.db")
cursor = conn.cursor()

coins = [
    ("Ripple", "ripple"),
    ("Hedera Hashgraph", "hedera"),
    ("Stellar", "stellar"),
    ("XDC Network", "xdc-network"),
    ("Sui", "sui"),
    ("Ondo", "ondo"),
    ("Algorand", "algorand")
]

for name, coin_id in coins:
    cursor.execute("INSERT OR IGNORE INTO coins (name, coin_id) VALUES (?, ?)", (name, coin_id))

conn.commit()
conn.close()
print("Coins table updated.")
