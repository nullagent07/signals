import ccxt
import pandas as pd
import pandas_ta as ta
from telegram import Bot
import asyncio
from datetime import datetime, timedelta

# Установите ваш токен Telegram и CHAT_ID
TELEGRAM_TOKEN = '7427463023:AAGkZ2xjm_d34O96SIF7AjM90BQT-3QC4Tk'
CHAT_ID = '555634362'

# Создание экземпляра биржи Bybit
exchange = ccxt.bybit()

# Классы для отслеживания состояния валют
class CurrencyState:
    def __init__(self, symbol):
        self.symbol = symbol
        self.state = 'initial'  # initial, sideways, pump, post-pump
        self.data = None  # хранение данных о валюте

def fetch_ohlcv(symbol, timeframe='1m', since=None, limit=1000):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

async def analyze_currency(currency):
    df = currency.data

    # Определение боковика
    window = 20  # период для анализа боковика (20 свечей)
    threshold = 0.02  # допустимое отклонение от диапазона в процентах

    df['mean'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()
    df['upper_band'] = df['mean'] + threshold * df['mean']
    df['lower_band'] = df['mean'] - threshold * df['mean']
    df['is_sideways'] = (df['close'] <= df['upper_band']) & (df['close'] >= df['lower_band'])

    # Определение пробоя
    breakout_threshold = 0.05  # порог для пробоя в процентах
    df['upper_breakout'] = df['close'] > (df['upper_band'] * (1 + breakout_threshold))
    df['lower_breakout'] = df['close'] < (df['lower_band'] * (1 - breakout_threshold))

    # Проверка объема
    volume_threshold = 2  # порог для увеличения объема
    df['volume_increase'] = df['volume'] > (df['volume'].rolling(window=window).mean() * volume_threshold)

    df['upper_breakout_with_volume'] = df['upper_breakout'] & df['volume_increase']
    df['lower_breakout_with_volume'] = df['lower_breakout'] & df['volume_increase']

    currency.data = df

    if currency.state == 'initial':
        if df['is_sideways'].iloc[-1]:
            currency.state = 'sideways'
    elif currency.state == 'sideways':
        if df['upper_breakout_with_volume'].iloc[-1] or df['lower_breakout_with_volume'].iloc[-1]:
            currency.state = 'pump'
            await send_telegram_message(f'Pump detected in {currency.symbol} at {df.index[-1]}!')
    elif currency.state == 'pump':
        if not df['upper_breakout_with_volume'].iloc[-1] and not df['lower_breakout_with_volume'].iloc[-1]:
            currency.state = 'post-pump'
    elif currency.state == 'post-pump':
        if df['is_sideways'].iloc[-1]:
            currency.state = 'sideways'

async def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message)

async def backtest_all_currencies():
    markets = exchange.load_markets()
    perpetual_usdt_pairs = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and 'USDT' in symbol]

    currency_states = {symbol: CurrencyState(symbol) for symbol in perpetual_usdt_pairs}

    start_date = datetime.now() - timedelta(days=30)  # берем данные за последние 30 дней
    since = int(start_date.timestamp() * 1000)

    for symbol, currency in currency_states.items():
        currency.data = fetch_ohlcv(symbol, since=since)
        await analyze_currency(currency)

if __name__ == "__main__":
    asyncio.run(backtest_all_currencies())

