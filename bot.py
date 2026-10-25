"""PROFITOLOGY ANALYTICS — free, heuristic screenshot analysis (not a trading predictor)."""
import asyncio
import io
import logging
import os

import cv2
import numpy as np
from PIL import Image, ImageOps
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
LOG = logging.getLogger('profitology')
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


def analyze_image(raw: bytes) -> str:
    im = Image.open(io.BytesIO(raw))
    im = ImageOps.exif_transpose(im).convert('RGB')
    im.thumbnail((1200, 1200))
    rgb = np.asarray(im)
    h, w = rgb.shape[:2]
    if h < 220 or w < 220:
        return '🟡 ЧЕКАТИ\nЗображення надто мале для оцінки. Надішліть чіткий скриншот графіка.'

    # Central upper region usually contains the candlestick chart, but UI layouts vary.
    roi = rgb[int(h * .12):int(h * .65), int(w * .08):int(w * .94)]
    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    # Identify vivid green and red chart marks. Exclude low-saturation UI text/background.
    green = cv2.inRange(hsv, (35, 80, 75), (90, 255, 255))
    red = cv2.bitwise_or(cv2.inRange(hsv, (0, 90, 75), (12, 255, 255)),
                         cv2.inRange(hsv, (165, 90, 75), (179, 255, 255)))
    # Ignore small colored artifacts, and count only vertical-ish connected components.
    def components(mask):
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
        found = []
        for i in range(1, count):
            x, y, cw, ch, area = stats[i]
            if 4 <= cw <= roi.shape[1] * .09 and 5 <= ch <= roi.shape[0] * .35 and area >= 14 and ch >= cw * .7:
                found.append((x + cw / 2, y + ch / 2, area))
        return found
    greens = components(green)
    reds = components(red)
    all_marks = [(x, y, 1) for x, y, _ in greens] + [(x, y, -1) for x, y, _ in reds]
    # If not enough distinct marks, abstain. Never imply accurate candle recognition.
    if len(all_marks) < 7:
        return ('🟡 ЧЕКАТИ\nНе вдалося впевнено відокремити свічки від інших елементів.\n'
                'Надішліть скриншот без зайвих панелей, щоб було видно 20–30 свічок.')
    all_marks.sort(key=lambda p: p[0])
    # Require marks spread over a meaningful width; colored indicators can otherwise mislead.
    xs = [m[0] for m in all_marks]
    if max(xs) - min(xs) < roi.shape[1] * .25:
        return '🟡 ЧЕКАТИ\nНа зображенні недостатньо розбірливих свічок для оцінки.'
    recent = all_marks[-max(5, len(all_marks) // 3):]
    n_green = sum(1 for _, _, c in recent if c == 1)
    n_red = len(recent) - n_green
    # Heuristic color balance only; cannot infer trade outcome.
    tendency = ('переважають зелені елементи' if n_green > n_red * 1.5 else
                'переважають червоні елементи' if n_red > n_green * 1.5 else
                'немає явної переваги кольору')
    return (f'📊 PROFITOLOGY ANALYTICS\n\n🟡 ЧЕКАТИ\n'
            f'На правій частині видимого графіка {tendency}.\n'
            'Це лише приблизний аналіз кольорових елементів скриншота, а не підтверджений сигнал. '
            'Алгоритм може сплутати свічки з індикаторами та кнопками.\n\n'
            '⚠️ Немає живих котирувань Pocket Option, зокрема OTC. '
            'За одним зображенням не можна надійно передбачити наступну свічку.')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📊 PROFITOLOGY ANALYTICS\nНадішліть скриншот графіка Pocket Option (OTC, валюти або крипто). '
        'Я безкоштовно оціню видимі елементи графіка. Це не торговий сигнал.')


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    await msg.reply_text('🔎 Аналізую скриншот…')
    try:
        if msg.photo:
            file_id = msg.photo[-1].file_id
        elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith('image/'):
            file_id = msg.document.file_id
        else:
            return
        f = await context.bot.get_file(file_id)
        if f.file_size and f.file_size > 8_000_000:
            await msg.reply_text('🟡 ЧЕКАТИ\nЗображення завелике. Надішліть файл до 8 МБ.')
            return
        raw = bytes(await f.download_as_bytearray())
        result = await asyncio.to_thread(analyze_image, raw)
        await msg.reply_text(result)
    except Exception:
        LOG.exception('Screenshot processing error')
        await msg.reply_text('⚠️ Не вдалося прочитати зображення. Спробуйте надіслати PNG або JPG.')


def main():
    if not TOKEN:
        raise RuntimeError('Set TELEGRAM_BOT_TOKEN in environment')
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, photo))
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
