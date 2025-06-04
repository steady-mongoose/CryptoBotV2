import os
import logging
import requests
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] - %(message)s'
)
logger = logging.getLogger('DiscordWebhookTest')

def test_discord_webhook():
    """Test posting a message to a Discord webhook."""
    # Load the webhook URL from environment variable
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable is not set.")
        return

    # Prepare the message
    current_time = datetime.now().strftime("%Y-%m-%d at %H:%M:%S")
    message = f"🔔 Test Message: This is a test webhook post sent on {current_time}."

    # Prepare the payload for Discord (simple content message)
    payload = {
        "content": message,
        "username": "Webhook Tester"  # Optional: Customize the webhook username
    }

    try:
        # Send the POST request to the Discord webhook
        response = requests.post(webhook_url, json=payload)

        # Check the response status
        if 200 <= response.status_code < 300:
            logger.info(f"Successfully posted to Discord webhook. Status code: {response.status_code}")
        else:
            logger.error(f"Failed to post to Discord webhook. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        logger.error(f"Error posting to Discord webhook: {e}")

if __name__ == "__main__":
    logger.info("Starting Discord webhook test...")
    test_discord_webhook()
    logger.info("Discord webhook test completed.")