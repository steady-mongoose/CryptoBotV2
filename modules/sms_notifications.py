
import requests
import logging
import os
from datetime import datetime

logger = logging.getLogger('CryptoBot')

class SMSNotifications:
    """Simple SMS notification system using TextBelt API (free tier)."""
    
    def __init__(self):
        self.api_key = os.getenv('TEXTBELT_API_KEY', 'textbelt')  # 'textbelt' is free tier
        self.phone_number = "9407688082"  # Your number
        self.enabled = True
        
    def send_sms(self, message: str) -> bool:
        """
        Send SMS notification.
        
        Args:
            message: The message to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info("SMS notifications disabled")
            return False
            
        try:
            # Use TextBelt API (free tier allows 1 text per day per phone number)
            url = "https://textbelt.com/text"
            
            payload = {
                'phone': self.phone_number,
                'message': message,
                'key': self.api_key
            }
            
            response = requests.post(url, data=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"✅ SMS sent successfully to {self.phone_number}")
                    return True
                else:
                    logger.error(f"❌ SMS failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                logger.error(f"❌ SMS API error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ SMS sending error: {e}")
            return False
    
    def send_completion_notification(self, platform: str, success: bool, details: dict) -> bool:
        """Send completion notification via SMS."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "✅ SUCCESS" if success else "❌ FAILED"
        
        message = f"CryptoBot {status}\n"
        message += f"Time: {timestamp}\n"
        message += f"Platform: {platform}\n"
        message += f"Posts: {details.get('posts_count', 0)}\n"
        
        if details.get('rate_limited'):
            message += "Note: X posts queued due to rate limits"
        
        # Truncate to SMS limit (160 chars)
        if len(message) > 160:
            message = message[:157] + "..."
            
        return self.send_sms(message)

# Global instance
sms_notifications = SMSNotifications()
