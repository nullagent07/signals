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
        
        # Выполнение технического анализа
        await analyze_data(df, symbol)

async def analyze_data(df, symbol):
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['EMA_12'] = ta.ema(df['close'], length=12)
    df['EMA_26'] = ta.ema(df['close'], length=26)
    df['MACD'] = ta.macd(df['close'])['MACD_12_26_9']
    df['Volume Change'] = df['volume'].pct_change()
    
    # Расчет Bollinger Bands
    bb = ta.bbands(df['close'], length=20, std=2)
    df['Bollinger High'] = bb['BBU_20_2.0']
    df['Bollinger Low'] = bb['BBL_20_2.0']
    
    # Проверка данных индикаторов для отладки
    print(f"{symbol} - Last RSI: {df['RSI'].iloc[-1]}, Last Volume Change: {df['Volume Change'].iloc[-1]}")
    
    # Фильтрация некорректных данных
    if pd.isna(df['Volume Change'].iloc[-1]) or pd.isna(df['RSI'].iloc[-1]):
        return
    
    # Условие для обнаружения Pump с учетом корректных данных
    pump_condition = (df['RSI'] > 70) & (df['Volume Change'] > 1.5)
    
    if pump_condition.iloc[-1]:
        await send_telegram_message(f'Pump detected in {symbol}!')

async def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=message)

# Основная функция
async def main():
    await analyze_all_pairs()

# Запуск функции
if __name__ == "__main__":
    asyncio.run(main())
