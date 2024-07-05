import ccxt.async_support as ccxt  # Используем асинхронную версию ccxt
import pandas as pd
import numpy as np
import asyncio

def calculate_atr(df, period=14):
    df['TR'] = np.maximum(df['high'] - df['low'], np.abs(df['high'] - df['close'].shift()), np.abs(df['low'] - df['close'].shift()))
    df['ATR'] = df['TR'].rolling(window=period).mean()
    return df['ATR']

def calculate_adx(df, period=14):
    df['TR'] = np.maximum(df['high'] - df['low'], np.abs(df['high'] - df['close'].shift()), np.abs(df['low'] - df['close'].shift()))
    df['+DM'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), df['high'] - df['high'].shift(), 0)
    df['-DM'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), df['low'].shift() - df['low'], 0)
    df['+DM'] = np.where(df['+DM'] > 0, df['+DM'], 0)
    df['-DM'] = np.where(df['-DM'] > 0, df['-DM'], 0)
    df['+DI'] = 100 * (df['+DM'] / df['TR']).rolling(window=period).mean()
    df['-DI'] = 100 * (df['-DM'] / df['TR']).rolling(window=period).mean()
    df['DX'] = 100 * np.abs((df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI']))
    df['ADX'] = df['DX'].rolling(window=period).mean()
    return df['ADX']

def calculate_bollinger_bands(df, period=20, std_dev=2):
    df['SMA'] = df['close'].rolling(window=period).mean()
    df['STD'] = df['close'].rolling(window=period).std()
    df['Upper Band'] = df['SMA'] + (df['STD'] * std_dev)
    df['Lower Band'] = df['SMA'] - (df['STD'] * std_dev)
    return df[['Upper Band', 'Lower Band']]

def calculate_rsi(df, period=14):
    delta = df['close'].diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df['RSI']

def calculate_correlation(df, period=14):
    df['Correlation'] = df['close'].rolling(window=period).corr(df['close'].shift(1))
    return df['Correlation']

def is_sideways_trend(df):
    atr = calculate_atr(df)
    adx = calculate_adx(df)
    bollinger_bands = calculate_bollinger_bands(df)
    rsi = calculate_rsi(df)
    correlation = calculate_correlation(df)

    is_sideways = (atr < atr.mean()) & (adx < 20) & (correlation < 0.2) & (rsi.between(30, 70))
    return is_sideways

async def fetch_futures_data(exchange, symbol, timeframe='15m', limit=100):
    ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return symbol, df

async def check_sideways_trend_for_symbol(exchange, symbol):
    symbol, df = await fetch_futures_data(exchange, symbol)
    if is_sideways_trend(df).any():
        return symbol, df
    return symbol, None

async def main():
    # Initialize exchange
    exchange = ccxt.bybit()

    try:
        # Fetch all futures markets
        markets = await exchange.load_markets()
        
        # Filter for perpetual contracts nominated in USDT
        futures_symbols = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and market['quote'] == 'USDT']
        
        # Check for sideways trends asynchronously
        tasks = [check_sideways_trend_for_symbol(exchange, symbol) for symbol in futures_symbols]
        results = await asyncio.gather(*tasks)
        
        # Filter results to get only those symbols that are in a sideways trend
        sideways_trends = {symbol: df for symbol, df in results if df is not None}
        
        # Display results
        for symbol, df in sideways_trends.items():
            print(f"Sideways trend detected for {symbol}")
            print(df.tail())
    finally:
        # Ensure resources are properly released
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
