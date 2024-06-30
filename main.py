import ccxt
import pandas as pd
import time
from datetime import datetime, timedelta, timezone

# Инициализация биржи с использованием ваших API ключей
exchange = ccxt.bybit({
    'apiKey': '1VNiNtRcjuO1mmrrmj',
    'secret': '79RS2q1PY8NEJwtqCxFLgQqyxzcFKd1YtBXL',
})

# Параметры
timeframe = '1m'  # Таймфрейм
interval = 60  # Интервал времени для проверки условий в секундах

# Функции для анализа

def check_sideways_trend(df, range_threshold=0.5):
    max_price = df['high'].max()
    min_price = df['low'].min()
    price_range = max_price - min_price
    avg_price = df['close'].mean()
    return (price_range / avg_price) * 100 < range_threshold

def check_sudden_pump(df, price_increase_threshold=5, volume_increase_threshold=50):
    df['price_change'] = df['close'].pct_change() * 100
    df['volume_change'] = df['volume'].pct_change() * 100
    
    recent_data = df.iloc[-5:]  # последние 5 минут
    price_change = (recent_data['close'].iloc[-1] / recent_data['close'].iloc[0] - 1) * 100
    avg_volume_change = recent_data['volume_change'].mean()
    
    return price_change >= price_increase_threshold and avg_volume_change >= volume_increase_threshold

def check_increasing_oi(symbol, oi_increase_threshold=5):
    # Пример данных об OI, замените на реальный запрос к API, если он доступен
    now = datetime.now(timezone.utc)
    oi_data = [
        [now - timedelta(minutes=i), 100 + i] for i in range(30)
    ]
    df_oi = pd.DataFrame(oi_data, columns=['timestamp', 'oi'])
    
    df_oi['timestamp'] = pd.to_datetime(df_oi['timestamp'])
    df_oi['oi_change'] = df_oi['oi'].pct_change() * 100
    
    recent_oi_change = df_oi['oi_change'].iloc[-5:]  # последние 5 минут
    avg_oi_change = recent_oi_change.mean()
    
    return avg_oi_change >= oi_increase_threshold

# Фильтрация символов для линейных рынков (Perpetual Contracts)
def get_supported_symbols(markets):
    supported_symbols = []
    for symbol, market in markets.items():
        if market['type'] == 'linear':
            supported_symbols.append(symbol)
    return supported_symbols

# Получение всех символов (торговых пар)
markets = exchange.load_markets()
symbols = get_supported_symbols(markets)

# Постоянный анализ всех символов
while True:
    results = []
    for symbol in symbols:
        try:
            # Получение текущего времени и исторических данных OHLCV
            now = datetime.now(timezone.utc)
            since = exchange.parse8601((now - timedelta(minutes=30)).isoformat())  # Последние 30 минут

            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since)

            # Конвертация данных в DataFrame для удобного анализа
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Проверка на боковой тренд
            is_sideways = check_sideways_trend(df)

            # Проверка на рост открытого интереса (OI)
            is_increasing_oi = check_increasing_oi(symbol)

            # Если боковой тренд и рост OI обнаружены, выполняем действия
            if is_sideways and is_increasing_oi:
                # Добавьте ваши действия здесь (например, уведомление, отправка сигнала и т.д.)
                print(f"Сигнал обнаружен для {symbol}!")

                results.append({
                    'symbol': symbol,
                    'sideways': is_sideways,
                    'sudden_pump': check_sudden_pump(df),
                    'increasing_oi': is_increasing_oi
                })

        except ccxt.BaseError as e:
            print(f"Ошибка при обработке {symbol}: {e}")

    # Вывод результатов для символов с боковым трендом и ростом OI
    for result in results:
        print(f"Символ: {result['symbol']}")
        print(f"Боковой тренд: {'Да' if result['sideways'] else 'Нет'}")
        print(f"Резкий памп: {'Да' if result['sudden_pump'] else 'Нет'}")
        print(f"Рост OI: {'Да' if result['increasing_oi'] else 'Нет'}")
        print('-------------------')

    # Ожидание перед следующей проверкой
    time.sleep(interval)
