import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BinanceKeyChecker')

def check_binance_keys():
    """Check if Binance API keys are present in the environment variables."""
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        logger.error("Missing Binance API keys. Please check your secrets.")
        return False

    logger.info("Binance API keys are present.")
    return True

if __name__ == "__main__":
    check_binance_keys()