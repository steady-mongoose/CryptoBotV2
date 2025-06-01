import sqlite3
import os

# Define the database path
db_path = os.path.join("data", "crypto_bot.db")
conn = sqlite3.connect(db_path)

# Define the cursor
cursor = conn.cursor()

# Query to list all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

# Print the tables
for table in tables:
    print(table[0])

# Close the connection
conn.close()