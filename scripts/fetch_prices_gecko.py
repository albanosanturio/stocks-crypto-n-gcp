import functions_framework
from google.cloud import bigquery
from datetime import datetime, timezone
import requests

PROJECT_ID = "stocks-crypto-n-gcp"
DATASET_ID = "market_data"
TABLE_ID = "prices"

# CoinGecko IDs -> symbol we want to store
COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
}

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

@functions_framework.http

def write_test_row(request):
    params = {
        "ids": ",".join(COINS.keys()),
        "vs_currencies": "usd"
    }

    resp = requests.get(COINGECKO_URL, params=params, timeout=10)

    if resp.status_code != 200:
        return (f"CoinGecko API error: {resp.status_code} {resp.text}", 502)

    data = resp.json()
    now = datetime.now(timezone.utc).isoformat()

    rows = [] 
    for coin_id, symbol in COINS.items():
        if coin_id not in data or "usd" not in data[coin_id]:
            continue
        rows.append({
            "symbol": symbol,
            "price": data[coin_id]["usd"],
            "source": "coingecko",
            "fetched_at": now
        })

    if not rows:
        return ("No valid price data received from CoinGecko", 500)

    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    errors = client.insert_rows_json(table_ref, rows)

    if errors:
        return (f"BigQuery insert errors: {errors}", 500)

    return (f"Inserted {len(rows)} rows into {table_ref}", 200)