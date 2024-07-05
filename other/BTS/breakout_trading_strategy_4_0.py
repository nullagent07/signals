import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import talib

# Параметры стратегии
timeframe = '1m'  # Таймфрейм теперь 1 минута для более частого анализа
lookback_period = 14
breakout_threshold = 1.05  # 5% выше уровня сопротивления или ниже уровня поддержки
volume_lookback_period = 20  # Период для скользящего среднего объема

# Функция для определения аномального роста объема
def is_anomalous_volume(df, volume_lookback_period):
    volume_ma = talib.SMA(df['volume'], timeperiod=volume_lookback_period)
    volume_std = df['volume'].rolling(window=volume_lookback_period).std()
    anomalous_volume = df['volume'] > (volume_ma + 2 * volume_std)
    df['volume_ma'] = volume_ma
    df['volume_std'] = volume_std
    df['anomalous_volume'] = anomalous_volume
    return df

# Функция для определения сигналов на пробой с учетом аномального объема
def is_breakout_trend(df, time_period, breakout_threshold, volume_lookback_period):
    df = is_anomalous_volume(df, volume_lookback_period)
    
    # Определение уровней сопротивления и поддержки
    high_max = df['high'].rolling(window=time_period).max()
    low_min = df['low'].rolling(window=time_period).min()
    df['high_max'] = high_max
    df['low_min'] = low_min

    # Определение сигналов на пробой с использованием .loc
    df['signal'] = 0
    df.loc[(df['close'] > high_max.shift(1) * breakout_threshold) & df['anomalous_volume'], 'signal'] = 1  # Покупка при пробое сопротивления и аномальном объеме
    df.loc[(df['close'] < low_min.shift(1) * (2 - breakout_threshold)) & df['anomalous_volume'], 'signal'] = -1  # Продажа при пробое поддержки и аномальном объеме

    # Установка стоп-лосса и тейк-профита
    stop_loss_long = low_min.shift(1)
    take_profit_long = df['close'] * (1 + (df['close'] - low_min.shift(1)) / low_min.shift(1))

    stop_loss_short = high_max.shift(1)
    take_profit_short = df['close'] * (1 - (high_max.shift(1) - df['close']) / high_max.shift(1))

    return df[['timestamp', 'close', 'high_max', 'low_min', 'signal', 'volume', 'volume_ma', 'volume_std', 'anomalous_volume']], stop_loss_long, take_profit_long, stop_loss_short, take_profit_short

# Асинхронная функция для анализа одной пары
async def analyze_pair(exchange, symbol):
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

            # Ожидание 1 секунды перед следующим запросом
            await asyncio.sleep(1)
        except ccxt.NetworkError as e:
            print(f"Network error analyzing {symbol}: {e}")
            await asyncio.sleep(1)  # Повторить через 1 секунду в случае ошибки сети
        except ccxt.ExchangeError as e:
            print(f"Exchange error analyzing {symbol}: {e}")
            await asyncio.sleep(1)  # Повторить через 1 секунду в случае ошибки биржи
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            await asyncio.sleep(1)  # Повторить через 1 секунду в случае общей ошибки

# Асинхронная функция для анализа всех пар
async def analyze_all_pairs():
    exchange = ccxt.bybit()
    await exchange.load_markets()
    
    # Фильтрация бессрочных контрактов, номинированных в USDT
    perpetual_usdt_pairs = [symbol for symbol, market in exchange.markets.items() if market['type'] == 'swap' and 'USDT' in symbol]
    
    # Создание задач для всех пар
    tasks = [analyze_pair(exchange, symbol) for symbol in perpetual_usdt_pairs]
    
    # Запуск всех задач
    await asyncio.gather(*tasks)

# Запуск анализа
asyncio.run(analyze_all_pairs())
