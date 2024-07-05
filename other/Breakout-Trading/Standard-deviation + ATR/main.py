import ccxt
import pandas as pd
import talib
import numpy as np
from scipy.signal import argrelextrema
import matplotlib.pyplot as plt

# Создаем объект биржи Bybit
exchange = ccxt.bybit()

# Загружаем все доступные рынки с биржи
markets = exchange.load_markets()

# Фильтруем только те рынки, которые торгуются в парах с USDT и являются perpetual контрактами
usdt_perpetual_pairs = [
    market for market in markets 
    if 'USDT' in market 
    and markets[market].get('type') == 'swap' 
    and markets[market].get('settle') == 'USDT'
]

# Параметры анализа
timeframe = '30m'
limit = 100  # Количество периодов для загрузки
period = 14
low_volatility_threshold = 0.005  # Пример порогового значения для Standard Deviation
low_atr_threshold = 50  # Пример порогового значения для ATR

# Функция для анализа пары
def analyze_pair(symbol):
    try:
        # Загрузка исторических данных
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        # Преобразование данных в DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Расчет Standard Deviation и ATR за 14 периодов
        df['stddev'] = talib.STDDEV(df['close'], timeperiod=period)
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=period)
        
        # Определение низкой волатильности
        df['low_volatility'] = (df['stddev'] < low_volatility_threshold) & (df['atr'] < low_atr_threshold)
        
        # Нахождение локальных минимумов и максимумов
        df['min'] = df.iloc[argrelextrema(df['close'].values, np.less_equal, order=5)[0]]['close']
        df['max'] = df.iloc[argrelextrema(df['close'].values, np.greater_equal, order=5)[0]]['close']
        
        # Проверка, есть ли низкая волатильность в последних данных
        if df['low_volatility'].iloc[-1]:
            print(f"{symbol} has low volatility.")
            # print(f"{df['min']} min")
            # print(f"{df['max']} max")
            print(f"Local max :\n", df[['timestamp', 'max']].dropna())         
            print(f"Local min :\n", df[['timestamp', 'min']].dropna())               
            print("\n" + "="*50 + "\n")       
            return df
        else:
            return None
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

# Анализ всех пар и сбор результатов только для низковолатильных пар
results = {}
for pair in usdt_perpetual_pairs:
    # print(f"Analyzing {pair}...")
    result = analyze_pair(pair)
    if result is not None:
        results[pair] = result

# # Визуализация для всех низковолатильных пар
# for pair, df in results.items():
#     plt.figure(figsize=(12, 6))
#     plt.plot(df['timestamp'], df['close'], label='Close Price')
#     plt.scatter(df['timestamp'], df['min'], label='Support', marker='^', color='g')
#     plt.scatter(df['timestamp'], df['max'], label='Resistance', marker='v', color='r')
#     plt.title(f'Support and Resistance Levels for {pair}')
#     plt.legend()
#     plt.show()
