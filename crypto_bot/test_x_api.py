import tweepy
import os
from dotenv import load_dotenv

load_dotenv()

# OAuth 1.0a
consumer_key = os.getenv("X_CONSUMER_KEY")
consumer_secret = os.getenv("X_CONSUMER_SECRET")
access_token = os.getenv("X_ACCESS_TOKEN")
access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
user = api.verify_credentials()
print("OAuth 1.0a User ID:", user.id)
print("Screen Name:", user.screen_name)

# OAuth 2.0
bearer_token = os.getenv("X_BEARER_TOKEN")  # Use X_BEARER_TOKEN from .env
client = tweepy.Client(bearer_token=bearer_token)
user = client.get_me(user_auth=False)
print("OAuth 2.0 User ID:", user.data.id)
print("Username:", user.data.username)