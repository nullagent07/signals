import ccxt
import pandas as pd
import pandas_ta as ta
from telegram import Bot
import asyncio
from collections import defaultdict

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

async def fetch_ohlcv(symbol, timeframe='15m', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

async def analyze_currency(currency):
    df = await fetch_ohlcv(currency.symbol)
    print(df)
    # Определение боковика
    window = 20  # период для анализа боковика
    threshold = 0.02  # допустимое отклонение от диапазона в процентах

    df['mean'] = df['close'].rolling(window=window).mean()
    # вычисляет стандартное отклонение цен закрытия за заданное количество периодов
    df['std'] = df['close'].rolling(window=window).std()

    # если прошлая свеча закрылась выше чем пред идущая но в границах боковика то и сам боковик увеличит допустимые границы для ледующей свечи?
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
            await send_telegram_message(f'Pump detected in {currency.symbol}!')
    elif currency.state == 'pump':
        if not df['upper_breakout_with_volume'].iloc[-1] and not df['lower_breakout_with_volume'].iloc[-1]:
            currency.state = 'post-pump'
    elif currency.state == 'post-pump':
        if df['is_sideways'].iloc[-1]:
            currency.state = 'sideways'

async def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message)

async def analyze_all_currencies():
    markets = exchange.load_markets()
    perpetual_usdt_pairs = [symbol for symbol, market in markets.items() if market['type'] == 'swap' and 'USDT' in symbol]

    currency_states = {symbol: CurrencyState(symbol) for symbol in perpetual_usdt_pairs}

    while True:
        # Логи для отслеживания валют по состояниям
        initial_currencies = []
        sideways_currencies = []
        pump_currencies = []
        post_pump_currencies = []

        for symbol, currency in currency_states.items():
            print(symbol)            
            await analyze_currency(currency)

            # Сбор валют по состояниям
            if currency.state == 'initial':
                initial_currencies.append(symbol)
            elif currency.state == 'sideways':
                sideways_currencies.append(symbol)
            elif currency.state == 'pump':
                pump_currencies.append(symbol)
            elif currency.state == 'post-pump':
                post_pump_currencies.append(symbol)

        # Логирование состояний валют
        print(f"Initial: {initial_currencies}")
        print(f"Sideways: {sideways_currencies}")
        print(f"Pump: {pump_currencies}")
        print(f"Post-Pump: {post_pump_currencies}")

        await asyncio.sleep(60)  # задержка между анализами

if __name__ == "__main__":
    asyncio.run(analyze_all_currencies())
