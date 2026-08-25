import functions_framework
from google.cloud import bigquery
from datetime import datetime, timezone
import requests
import os

PROJECT_ID = "stocks-crypto-n-gcp"
DATASET_ID = "market_data"
TABLE_ID = "macro"

FRED_API_KEY = os.environ.get("FRED_API_KEY")
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

# FRED series we care about
SERIES = ["FEDFUNDS", "DGS10"]

@functions_framework.http
def fetch_macro_fred(request):
    if not FRED_API_KEY:
        return ("Missing FRED_API_KEY environment variable", 500)

    now = datetime.now(timezone.utc).isoformat()
    rows = []

    for series_id in SERIES:
        params = {
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1  # just the most recent observation
        }

        resp = requests.get(FRED_URL, params=params, timeout=10)

        if resp.status_code != 200:
            return (f"FRED API error for {series_id}: {resp.status_code} {resp.text}", 502)

        data = resp.json()
        observations = data.get("observations", [])

        if not observations:
            continue

        latest = observations[0]
        value_str = latest.get("value")

        # FRED uses "." for missing data points
        if value_str is None or value_str == ".":
            continue

        rows.append({
            "series_id": series_id,
            "value": float(value_str),
            "source": "fred",
            "fetched_at": now
        })

    if not rows:
        return ("No valid macro data received from FRED", 500)

    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    errors = client.insert_rows_json(table_ref, rows)

    if errors:
        return (f"BigQuery insert errors: {errors}", 500)

    return (f"Inserted {len(rows)} rows into {table_ref}", 200)