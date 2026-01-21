# App_DTCTL

Streamlit app to scrape CoinAfrique categories, download raw Web Scraper data,
and explore cleaned data in a dashboard.

## Features

- Scrape multiple pages with BeautifulSoup and clean the results.
- Download a sample Web Scraper CSV (non cleaned) or upload your own.
- View a cleaned dashboard (metrics + charts).
- Open an evaluation form (Kobo or Google Forms).

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Data notes

- Sample raw data is stored in `data/web_scraper_raw.csv`.
- Cleaned data adds `prix` (numeric) and keeps `prix_brut` (raw text).