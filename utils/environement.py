import os
from dotenv import load_dotenv


def load_environment():
    load_dotenv()
    binance_api_key = os.getenv('TESTNET_API_KEY') if os.getenv('API_MODE') == 'TESTNET' else os.getenv('PROD_API_KEY')
    binance_secret = os.getenv('TESTNET_API_SECRET') if os.getenv('API_MODE') == 'TESTNET' else os.getenv('PROD_API_SECRET')
    bybite_api_key = os.getenv('BYBIT_API_KEY')
    bybite_secret = os.getenv('BYTBIT_API_SECRET')
    return binance_api_key, binance_secret, bybite_api_key, bybite_secret

def load_env_variables():
    load_dotenv()
    binance_api_key = os.getenv('TESTNET_API_KEY') if os.getenv('API_MODE') == 'TESTNET' else os.getenv('PROD_API_KEY')
    binance_secret = os.getenv('TESTNET_API_SECRET') if os.getenv('API_MODE') == 'TESTNET' else os.getenv('PROD_API_SECRET')
    return binance_api_key, binance_secret