from fastapi import FastAPI
from google.cloud import bigquery

app = FastAPI(title="Market Data API")
client = bigquery.Client()

LATEST_VIEW = "stocks-crypto-n-gcp.market_data.view_latest_price"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/market-snapshot")
def market_snapshot():
    query = f"SELECT symbol, category, price, fetched_at FROM `{LATEST_VIEW}`"
    rows = client.query(query).result()

    snapshot = {}
    for row in rows:
        snapshot.setdefault(row["category"], {})[row["symbol"]] = {
            "price": row["price"],
            "as_of": row["fetched_at"].isoformat(),
        }
    return snapshot