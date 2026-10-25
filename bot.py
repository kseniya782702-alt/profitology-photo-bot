"""PROFITOLOGY ANALYTICS — Telegram crypto signal assistant (UA)."""
import logging
import os
from datetime import datetime, timezone

import pandas as pd
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
SYMBOLS = {'BTC/USDT': 'BTCUSDT', 'ETH/USDT': 'ETHUSDT', 'SOL/USDT': 'SOLUSDT', 'BNB/USDT': 'BNBUSDT'}


def menu():
    rows = [[InlineKeyboardButton(name, callback_data=f'pair:{symbol}')] for name, symbol in SYMBOLS.items()]
    rows.append([InlineKeyboardButton('OTC (джерело даних недоступне)', callback_data='otc')])
    return InlineKeyboardMarkup(rows)


def signal_button(symbol):
    return InlineKeyboardMarkup([[InlineKeyboardButton('🔎 ОТРИМАТИ СИГНАЛ', callback_data=f'analyze:{symbol}')],
                                 [InlineKeyboardButton('↩️ Інша пара', callback_data='menu')]])


def candles(symbol):
    response = requests.get('https://api.binance.com/api/v3/klines',
                            params={'symbol': symbol, 'interval': '1m', 'limit': 120}, timeout=12)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list) or len(data) < 50:
        raise ValueError('Недостатньо свічок для аналізу')
    # Остання свічка може бути незавершеною — виключаємо її.
    closed = [x for x in data if int(x[6]) <= int(datetime.now(timezone.utc).timestamp() * 1000)]
    if len(closed) < 40:
        raise ValueError('Недостатньо закритих свічок')
    return pd.Series([float(x[4]) for x in closed], dtype='float64')


def analyze(symbol):
    close = candles(symbol)
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rsi = 100 - 100 / (1 + gain.iloc[-1] / max(loss.iloc[-1], 1e-12))
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    upward = ema9.iloc[-1] > ema21.iloc[-1] and macd.iloc[-1] > macd_signal.iloc[-1] and 50 < rsi < 70
    downward = ema9.iloc[-1] < ema21.iloc[-1] and macd.iloc[-1] < macd_signal.iloc[-1] and 30 < rsi < 50
    label = '🟢 BUY / КУПИТИ' if upward else '🔴 SELL / ПРОДАТИ' if downward else '🟡 WAIT / ОЧІКУВАТИ'
    return (f'📊 {symbol} · 1 хвилина\n\n{label}\n\n'
            f'Ціна останньої закритої свічки: {close.iloc[-1]:,.4f} USDT\n'
            f'EMA 9: {ema9.iloc[-1]:,.4f}\nEMA 21: {ema21.iloc[-1]:,.4f}\n'
            f'RSI 14: {rsi:.1f}\nMACD: {macd.iloc[-1]:.5f}\n\n'
            'Це технічний сигнал, а не гарантія результату. '
            'Однохвилинні прогнози мають високий ризик помилки.')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🟢 PROFITOLOGY ANALYTICS\nОберіть актив для аналізу:', reply_markup=menu())


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    value = query.data
    if value == 'menu':
        await query.edit_message_text('Оберіть актив:', reply_markup=menu())
    elif value == 'otc':
        await query.edit_message_text('⚠️ OTC: перевіреного потоку котирувань Pocket Option немає. '
                                      'Не створюємо вигаданих сигналів.', reply_markup=menu())
    elif value.startswith('pair:'):
        symbol = value.split(':', 1)[1]
        if symbol in SYMBOLS.values():
            await query.edit_message_text(f'📈 {symbol}\nТаймфрейм: 1 хвилина', reply_markup=signal_button(symbol))
    elif value.startswith('analyze:'):
        symbol = value.split(':', 1)[1]
        if symbol not in SYMBOLS.values():
            return
        try:
            import asyncio
            result = await asyncio.to_thread(analyze, symbol)
        except Exception as exc:
            LOG.warning('Market data error: %s', exc)
            result = '⚠️ Не вдалося отримати ринкові дані. Спробуйте пізніше.'
        await query.edit_message_text(result, reply_markup=signal_button(symbol))


def main():
    if not TOKEN:
        raise RuntimeError('Задайте TELEGRAM_BOT_TOKEN як змінну середовища; не вставляйте токен у код.')
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(callback))
    app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", "10000")),
    url_path="telegram",
    webhook_url=os.environ["RENDER_EXTERNAL_URL"].rstrip("/") + "/telegram",
    drop_pending_updates=True,
)


if __name__ == '__main__':
    main()
