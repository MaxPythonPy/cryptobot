import ccxt.async_support as ccxt  # noqa: E402


exchanges = {
    'okx': ccxt.okx(),
    'bybit': ccxt.bybit({"options": {"defaultType": "spot"}}),
    'binance': ccxt.binance(),
    'kucoin': ccxt.kucoin(),
    'bitmart': ccxt.bitmart(),
    'gate': ccxt.gate()
}

def build_list_of_exchanges_from_selection(exchanges_selection):
    list_of_exchanges = []
    for exchange in exchanges_selection:
        list_of_exchanges.append(exchanges[exchange.lower()])
    return list_of_exchanges


symbols = [
    "BTC/USDT",
    "LTC/USDT",
    "DOGE/USDT",
    "SHIB/USDT",
    "SOL/USDT",
    "ETH/USDT",
    "ADA/USDT",
    "DOT/USDT",
    "UNI/USDT",
    "LINK/USDT",
]

exchanges_list = [
    "OKX",
    "Bybit",
    "Binance",
    "KuCoin",
    "BitMart",
    "Gate"
]

order_sizes = {
    "BTC/USDT": 0.001,
    "LTC/USDT": 0.01,
    "DOGE/USDT": 100,
    "SHIB/USDT": 1000000,
    "SOL/USDT": 0.1,
    "ETH/USDT": 0.01,
    "ADA/USDT": 1,
    "DOT/USDT": 0.1,
    "UNI/USDT": 0.1,
    "LINK/USDT": 0.1,
}