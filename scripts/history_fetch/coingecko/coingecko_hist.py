"""
One-time local backfill script.
Fetches ~100 days of historical daily prices for BTC, ETH, SOL from
CoinGecko and writes them to a CSV in the long format expected by
BigQuery's market_data.prices table (symbol, price, source, fetched_at),
ready for staging + review before merging into the main table.

CoinGecko's market_chart endpoint returns multiple price points per day
for short ranges (roughly hourly). Since the project's data granularity
is daily, this script collapses each day down to a single price (the
last observed price for that calendar day) before writing the CSV.

Run once. Not deployed as a Cloud Function.
"""

import requests
import csv
import time
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/{id}/market_chart"
COINGECKO_API_KEY = os.environ.get("COINGECKO_API_KEY")  # optional -- see note below

# CoinGecko IDs -> symbol we want to store (matches the live function's mapping)
COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
}

DAYS = 100
CSV_OUTPUT_FILE = "./scripts/history_fetch/coingecko/coingecko_history.csv"


def fetch_history(coin_id, symbol):
    url = COINGECKO_URL.format(id=coin_id)
    params = {
        "vs_currency": "usd",
        "days": DAYS,
        # No 'interval' param needed: CoinGecko auto-returns daily
        # granularity (00:00 UTC) for any range above 90 days on the
        # free/demo tier. The 'interval' override is documented but not
        # honored on this tier, so days=100 already gives us exactly
        # what we want -- one price point per day.
    }
    headers = {}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY

    resp = requests.get(url, params=params, headers=headers, timeout=15)

    if resp.status_code != 200:
        print(f"WARNING: CoinGecko API error for {symbol}: {resp.status_code} {resp.text}")
        return []

    data = resp.json()
    raw_prices = data.get("prices", [])  # list of [timestamp_ms, price], already ~1/day

    if not raw_prices:
        print(f"WARNING: no price data for {symbol}")
        return []

    rows = []
    for timestamp_ms, price in raw_prices:
        date_str = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        fetched_at = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=12, tzinfo=timezone.utc
        ).isoformat()

        rows.append({
            "symbol": symbol,
            "price": float(price),
            "source": "coingecko-historical",
            "fetched_at": fetched_at
        })

    return rows


def write_csv(all_rows):
    sorted_rows = sorted(all_rows, key=lambda r: r["fetched_at"], reverse=True)

    print(f"Writing {len(sorted_rows)} rows to {CSV_OUTPUT_FILE}...")

    with open(CSV_OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["symbol", "price", "source", "fetched_at"])
        writer.writeheader()
        writer.writerows(sorted_rows)

    print("CSV written.")


def main():
    all_rows = []
    for i, (coin_id, symbol) in enumerate(COINS.items()):
        if i > 0:
            time.sleep(2)  # be polite between calls, CoinGecko's free tier is generous but not unlimited

        print(f"Fetching history for {symbol}...")
        rows = fetch_history(coin_id, symbol)
        print(f"  -> {len(rows)} days retrieved")
        all_rows.extend(rows)

    if not all_rows:
        print("No rows to write. Exiting.")
        return

    write_csv(all_rows)

    print(f"\nWould write {len(all_rows)} total rows.")
    print("Sample rows:")
    for row in all_rows[:5]:
        print(row)


if __name__ == "__main__":
    main()