import sys

import ccxt.pro as ccxtpro
import asyncio
from utils.environement import load_env_variables

# from oldArbitrage.debug_api_key import exchange

if sys.platform.startswith('win'):
    print('system is windows')
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    
    api_key, secret = load_env_variables()
    exchange = ccxtpro.binance({
        'apiKey': api_key,
        'secret': secret,
        'enableRateLimit': True,
    })
    if exchange:
        await exchange.close()
    await exchange.load_markets()

    # Real-time ticker updates
    while ticker:
        ticker = await exchange.watch_ticker('BTC/USDT')
        print(ticker)
        
    

asyncio.run(main())
