
import logging
import tweepy
from typing import Optional

logger = logging.getLogger('CryptoBot')

class XAPIBypassHandler:
    """
    Handles X API rate limit bypass by separating posting from search functionality.
    Preserves posting capability while avoiding 429 errors from search operations.
    """
    
    def __init__(self):
        self.posting_client = None
        self.search_disabled = True  # Always disable search to avoid 429 errors
        
    def get_posting_client(self):
        """Get X client configured for posting only."""
        if not self.posting_client:
            from modules.api_clients import get_x_client
            self.posting_client = get_x_client(posting_only=True)
        return self.posting_client
    
    def can_search(self) -> bool:
        """Always return False to bypass search and avoid 429 errors."""
        return False
    
    def handle_rate_limit_error(self, error: tweepy.TooManyRequests, operation: str) -> bool:
        """
        Handle rate limit errors by disabling search operations but preserving posting.
        
        Args:
            error: The rate limit error
            operation: The operation that caused the error ('search' or 'post')
            
        Returns:
            bool: True if operation can be retried, False if should be skipped
        """
        if operation == 'search':
            logger.warning(f"X API search rate limited: {error} - Using alternative social metrics")
            self.search_disabled = True
            return False  # Don't retry search, use alternatives
        elif operation == 'post':
            logger.warning(f"X API posting rate limited: {error} - Will retry later")
            return True  # Retry posting after delay
        else:
            logger.warning(f"X API rate limited for {operation}: {error}")
            return False
    
    def is_search_available(self) -> bool:
        """Check if search functionality should be used (always False to avoid 429)."""
        return False
    
    def log_bypass_status(self):
        """Log the current bypass status."""
        logger.info("X API Bypass Status:")
        logger.info(f"  - Search operations: DISABLED (bypassed to avoid 429 errors)")
        logger.info(f"  - Posting operations: ENABLED")
        logger.info(f"  - Social metrics: Using alternative APIs")

# Global bypass handler instance
x_bypass_handler = XAPIBypassHandler()
