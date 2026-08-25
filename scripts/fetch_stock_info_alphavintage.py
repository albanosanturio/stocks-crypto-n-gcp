import functions_framework
from google.cloud import bigquery
from datetime import datetime, timezone
import requests
import time
import os

PROJECT_ID = "stocks-crypto-n-gcp"
DATASET_ID = "market_data"
TABLE_ID = "stocks"

ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY")
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

# Keep this short — free tier is 25 requests/day total
TICKERS = ["SPY", "QQQ", "DIA"]

@functions_framework.http
def fetch_stock_info_alphavantage(request):
    if not ALPHA_VANTAGE_KEY:
        return ("Missing ALPHA_VANTAGE_KEY environment variable", 500)

    now = datetime.now(timezone.utc).isoformat()
    rows = []

    for symbol in TICKERS:
        time.sleep(1)
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_KEY
        }

        resp = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=10)

        if resp.status_code != 200:
            return (f"Alpha Vantage API error for {symbol}: {resp.status_code} {resp.text}", 502)

        data = resp.json()
        quote = data.get("Global Quote", {})
        price_str = quote.get("05. price")

        # Alpha Vantage returns an empty dict (not an error) if rate-limited
        if not price_str:
            return (f"No price data for {symbol} — possibly rate-limited. Response: {data}", 429)

        rows.append({
            "symbol": symbol,
            "price": float(price_str),
            "source": "alphavantage",
            "fetched_at": now
        })

    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    errors = client.insert_rows_json(table_ref, rows)

    if errors:
        return (f"BigQuery insert errors: {errors}", 500)

    return (f"Inserted {len(rows)} rows into {table_ref}", 200)