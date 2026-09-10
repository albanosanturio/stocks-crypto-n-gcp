"""
One-time local backfill script.
Fetches ~100 days of historical daily observations for FEDFUNDS and
DGS10 from FRED and writes them to a CSV in the long format expected
by BigQuery's market_data.macro table (series_id, value, source,
fetched_at), ready for staging + review before merging into the main
table.

Note: FRED series are not all published daily -- FEDFUNDS is monthly,
DGS10 is daily (business days only, with holidays as "." missing
values). This script keeps whatever FRED actually returns; it does not
attempt to forward-fill gaps.

Run once. Not deployed as a Cloud Function.
"""

import requests
import csv
import time
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

FRED_API_KEY = os.environ.get("FRED_API_KEY")
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

SERIES = ["FEDFUNDS", "DGS10"]

DAYS = 100
CSV_OUTPUT_FILE = "./scripts/history_fetch/fred/fred_history.csv"

if not FRED_API_KEY:
    raise RuntimeError("Set FRED_API_KEY as an environment variable before running.")


def fetch_history(series_id):
    start_date = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%Y-%m-%d")

    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "asc",
        "observation_start": start_date,
    }

    resp = requests.get(FRED_URL, params=params, timeout=15)

    if resp.status_code != 200:
        print(f"WARNING: FRED API error for {series_id}: {resp.status_code} {resp.text}")
        return []

    data = resp.json()
    observations = data.get("observations", [])

    rows = []
    for obs in observations:
        value_str = obs.get("value")
        date_str = obs.get("date")

        # FRED uses "." for missing/not-yet-published data points
        if value_str is None or value_str == "." or not date_str:
            continue

        fetched_at = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=12, tzinfo=timezone.utc
        ).isoformat()

        rows.append({
            "series_id": series_id,
            "value": float(value_str),
            "source": "fred-historical",
            "fetched_at": fetched_at
        })

    return rows


def write_csv(all_rows):
    sorted_rows = sorted(all_rows, key=lambda r: r["fetched_at"], reverse=True)

    print(f"Writing {len(sorted_rows)} rows to {CSV_OUTPUT_FILE}...")

    with open(CSV_OUTPUT_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["series_id", "value", "source", "fetched_at"])
        writer.writeheader()
        writer.writerows(sorted_rows)

    print("CSV written.")


def main():
    all_rows = []
    for i, series_id in enumerate(SERIES):
        if i > 0:
            time.sleep(1)

        print(f"Fetching history for {series_id}...")
        rows = fetch_history(series_id)
        print(f"  -> {len(rows)} observations retrieved")
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