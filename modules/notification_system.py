
import aiohttp
import logging
import os
from datetime import datetime
from typing import Dict, Optional
from modules.sms_notifications import sms_notifications

logger = logging.getLogger('CryptoBot')

class NotificationSystem:
    """Comprehensive notification system for bot completion alerts."""

    def __init__(self):
        self.discord_webhook = os.getenv('NOTIFICATION_WEBHOOK_URL')
        self.signal_number = os.getenv('SIGNAL_PHONE_NUMBER')
        self.sms_number = os.getenv('SMS_PHONE_NUMBER')
        self.enabled = os.getenv('NOTIFICATIONS_ENABLED', 'true').lower() == 'true'

    async def send_completion_notification(self, 
                                         platform: str, 
                                         success: bool, 
                                         details: Dict,
                                         session: aiohttp.ClientSession):
        """
        Send completion notification across configured channels.
        
        Args:
            platform: 'discord', 'x', or 'both'
            success: True if posting succeeded
            details: Dict with run details (posts_count, errors, etc.)
            session: aiohttp session for webhook calls
        """
        if not self.enabled:
            logger.debug("Notifications disabled, skipping")
            return

        status_emoji = "✅" if success else "❌"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create notification message
        message = self._create_notification_message(platform, success, details, status_emoji, timestamp)
        
        # Send to configured channels
        if self.discord_webhook:
            await self._send_discord_notification(message, session)
        
        # Send SMS notification
        try:
            sms_sent = sms_notifications.send_completion_notification(platform, success, details)
            if sms_sent:
                logger.info("✅ SMS notification sent successfully")
            else:
                logger.warning("⚠️ SMS notification failed")
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
        
        # Future: Add Signal integration
        if self.signal_number:
            logger.info(f"Signal notification would be sent to {self.signal_number}")

    def _create_notification_message(self, platform: str, success: bool, details: Dict, status_emoji: str, timestamp: str) -> str:
        """Create formatted notification message."""
        
        # Header
        if success:
            title = f"{status_emoji} CryptoBot Run Completed Successfully"
        else:
            title = f"{status_emoji} CryptoBot Run Failed"
        
        # Platform info
        platform_text = {
            'discord': 'Discord Only',
            'x': 'X (Twitter) Only', 
            'both': 'Discord + X'
        }.get(platform, platform.title())
        
        # Details
        posts_count = details.get('posts_count', 0)
        errors = details.get('errors', [])
        queue_status = details.get('queue_status', {})
        content_differences = details.get('content_differences', [])
        
        message = f"**{title}**\n\n"
        message += f"🕒 **Time**: {timestamp}\n"
        message += f"📱 **Platform**: {platform_text}\n"
        message += f"📊 **Posts**: {posts_count}\n"
        
        if queue_status:
            message += f"🔄 **Queue**: {queue_status.get('post_queue_size', 0)} posts, {queue_status.get('thread_queue_size', 0)} threads\n"
        
        if content_differences:
            message += f"\n⚠️ **Content Differences Detected**:\n"
            for diff in content_differences[:3]:  # Limit to 3
                message += f"• {diff}\n"
        
        if errors:
            message += f"\n❌ **Errors** ({len(errors)}):\n"
            for error in errors[:3]:  # Limit to 3 errors
                message += f"• {error}\n"
        
        # Rate limit info for X
        if platform in ['x', 'both'] and details.get('rate_limited'):
            message += f"\n⏳ **Rate Limited**: Posts queued for later processing\n"
        
        return message

    async def _send_discord_notification(self, message: str, session: aiohttp.ClientSession):
        """Send notification to Discord webhook."""
        try:
            payload = {"content": message}
            async with session.post(self.discord_webhook, json=payload) as response:
                if response.status == 204:
                    logger.info("✅ Notification sent to Discord")
                else:
                    logger.error(f"Failed to send Discord notification: {response.status}")
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")

    async def send_content_difference_alert(self, 
                                          differences: list, 
                                          session: aiohttp.ClientSession):
        """Send alert when X and Discord content differs."""
        if not self.enabled or not differences:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"⚠️ **Content Difference Alert**\n\n"
        message += f"🕒 **Time**: {timestamp}\n"
        message += f"📊 **Differences Found**: {len(differences)}\n\n"
        
        for i, diff in enumerate(differences[:5], 1):  # Limit to 5
            message += f"**{i}.** {diff}\n"
        
        if len(differences) > 5:
            message += f"\n... and {len(differences) - 5} more differences"
        
        if self.discord_webhook:
            await self._send_discord_notification(message, session)

# Global instance
notification_system = NotificationSystem()
