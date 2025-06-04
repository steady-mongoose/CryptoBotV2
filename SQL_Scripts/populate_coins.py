import sqlite3

conn = sqlite3.connect("C:/CryptoBotV2/data/crypto_bot.db")
cursor = conn.cursor()

coins = [
    ("Ripple", "ripple"),
    ("Hedera Hashgraph", "hedera-hashgraph"),
    ("Stellar", "stellar"),
    ("XDC Network", "xdc"),  # Updated for XDC
    ("Sui", "sui"),
    ("Ondo", "ondo-finance"),
    ("Algorand", "algorand"),
    ("Casper", "casper")  # Updated for Casper
]

for name, coin_id in coins:
    cursor.execute("INSERT OR IGNORE INTO coins (name, coin_id) VALUES (?, ?)", (name, coin_id))

conn.commit()
conn.close()
print("Coins table updated.")