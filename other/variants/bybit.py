# import ccxt
# import pandas as pd
# import time
# from datetime import datetime, timedelta, timezone

# exchange = ccxt.bybit({
#     'apiKey': '1VNiNtRcjuO1mmrrmj',
#     'secret': '79RS2q1PY8NEJwtqCxFLgQqyxzcFKd1YtBXL',
# })
# import ccxt
# import pandas as pd
# from datetime import datetime, timedelta

# def fetch_ohlcv(exchange, symbol, timeframe='1d', since=None):
#     ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since)
#     return pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

# def is_consolidating(df, days=14, threshold=0.02):
#     recent_data = df.tail(days)
#     price_range = recent_data['close'].max() - recent_data['close'].min()
#     avg_price = recent_data['close'].mean()
#     return price_range / avg_price < threshold

# # Инициализация биржи
# exchange = ccxt.bybit()
# markets = exchange.load_markets()

# consolidating_pairs = []
# threshold_percentage = 0.02  # Порог консолидации, например, 2%
# days_to_check = 14

# since = int((datetime.now() - timedelta(days=days_to_check * 2)).timestamp() * 1000)  # За последние 28 дней

# # Проверка каждой пары
# for symbol, market in markets.items():
#     if market['type'] != 'future':  # Проверяем, что это фьючерсный рынок
#         continue
#     try:
#         df = fetch_ohlcv(exchange, symbol, since=since)
#         if not df.empty and len(df) >= days_to_check:
#             if is_consolidating(df, days=days_to_check, threshold=threshold_percentage):
#                 consolidating_pairs.append(symbol)
#     except Exception as e:
#         print(f"Не удалось получить данные для {symbol}: {e}")

# print("Фьючерсные пары с консолидацией за последние 14 дней:", consolidating_pairs)

# import ccxt

# exchange = ccxt.bybit({
#     'apiKey': '1VNiNtRcjuO1mmrrmj',
#     'secret': '79RS2q1PY8NEJwtqCxFLgQqyxzcFKd1YtBXL',
# })

# # Загрузка всех рынков
# markets = exchange.load_markets()

# # Фильтрация бессрочных контрактов, номинированных в USDT
# perpetual_usdt_pairs = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and 'USDT' in symbol]

# # Вывод бессрочных USDT пар
# for pair in perpetual_usdt_pairs:
#     print(pair)


import ccxt
import talib as ta

import pandas as pd
import numpy as np

# Создание экземпляра биржи Bybit
exchange = ccxt.bybit()

# Загрузка всех рынков
markets = exchange.load_markets()

# Фильтрация бессрочных контрактов, номинированных в USDT
perpetual_usdt_pairs = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and 'USDT' in symbol]

# Параметры анализа
time_period = 2
atr_threshold = 0.005  # 0.5% волатильности
range_percentage = 0.02  # ±2% от средней цены

# Функция для определения бокового тренда
def is_sideways_trend(symbol, df, time_period, atr_threshold, range_percentage):
    # Расчет ATR
    df['ATR'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=time_period)
    
    # Средняя цена за период
    df['SMA'] = ta.SMA(df['close'], timeperiod=time_period)
    
    # Условие 1: ATR ниже порога
    atr_condition = df['ATR'].iloc[-1] < atr_threshold * df['SMA'].iloc[-1]
    
    # Условие 2: Цены не выходят за рамки диапазона ±2% от средней цены
    price_condition = (df['close'] > df['SMA'] * (1 - range_percentage)).all() and (df['close'] < df['SMA'] * (1 + range_percentage)).all()
    
    return atr_condition and price_condition

# Анализ бокового тренда для каждой пары
sideways_trends = []

for symbol in perpetual_usdt_pairs:

    print(symbol)
    # Загрузка исторических данных
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=time_period)
    print(ohlcv)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Преобразование времени
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Определение бокового тренда
    if is_sideways_trend(symbol, df, time_period, atr_threshold, range_percentage):
        sideways_trends.append(symbol)

# Вывод пар с боковым трендом
print("Pairs with sideways trend:")
for pair in sideways_trends:
    print(pair)
