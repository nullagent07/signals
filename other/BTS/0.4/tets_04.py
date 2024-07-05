import ccxt
import pandas as pd
import talib
import matplotlib.pyplot as plt

# Параметры стратегии
timeframe = '1m'
lookback_period = 14
volume_lookback_period = 10

# Функция для определения сигналов на пробой
def is_breakout_trend(df, time_period, volume_lookback_period):
    volume_ma = talib.SMA(df['volume'], timeperiod=volume_lookback_period)
    df['volume_ma'] = volume_ma
    df['volume_increase'] = df['volume'] > volume_ma
    
    high_max = df['high'].rolling(window=time_period).max()
    low_min = df['low'].rolling(window=time_period).min()
    df['high_max'] = high_max
    df['low_min'] = low_min
    df['signal'] = 0

    # Условия для генерации сигналов
    buy_conditions = (df['close'] > high_max.shift(1)) & df['volume_increase']
    sell_conditions = (df['close'] < low_min.shift(1)) & df['volume_increase']

    df.loc[buy_conditions, 'signal'] = 1
    df.loc[sell_conditions, 'signal'] = -1

    stop_loss_long = low_min.shift(1)
    take_profit_long = high_max.shift(1)
    stop_loss_short = high_max.shift(1)
    take_profit_short = low_min.shift(1)
    
    return df[['timestamp', 'close', 'high_max', 'low_min', 'signal', 'volume', 'volume_ma', 'volume_increase']], stop_loss_long, take_profit_long, stop_loss_short, take_profit_short

# Функция для загрузки исторических данных
def fetch_historical_data(symbol, timeframe, limit):
    exchange = ccxt.bybit()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Функция для проведения бэктеста
def backtest_strategy(symbol, timeframe, lookback_period, volume_lookback_period):
    df = fetch_historical_data(symbol, timeframe, limit=max(lookback_period, volume_lookback_period) * 2)
    print("Historical Data:")
    print(df.head())
    
    signals_df, stop_loss_long, take_profit_long, stop_loss_short, take_profit_short = is_breakout_trend(df, lookback_period, volume_lookback_period)
    
    print("Signals DataFrame:")
    print(signals_df.tail())
    
    # Инициализация начального капитала и метрик
    initial_capital = 10000
    capital = initial_capital
    position = 0
    pnl = []
    entry_price = 0
    stop_loss = 0
    take_profit = 0

    for i in range(1, len(signals_df)):
        if signals_df['signal'].iloc[i] == 1 and position == 0:
            position = capital / signals_df['close'].iloc[i]
            capital = 0
            entry_price = signals_df['close'].iloc[i]
            stop_loss = stop_loss_long.iloc[i]
            take_profit = take_profit_long.iloc[i]
        elif signals_df['signal'].iloc[i] == -1 and position == 0:
            position = -capital / signals_df['close'].iloc[i]
            capital = 0
            entry_price = signals_df['close'].iloc[i]
            stop_loss = stop_loss_short.iloc[i]
            take_profit = take_profit_short.iloc[i]
        
        if position > 0:
            if signals_df['close'].iloc[i] <= stop_loss or signals_df['close'].iloc[i] >= take_profit:
                capital = position * signals_df['close'].iloc[i]
                position = 0
        elif position < 0:
            if signals_df['close'].iloc[i] >= stop_loss or signals_df['close'].iloc[i] <= take_profit:
                capital = -position * signals_df['close'].iloc[i]
                position = 0
        
        pnl.append(capital + (position * signals_df['close'].iloc[i] if position != 0 else 0))

    pnl_df = pd.DataFrame({'timestamp': signals_df['timestamp'][1:len(pnl)+1], 'pnl': pnl})
    plt.plot(pnl_df['timestamp'], pnl_df['pnl'])
    plt.xlabel('Time')
    plt.ylabel('PnL')
    plt.title('Backtest PnL')
    plt.show()

    print(f"Initial capital: {initial_capital}")
    print(f"Ending capital: {capital + (position * signals_df['close'].iloc[-1] if position != 0 else 0)}")
    print(f"PnL: {(capital + (position * signals_df['close'].iloc[-1] if position != 0 else 0)) - initial_capital}")

# Запуск бэктеста для пары BTC/USDT
symbol = 'BTC/USDT'
backtest_strategy(symbol, timeframe, lookback_period, volume_lookback_period)
