"""PROFITOLOGY ANALYTICS — free, cautious screenshot chart description.
No Pocket Option connection, prediction, automated trades, or paid AI.
"""
import asyncio
import io
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Prevent httpx request logs from exposing Telegram token in request URLs.
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
for name in ('httpx', 'httpcore', 'telegram'): logging.getLogger(name).setLevel(logging.WARNING)
LOG = logging.getLogger('profitology')
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
MAX_BYTES = 8_000_000


def describe_chart(raw: bytes) -> str:
    if len(raw) > MAX_BYTES:
        return '🟡 ЧЕКАТИ — файл завеликий (понад 8 МБ).'
    try:
        with Image.open(io.BytesIO(raw)) as original:
            image = ImageOps.exif_transpose(original).convert('RGB')
    except (UnidentifiedImageError, OSError, ValueError):
        return '⚠️ Не вдалося відкрити зображення. Надішліть чіткий PNG або JPG.'
    width, height = image.size
    if width < 320 or height < 240:
        return '🟡 ЧЕКАТИ — замала роздільність. Надішліть чіткіший скриншот.'
    # Work on a bounded image. Focus on the central plot to avoid buy/sell buttons.
    image.thumbnail((1600, 1600))
    rgb = np.asarray(image)
    h, w = rgb.shape[:2]
    x0, x1 = int(w * .12), int(w * .88)
    y0, y1 = int(h * .19), int(h * .75)
    crop = rgb[y0:y1, x0:x1]
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    # Typical green/red candle bodies; reject faint background pixels.
    green = cv2.inRange(hsv, (35, 80, 75), (90, 255, 255))
    red = cv2.bitwise_or(cv2.inRange(hsv, (0, 95, 75), (12, 255, 255)),
                         cv2.inRange(hsv, (168, 95, 75), (179, 255, 255)))
    ch, cw = crop.shape[:2]
    # Detect narrow, mostly vertical filled blobs rather than horizontal indicator lines.
    found = []
    for label, mask in [('green', green), ('red', red)]:
        count, _, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
        for i in range(1, count):
            x, y, bw, bh, area = map(int, stats[i])
            if not (2 <= bw <= max(12, int(cw * .045)) and 4 <= bh <= max(20, int(ch * .30))):
                continue
            if not (7 <= area <= max(200, int(cw * ch * .008))):
                continue
            if area / max(1, bw * bh) < .34 or bw > bh * 2.5:
                continue
            found.append((x + bw / 2, y + bh / 2, bh, label))
    found.sort(key=lambda item: item[0])
    # Deduplicate blobs at nearly identical horizontal positions.
    dedup = []
    for item in found:
        if dedup and abs(item[0] - dedup[-1][0]) < max(3, cw * .008):
            if item[2] > dedup[-1][2]: dedup[-1] = item
        else:
            dedup.append(item)
    if len(dedup) < 7:
        return ('📊 PROFITOLOGY ANALYTICS\n\n🟡 ЧЕКАТИ\n'
                'Не вдалося достатньо чітко відокремити свічки від індикаторів або елементів інтерфейсу.\n'
                '📸 Надішліть повний, чіткий графік без меню, із 20–40 видимими свічками.\n\n'
                '⚠️ Живих котирувань Pocket Option/OTC немає; прогноз наступної свічки не виконується.')
    # Remove the far-right UI/price label area and use a bounded recent segment.
    candles = [c for c in dedup if c[0] < cw * .91]
    recent = candles[-min(12, len(candles)):]
    if len(recent) < 6:
        return '🟡 ЧЕКАТИ — недостатньо розпізнаних свічок у правій частині графіка.'
    green_n = sum(c[3] == 'green' for c in recent)
    red_n = len(recent) - green_n
    # Screen y increases downward. A slope of body centers is descriptive only.
    xs = np.array([c[0] for c in recent], dtype=float)
    ys = np.array([c[1] for c in recent], dtype=float)
    if np.ptp(xs) < 10: return '🟡 ЧЕКАТИ — замало горизонтального простору для оцінки.'
    slope = float(np.polyfit(xs, ys, 1)[0])
    delta = float(np.polyval(np.polyfit(xs, ys, 1), xs[-1]) - np.polyval(np.polyfit(xs, ys, 1), xs[0]))
    min_move = max(7, ch * .045)
    if delta < -min_move and green_n >= red_n:
        trend = 'переважно висхідний рух на видимому фрагменті'
    elif delta > min_move and red_n >= green_n:
        trend = 'переважно низхідний рух на видимому фрагменті'
    elif abs(delta) < min_move:
        trend = 'боковий або нечіткий рух'
    else:
        trend = 'суперечливі ознаки руху'
    # Always WAIT: screenshots alone do not justify an execution recommendation.
    return (f'📊 PROFITOLOGY ANALYTICS\n\n'
            f'🟡 ДІЯ: ЧЕКАТИ\n'
            f'🔎 Візуальна оцінка: {trend}.\n'
            f'🕯️ Розпізнано свічкоподібних елементів: {len(dedup)}; останні {len(recent)}: '
            f'🟢 {green_n} / 🔴 {red_n}.\n'
            '📉 EMA, RSI, MACD та рівні цін не обчислюються: з пікселів їх неможливо достовірно відновити.\n\n'
            '⚠️ Це евристика кольорів і геометрії, а не торговий сигнал. '
            'Можливе помилкове розпізнавання ліній індикаторів як свічок. '
            'Немає живих котирувань Pocket Option (включно з OTC); напрямок наступної свічки невідомий.')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        '📊 PROFITOLOGY ANALYTICS\nНадішліть скриншот Pocket Option (OTC, валюта або крипто). '
        'Я безкоштовно опишу видимий тренд і свічкоподібні елементи. '
        'Не відкриваю угод і не прогнозую наступну свічку.')


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    try:
        obj = msg.photo[-1] if msg.photo else msg.document
        if not obj: return
        if getattr(obj, 'file_size', 0) and obj.file_size > MAX_BYTES:
            await msg.reply_text('🟡 ЧЕКАТИ — надішліть зображення до 8 МБ.')
            return
        await msg.reply_text('🔎 Аналізую скриншот…')
        telegram_file = await context.bot.get_file(obj.file_id)
        raw = bytes(await telegram_file.download_as_bytearray())
        answer = await asyncio.to_thread(describe_chart, raw)
        await msg.reply_text(answer)
    except Exception as error:
        LOG.error('Image handling failed: %s', type(error).__name__)
        await msg.reply_text('⚠️ Не вдалося обробити файл. Спробуйте PNG/JPG або повторіть пізніше.')


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/', '/health'):
            self.send_error(404)
            return
        payload = b'OK - PROFITOLOGY\n'
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
    def log_message(self, fmt, *args):
        return


def main():
    if not TOKEN: raise RuntimeError('TELEGRAM_BOT_TOKEN is missing in Render Environment')
    port = int(os.getenv('PORT', '10000'))
    server = ThreadingHTTPServer(('0.0.0.0', port), Health)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    LOG.info('HTTP health server listening on port %s', port)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, on_photo))
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
