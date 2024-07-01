import ccxt
import pandas as pd
import pandas_ta as ta

# Создание экземпляра биржи Bybit
exchange = ccxt.bybit()

# Параметры стратегии
timeframe = '1h'
lookback_period = 14
breakout_threshold = 1.01  # 1% выше уровня сопротивления или ниже уровня поддержки

# Функция для определения сигналов на пробой
def is_breakout_trend(symbol, df, time_period, breakout_threshold):
    # Определение уровней сопротивления и поддержки
    df['high_max'] = df['high'].rolling(window=time_period).max()
    df['low_min'] = df['low'].rolling(window=time_period).min()

    # Определение сигналов на пробой с использованием .loc
    df['signal'] = 0
    df.loc[df['close'] > df['high_max'].shift(1) * breakout_threshold, 'signal'] = 1  # Покупка при пробое сопротивления
    df.loc[df['close'] < df['low_min'].shift(1) * (2 - breakout_threshold), 'signal'] = -1  # Продажа при пробое поддержки

    # Установка стоп-лосса и тейк-профита
    stop_loss_long = df['low_min'].shift(1)
    take_profit_long = df['close'] * (1 + (df['close'] - df['low_min'].shift(1)) / df['low_min'].shift(1))

    stop_loss_short = df['high_max'].shift(1)
    take_profit_short = df['close'] * (1 - (df['high_max'].shift(1) - df['close']) / df['high_max'].shift(1))

    return df[['timestamp', 'close', 'high_max', 'low_min', 'signal']], stop_loss_long, take_profit_long, stop_loss_short, take_profit_short

# Загрузка всех рынков
markets = exchange.load_markets()

# Фильтрация бессрочных контрактов, номинированных в USDT
perpetual_usdt_pairs = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and 'USDT' in symbol]

# Анализ пробоя для каждой пары
for symbol in perpetual_usdt_pairs:
    # Загрузка исторических данных
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=lookback_period*2)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Преобразование времени
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Определение сигналов на пробой
    signals_df, stop_loss_long, take_profit_long, stop_loss_short, take_profit_short = is_breakout_trend(symbol, df, lookback_period, breakout_threshold)
    
    # Вывод результатов для текущей пары
    print(f"Pair: {symbol}")
    print(signals_df.tail(10))  # Вывод последних 10 записей
    print("Current signal:", signals_df['signal'].iloc[-1])
    if signals_df['signal'].iloc[-1] == 1:
        print("Stop loss for long position:", stop_loss_long.iloc[-1])
        print("Take profit for long position:", take_profit_long.iloc[-1])
    elif signals_df['signal'].iloc[-1] == -1:
        print("Stop loss for short position:", stop_loss_short.iloc[-1])
        print("Take profit for short position:", take_profit_short.iloc[-1])
    else:
        print("No breakout signal at the moment.")
    print("\n" + "="*50 + "\n")

