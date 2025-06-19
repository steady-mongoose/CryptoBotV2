import tweepy
from dotenv import load_dotenv
import os

load_dotenv("C:\\CryptoBotV2\\crypto_bot\\.env")
client = tweepy.Client(
    consumer_key=os.getenv("X_CONSUMER_KEY"),
    consumer_secret=os.getenv("X_CONSUMER_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
)
try:
    response = client.create_tweet(text="Test tweet from CryptoBotV2 (2025-06-14)")
    print(f"Posted tweet: {response.data['id']}")
except Exception as e:
    print(f"Error: {e}")