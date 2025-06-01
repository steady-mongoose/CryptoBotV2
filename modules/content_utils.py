import logging
from pycoingecko import CoinGeckoAPI

logger = logging.getLogger('CryptoBot')

def get_coin_mapping(cg_client):
    """
    Get the coin mapping dictionary and update XDC Network ID if needed.
    Returns the coin mapping and updated coin IDs.
    """
    coin_mapping = {
        "Ripple": "ripple",
        "Hedera Hashgraph": "hedera-hashgraph",
        "Stellar": "stellar",
        "XDC Network": "xdc-network",
        "Sui": "sui",
        "Algorand": "algorand",
        "Ondo": "ondo-finance",
        "Casper": "casper-network"
    }

    coin_ids = list(coin_mapping.values())
    try:
        all_coins = cg_client.get_coins_list()
        xdc_coin = next((coin for coin in all_coins if coin['symbol'].lower() == 'xdc' or coin['name'].lower() == 'xdc network'), None)
        if xdc_coin:
            logger.debug(f"Found XDC Network in CoinGecko coin list: {xdc_coin}")
            if xdc_coin['id'] != "xdc-network":
                logger.warning(f"XDC Network ID has changed to {xdc_coin['id']}, updating coin_mapping")
                coin_mapping["XDC Network"] = xdc_coin['id']
                coin_ids[coin_ids.index("xdc-network")] = xdc_coin['id']
        else:
            logger.error("XDC Network not found in CoinGecko coin list, excluding permanently")
            coin_ids.remove("xdc-network")
    except Exception as e:
        logger.error(f"Error fetching CoinGecko coin list: {e}")

    return coin_mapping, coin_ids