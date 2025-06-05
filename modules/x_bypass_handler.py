
import logging
import tweepy
from typing import Optional

logger = logging.getLogger('CryptoBot')

import logging

logger = logging.getLogger('CryptoBot')

class XAPIBypassHandler:
    """
    Handles X API rate limit bypass by separating posting from search functionality.
    Preserves posting capability while avoiding 429 errors from search operations.
    """
    
    def __init__(self):
        self.posting_client = None
        self.search_disabled = True  # PERMANENTLY DISABLED to prevent rate limits
        
    def get_posting_client(self):
        """Get X client configured for posting only."""
        if not self.posting_client:
            from modules.api_clients import get_x_client
            self.posting_client = get_x_client(posting_only=True)
        return self.posting_client
    
    def can_search(self) -> bool:
        """Return True if search is available, False if disabled due to errors."""
        return not self.search_disabled
    
    def force_disable_search(self):
        """Permanently disable search functionality to prevent rate limits."""
        self.search_disabled = True
        logger.info("X API search functionality permanently disabled to prevent rate limits")
    
    def handle_rate_limit_error(self, error, operation: str) -> bool:
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
            logger.warning(f"X API posting rate limited: {error} - Will retry via queue")
            return True  # Can retry posting via queue system
        
        return False

# Global instance
x_bypass_handler = XAPIBypassHandler()
            logger.warning(f"X API posting rate limited: {error} - Will retry later")
            return True  # Retry posting after delay
        else:
            logger.warning(f"X API rate limited for {operation}: {error}")
            return False
    
    def is_search_available(self) -> bool:
        """Check if search functionality should be used."""
        return not self.search_disabled
    
    def enable_search(self):
        """Manually enable search operations (DANGER: may cause rate limits)."""
        logger.warning("⚠️  ENABLING X API SEARCH - This may cause rate limits!")
        self.search_disabled = False
        logger.info("X API search operations manually ENABLED")
    
    def force_disable_search(self):
        """Force disable search operations permanently."""
        self.search_disabled = True
        logger.info("X API search operations FORCE DISABLED")
    
    def log_bypass_status(self):
        """Log the current bypass status."""
        logger.info("X API Smart Bypass Status:")
        search_status = "DISABLED (preventing rate limits)" if self.search_disabled else "ENABLED"
        logger.info(f"  - Search operations: {search_status}")
        logger.info(f"  - Posting operations: ENABLED (always preserved)")
        logger.info(f"  - Social metrics: {'Alternative APIs only' if self.search_disabled else 'X API + alternatives'}")

# Global bypass handler instance
x_bypass_handler = XAPIBypassHandler()
