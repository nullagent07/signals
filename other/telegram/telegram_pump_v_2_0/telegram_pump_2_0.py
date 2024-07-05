import ccxt
import pandas as pd
import pandas_ta as ta
from telegram import Bot
import asyncio

# Установите ваш токен Telegram
TELEGRAM_TOKEN = '7427463023:AAGkZ2xjm_d34O96SIF7AjM90BQT-3QC4Tk'
CHAT_ID = '555634362'

# Создание экземпляра биржи Bybit
exchange = ccxt.bybit()

async def analyze_all_pairs():
    # Загрузка всех рынков
    markets = exchange.load_markets()
    
    # Фильтрация бессрочных контрактов, номинированных в USDT
    perpetual_usdt_pairs = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and 'USDT' in symbol]
    
    for symbol in perpetual_usdt_pairs:
        # Получение данных о свечах
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Выполнение анализа боковика и пробоев
        await analyze_sideways_and_breakouts(df, symbol)

async def analyze_sideways_and_breakouts(df, symbol):
    # Определение боковика
    window = 20  # период для анализа боковика
    threshold = 0.02  # допустимое отклонение от диапазона в процентах

    # Рассчет средней цены и стандартного отклонения
    df['mean'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()

    # Определение верхней и нижней границ боковика
    df['upper_band'] = df['mean'] + threshold * df['mean']
    df['lower_band'] = df['mean'] - threshold * df['mean']

    # Проверка на боковик
    df['is_sideways'] = (df['close'] <= df['upper_band']) & (df['close'] >= df['lower_band'])

    # Определение пробоя
    breakout_threshold = 0.05  # порог для пробоя в процентах
    df['upper_breakout'] = df['close'] > (df['upper_band'] * (1 + breakout_threshold))
    df['lower_breakout'] = df['close'] < (df['lower_band'] * (1 - breakout_threshold))

    # Проверка объема
    volume_threshold = 2  # порог для увеличения объема
    df['volume_increase'] = df['volume'] > (df['volume'].rolling(window=window).mean() * volume_threshold)

    # Проверка условий пробоя с увеличением объема
    df['upper_breakout_with_volume'] = df['upper_breakout'] & df['volume_increase']
    df['lower_breakout_with_volume'] = df['lower_breakout'] & df['volume_increase']

    # Логирование и уведомление при пробое с увеличением объема
    if df['upper_breakout_with_volume'].iloc[-1]:
        await send_telegram_message(f'Upper breakout with volume detected in {symbol}!')
    if df['lower_breakout_with_volume'].iloc[-1]:
        await send_telegram_message(f'Lower breakout with volume detected in {symbol}!')

async def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message)

# Основная функция
async def main():
    await analyze_all_pairs()

# Запуск функции
if __name__ == "__main__":
    asyncio.run(main())
