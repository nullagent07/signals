import ccxt
import talib
import pandas as pd
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def fetch_ohlcv(exchange, symbol, timeframe='1h', limit=168):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        ohlcv = await loop.run_in_executor(
            pool, exchange.fetch_ohlcv, symbol, timeframe, limit
        )
    return ohlcv

async def fetch_and_analyze_symbol(exchange, symbol, rsi_period=14, bb_period=20, atr_period=14):
    try:
        # Fetch historical data for the symbol
        ohlcv = await fetch_ohlcv(exchange, symbol)

        # Convert data to pandas DataFrame
        data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
        data.set_index('timestamp', inplace=True)

        # Calculate indicators
        data['rsi'] = talib.RSI(data['close'], timeperiod=rsi_period)
        data['upper_band'], data['middle_band'], data['lower_band'] = talib.BBANDS(data['close'], timeperiod=bb_period, nbdevup=2, nbdevdn=2, matype=0)
        data['atr'] = talib.ATR(data['high'], data['low'], data['close'], timeperiod=atr_period)

        # Criteria for sideways market (bikovik)
        rsi_neutral_zone = (data['rsi'] > 40) & (data['rsi'] < 60)
        price_between_bands = (data['close'] > data['lower_band']) & (data['close'] < data['upper_band'])
        low_atr = data['atr'] < data['atr'].rolling(window=atr_period).mean()

        data['sideways'] = rsi_neutral_zone & price_between_bands & low_atr

        # If the market is sideways for more than half of the period, consider it as sideways
        if data['sideways'].sum() > (len(data) / 2):
            return symbol
        else:
            return None
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

async def main():
    # Initialize exchange
    exchange = ccxt.bybit()

    # Fetch all futures markets
    markets = exchange.load_markets()

    # Filter for perpetual contracts nominated in USDT
    futures_symbols = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and market['quote'] == 'USDT']

    # Analyze each symbol asynchronously
    tasks = [fetch_and_analyze_symbol(exchange, symbol) for symbol in futures_symbols]
    results = await asyncio.gather(*tasks)

    # Filter out None values
    sideways_symbols = [result for result in results if result is not None]

    # Print symbols with sideways market
    print("Symbols with sideways market:", sideways_symbols)

asyncio.run(main())
