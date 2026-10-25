"""PROFITOLOGY ANALYTICS: screenshot analysis for Pocket Option charts."""
import asyncio
import base64
import logging
import os
from io import BytesIO

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
MODEL = os.environ.get('VISION_MODEL', 'gpt-4.1-mini')
PROMPT = '''Проаналізуй надісланий скриншот торгового графіка Pocket Option українською.
Поверни стислий звіт у форматі:
📊 Актив: [назва або не видно]
⏱ Таймфрейм: [або не видно]
📈 Тренд: [висхідний/спадний/боковий/невизначений]
🔎 Спостереження: [2-4 конкретні ознаки, які справді видно: свічки, середні, рівні, індикатори]
🎯 Оцінка: 🟢 BUY / 🔴 SELL / 🟡 WAIT
📝 Пояснення: [1-2 речення]

Важливо: це оцінка статичного зображення, не прогноз у реальному часі. Не вигадуй чисел,
індикаторів або відсотків упевненості. Якщо сигнал неоднозначний, графік погано видно,
свічка незакрита або недостатньо даних — WAIT. Не обіцяй прибуток.
Наприкінці додай: «⚠️ Скриншот не гарантує напрямку наступної свічки. OTC має високий ризик.»'''


def analyze_image(image_bytes: bytes) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError('OPENAI_API_KEY is not configured')
    encoded = base64.b64encode(image_bytes).decode('ascii')
    payload = {
        'model': MODEL,
        'max_tokens': 550,
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': PROMPT},
            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{encoded}', 'detail': 'high'}}
        ]}]
    }
    response = requests.post('https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type': 'application/json'},
        json=payload, timeout=75)
    if not response.ok:
        LOG.error('Vision API status: %s', response.status_code)
        raise RuntimeError(f'Vision API HTTP {response.status_code}')
    return response.json()['choices'][0]['message']['content']


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('📸 PROFITOLOGY ANALYTICS\nНадішліть скриншот графіка Pocket Option як фото або файл. Я автоматично підготую технічну оцінку.')


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    await msg.reply_text('🔎 Аналізую зображення, зачекайте...')
    try:
        if msg.photo:
            file = await msg.photo[-1].get_file()
        elif msg.document and msg.document.mime_type in ('image/jpeg', 'image/png', 'image/webp'):
            if msg.document.file_size and msg.document.file_size > 8_000_000:
                await msg.reply_text('⚠️ Файл завеликий. Надішліть зображення до 8 МБ.')
                return
            file = await msg.document.get_file()
        else:
            await msg.reply_text('Надішліть зображення JPG, PNG або WebP.')
            return
        buf = BytesIO()
        await file.download_to_memory(out=buf)
        raw = buf.getvalue()
        if len(raw) > 8_000_000:
            await msg.reply_text('⚠️ Зображення завелике. Стисніть його до 8 МБ.')
            return
        # Telegram photos are JPEG; files may be PNG/WebP, whose MIME type is passed through.
        if msg.document and msg.document.mime_type != 'image/jpeg':
            from PIL import Image
            image = Image.open(BytesIO(raw)).convert('RGB')
            output = BytesIO()
            image.save(output, format='JPEG', quality=88)
            raw = output.getvalue()
        result = await asyncio.to_thread(analyze_image, raw)
        await msg.reply_text(result[:4000])
    except Exception as exc:
        LOG.warning('Screenshot analysis failed: %s', type(exc).__name__)
        await msg.reply_text('⚠️ Не вдалося проаналізувати зображення. Перевірте налаштування API та журнал Render.')


def main():
    if not TOKEN:
        raise RuntimeError('Missing TELEGRAM_BOT_TOKEN')
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, photo))
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
