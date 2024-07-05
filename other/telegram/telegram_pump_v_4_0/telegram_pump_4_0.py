import ccxt
import pandas as pd
import talib
from telegram import Bot
import asyncio

# Установите ваш токен Telegram и CHAT_ID
TELEGRAM_TOKEN = '7427463023:AAGkZ2xjm_d34O96SIF7AjM90BQT-3QC4Tk'
CHAT_ID = '555634362'

# Создание экземпляра биржи Bybit
exchange = ccxt.bybit()

async def fetch_ohlcv(symbol, timeframe='15m', limit=100):
    # Получение исторических данных OHLCV
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

async def analyze_currency(symbol):
    df = await fetch_ohlcv(symbol)

    # Параметры для анализа
    window = 20  # Период для расчета среднего объема
    price_threshold = 0.05  # Порог для увеличения цены в процентах
    volume_threshold = 2  # Порог для увеличения объема

    # Проверка увеличения цены (процентное изменение)
    df['price_increase'] = df['close'].pct_change() > price_threshold

    # Проверка увеличения объема (скользящее среднее объема)
    df['volume_mean'] = talib.SMA(df['volume'], timeperiod=window)
    df['volume_increase'] = df['volume'] > (df['volume_mean'] * volume_threshold)

    # Обнаружение сигнала увеличения цены и объема
    df['signal'] = df['price_increase'] & df['volume_increase']

    # Отправка уведомления, если сигнал обнаружен
    if df['signal'].iloc[-1]:
        await send_telegram_message(f'Significant price and volume increase detected in {symbol}!')

async def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message)

async def analyze_all_currencies():
    markets = exchange.load_markets()
    perpetual_usdt_pairs = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and 'USDT' in symbol]

    while True:
        for symbol in perpetual_usdt_pairs:
            await analyze_currency(symbol)
        await asyncio.sleep(1)  # задержка между анализами в 1 секунду

if __name__ == "__main__":
    asyncio.run(analyze_all_currencies())
