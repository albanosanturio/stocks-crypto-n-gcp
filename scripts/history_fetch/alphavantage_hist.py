"""
One-time local backfill script.
Fetches ~100 days of historical daily closes for SPY, QQQ, DIA from
Alpha Vantage and inserts them into BigQuery's market_data.stocks table.

Run once. Not deployed as a Cloud Function.
"""

import requests
import csv
import time
import os
from datetime import datetime, timezone
#from google.cloud import bigquery
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")  # adjust path to wherever it actually is

PROJECT_ID = "stocks-crypto-n-gcp"
DATASET_ID = "market_data"
TABLE_ID = "stocks"

ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY")
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

TICKERS = ["SPY", "QQQ", "DIA"]

CSV_OUTPUT_FILE = "alphavantage_history_qa.csv"

if not ALPHA_VANTAGE_KEY:
    raise RuntimeError("Set ALPHA_VANTAGE_KEY as an environment variable before running.")


def fetch_history(symbol):
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "compact",  # ~100 trading days
        "apikey": ALPHA_VANTAGE_KEY
    }
    resp = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    time_series = data.get("Time Series (Daily)")
    if not time_series:
        print(f"WARNING: no data for {symbol}. Response: {data}")
        return []

    rows = []
    for date_str, values in time_series.items():
        close_price = values.get("4. close")
        if close_price is None:
            continue

        # Use midday UTC as a stand-in timestamp for the trading day
        fetched_at = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=12, tzinfo=timezone.utc
        ).isoformat()

        rows.append({
            "symbol": symbol,
            "price": float(close_price),
            "source": "alphavantage-historical",
            "fetched_at": fetched_at
        })

    return rows

def write_csv(all_rows):
    """
    Pivots the flat row list (one row per symbol+date) into one row per
    date with a column per ticker, and writes it to CSV for QA in a
    spreadsheet before loading into BigQuery.
    """
    # date -> {symbol: price}
    by_date = {}
    for row in all_rows:
        date_str = row["fetched_at"][:10]  # just the date part, e.g. "2026-09-08"
        by_date.setdefault(date_str, {})[row["symbol"]] = row["price"]
 
    sorted_dates = sorted(by_date.keys(), reverse=True)
 
    print(f"Writing {len(sorted_dates)} rows to {CSV_OUTPUT_FILE}...")
 
    with open(CSV_OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date"] + TICKERS)
 
        for date_str in sorted_dates:
            row = [date_str]
            for symbol in TICKERS:
                row.append(by_date[date_str].get(symbol, ""))
            writer.writerow(row)
 
    print("CSV written.")

def main():
    #client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    all_rows = []
    for i, symbol in enumerate(TICKERS):
        if i > 0:
            time.sleep(1)  # respect Alpha Vantage's 1 req/sec limit

        print(f"Fetching history for {symbol}...")
        rows = fetch_history(symbol)
        print(f"  -> {len(rows)} days retrieved")
        all_rows.extend(rows)

    if not all_rows:
        print("No rows to insert. Exiting.")
        return

    write_csv(all_rows)
    
#    print(f"Inserting {len(all_rows)} total rows into {table_ref}...")
#    errors = client.insert_rows_json(table_ref, all_rows)
#
#    if errors:
#        print(f"BigQuery insert errors: {errors}")
#    else:
#        print("Done. Inserted successfully.")

    print(f"Would insert {len(all_rows)} total rows into {table_ref}")
    print("Sample rows:")
    for row in all_rows[:5]:
        print(row)


if __name__ == "__main__":
    main()