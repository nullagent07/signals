import ccxt
import talib
import pandas as pd
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Функция для получения исторических данных
async def fetch_ohlcv(exchange, symbol, timeframe='15m', limit=96):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        ohlcv = await loop.run_in_executor(
            pool, exchange.fetch_ohlcv, symbol, timeframe, limit
        )
    return ohlcv

# Функция для вычисления индикаторов и определения бокового тренда
def analyze_data(data, rsi_period=14, bb_period=20, atr_period=14):
    data['rsi'] = talib.RSI(data['close'], timeperiod=rsi_period)
    data['upper_band'], data['middle_band'], data['lower_band'] = talib.BBANDS(data['close'], timeperiod=bb_period, nbdevup=2, nbdevdn=2, matype=0)
    data['atr'] = talib.ATR(data['high'], data['low'], data['close'], timeperiod=atr_period)
    data['volume_sma'] = data['volume'].rolling(window=9).mean()
    return data

# Функция для выявления объемных и ценовых спайков
def detect_spikes(data):
    data['volume_spike'] = data['volume'] > data['volume_sma'] * 2
    data['price_spike'] = ((data['close'] - data['close'].shift(1)) / data['close'].shift(1)).abs() > 0.05
    return data

# Основная асинхронная функция
async def main():
    exchange = ccxt.bybit()
    markets = exchange.load_markets()
    futures_symbols = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and market['quote'] == 'USDT']

    timeframe = '15m'
    rsi_period = 14
    bb_period = 20
    atr_period = 14
    limit = 500  # Для бэктестинга возьмем больше данных

    results = []

    for symbol in futures_symbols:
        ohlcv = await fetch_ohlcv(exchange, symbol, timeframe, limit)
        
        # Преобразование данных в DataFrame
        data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
        data.set_index('timestamp', inplace=True)

        # Анализ данных и расчет индикаторов
        data = analyze_data(data, rsi_period, bb_period, atr_period)

        # Выявление спайков
        data = detect_spikes(data)

        # Проверка наличия спайков
        if data['volume_spike'].any() or data['price_spike'].any():
            results.append(symbol)
            print(f"Signal detected for {symbol}")

    # Вывод всех символов с сигналами
    print("Symbols with signals:", results)

asyncio.run(main())
