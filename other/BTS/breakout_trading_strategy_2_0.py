import asyncio
import ccxt.async_support as ccxt
import pandas as pd

# Создание экземпляра биржи Bybit
exchange = ccxt.bybit()

# Параметры стратегии
timeframe = '30m'
lookback_period = 14
breakout_threshold = 1.05  # 5% выше уровня сопротивления или ниже уровня поддержки
volume_lookback_period = 20  # Период для скользящего среднего объема

# Функция для определения аномального роста объема
def is_anomalous_volume(df, volume_lookback_period):
    df['volume_ma'] = df['volume'].rolling(window=volume_lookback_period).mean()
    df['volume_std'] = df['volume'].rolling(window=volume_lookback_period).std()
    df['anomalous_volume'] = (df['volume'] > df['volume_ma'] + 2 * df['volume_std'])
    return df

# Функция для определения сигналов на пробой с учетом аномального объема
def is_breakout_trend(df, time_period, breakout_threshold, volume_lookback_period):
    df = is_anomalous_volume(df, volume_lookback_period)
    
    # Определение уровней сопротивления и поддержки
    df['high_max'] = df['high'].rolling(window=time_period).max()
    df['low_min'] = df['low'].rolling(window=time_period).min()

    # Определение сигналов на пробой с использованием .loc
    df['signal'] = 0
    df.loc[(df['close'] > df['high_max'].shift(1) * breakout_threshold) & df['anomalous_volume'], 'signal'] = 1  # Покупка при пробое сопротивления и аномальном объеме
    df.loc[(df['close'] < df['low_min'].shift(1) * (2 - breakout_threshold)) & df['anomalous_volume'], 'signal'] = -1  # Продажа при пробое поддержки и аномальном объеме

    # Установка стоп-лосса и тейк-профита
    stop_loss_long = df['low_min'].shift(1)
    take_profit_long = df['close'] * (1 + (df['close'] - df['low_min'].shift(1)) / df['low_min'].shift(1))

    stop_loss_short = df['high_max'].shift(1)
    take_profit_short = df['close'] * (1 - (df['high_max'].shift(1) - df['close']) / df['high_max'].shift(1))

    return df[['timestamp', 'close', 'high_max', 'low_min', 'signal', 'volume', 'volume_ma', 'volume_std', 'anomalous_volume']], stop_loss_long, take_profit_long, stop_loss_short, take_profit_short

# Асинхронная функция для анализа одной пары
async def analyze_pair(symbol):
    while True:
        try:
            # Загрузка исторических данных
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=max(lookback_period, volume_lookback_period) * 2)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Преобразование времени
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Определение сигналов на пробой
            signals_df, stop_loss_long, take_profit_long, stop_loss_short, take_profit_short = is_breakout_trend(df, lookback_period, breakout_threshold, volume_lookback_period)
            
            # Проверка текущего сигнала и вывод результатов, если есть сигнал
            current_signal = signals_df['signal'].iloc[-1]
            if current_signal != 0:            
                print(f"Pair: {symbol}")
                print(signals_df.tail(10))  # Вывод последних 10 записей
                print("Current signal:", current_signal)
                if current_signal == 1:
                    print("Stop loss for long position:", stop_loss_long.iloc[-1])
                    print("Take profit for long position:", take_profit_long.iloc[-1])
                elif current_signal == -1:
                    print("Stop loss for short position:", stop_loss_short.iloc[-1])
                    print("Take profit for short position:", take_profit_short.iloc[-1])
                    print("\n" + "="*50 + "\n")

            # Ожидание 10 секунд перед следующим запросом
            await asyncio.sleep(10)
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            await asyncio.sleep(10)  # Повторить через 10 секунд в случае ошибки

# Асинхронная функция для анализа всех пар
async def analyze_all_pairs():
    # Загрузка всех рынков
    markets = await exchange.load_markets()
    
    # Фильтрация бессрочных контрактов, номинированных в USDT
    perpetual_usdt_pairs = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and 'USDT' in symbol]
    
    # Создание задач для всех пар
    tasks = [asyncio.create_task(analyze_pair(symbol)) for symbol in perpetual_usdt_pairs]
    
    # Запуск всех задач
    await asyncio.gather(*tasks)

# Запуск анализа
asyncio.run(analyze_all_pairs())