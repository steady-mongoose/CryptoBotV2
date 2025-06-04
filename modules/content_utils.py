import logging
from pycoingecko import CoinGeckoAPI

logger = logging.getLogger('CryptoBot')

def get_coin_mapping(cg_client):
    """
    Get the coin mapping dictionary and update XDC Network ID if needed.
    Returns the coin mapping and updated coin IDs.
    """
    # Updated coin mapping with Coinbase-compatible IDs
    coin_mapping = {
        "Ripple": "XRP",
        "Hedera Hashgraph": "HBAR",
        "Stellar": "XLM",
        "XDC Network": "XDC",
        "Sui": "SUI",
        "Ondo": "ONDO",
        "Algorand": "ALGO",
        "Casper": "CSPR"
    }

    coin_ids = list(coin_mapping.values())
    try:
        all_coins = cg_client.get_coins_list()
        # Validate XDC Network ID against CoinGecko
        xdc_coin = next((coin for coin in all_coins if coin['symbol'].lower() == 'xdc' or coin['name'].lower() == 'xdc network'), None)
        if xdc_coin:
            logger.debug(f"Found XDC Network in CoinGecko coin list: {xdc_coin}")
            if xdc_coin['id'] != "XDC":
                logger.warning(f"XDC Network ID has changed to {xdc_coin['id']}, updating coin_mapping")
                coin_mapping["XDC Network"] = xdc_coin['id']  # Will set to "xdce-crowd-sale"
                coin_ids[coin_ids.index("XDC")] = xdc_coin['id']
        else:
            logger.error("XDC Network not found in CoinGecko coin list, excluding permanently")
            coin_ids.remove("XDC")
    except Exception as e:
        logger.error(f"Error fetching CoinGecko coin list: {e}")

    return coin_mapping, coin_ids