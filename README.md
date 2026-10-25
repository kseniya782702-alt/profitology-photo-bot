# PROFITOLOGY-style Photo Bot (prototype)

Mobile-friendly Streamlit interface inspired by screenshots. Not affiliated with PROFITOLOGY or Pocket Option.

## Run
```
pip install -r requirements.txt
streamlit run app.py
```

Deploy on Streamlit Community Cloud by uploading `app.py` and `requirements.txt` to a GitHub repository, then deploying the repository. Open the URL in Android Chrome and choose Add to Home screen.

## Important limitations
The app accepts screenshots and displays them, but **does not automatically read candlesticks or generate image-derived trade signals**. It uses explicitly selected chart observations to issue conditional BUY/SELL/WAIT suggestions. It does not access Pocket Option OTC quotes or place trades. No claimed win rate or guaranteed prediction accuracy. History lasts only for the browser session.
