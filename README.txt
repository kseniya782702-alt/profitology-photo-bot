PROFITOLOGY ANALYTICS — free screenshot analyzer

1. In GitHub repository, replace bot.py with this bot.py.
2. Replace requirements.txt with the supplied requirements.txt (English file name).
3. In Render: Build Command = pip install -r requirements.txt
   Start Command = python bot.py
4. Environment: TELEGRAM_BOT_TOKEN must be set. OPENAI_API_KEY is not needed.
5. Redeploy, send a screenshot to your Telegram bot.

IMPORTANT: This free computer-vision baseline detects colored marks only. It cannot
reliably identify candles, RSI, EMA, trend or future direction and deliberately
abstains from BUY/SELL predictions. It supports screenshots from OTC and regular
Pocket Option instruments but has no access to live Pocket Option quotes.

SECURITY: Rotate any previously exposed Telegram bot token in BotFather.
HOSTING: A polling bot does not bind an HTTP port. Render Web Service may time out;
use a suitable background-worker host for reliable operation.
