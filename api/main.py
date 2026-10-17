import math
from datetime import date, timedelta

from pathlib import Path
from fastapi.responses import HTMLResponse

from fastapi import FastAPI, HTTPException, Query
from google.cloud import bigquery

app = FastAPI(title="Market Data API")
client = bigquery.Client()
LANDING_HTML = (Path(__file__).parent / "landing.html").read_text(encoding="utf-8")

LATEST_VIEW = "stocks-crypto-n-gcp.market_data.view_latest_price"
RETURNS_VIEW = "stocks-crypto-n-gcp.market_data.view_daily_returns"

VALID_SYMBOLS = {"BTC", "ETH", "SOL", "SPY", "QQQ", "DIA"}
# Crypto trades every day, stocks only on ~252 trading days a year
ANNUALIZATION_DAYS = {"crypto": 365, "stock": 252}

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing():
    return LANDING_HTML

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


@app.get("/api/volatility/{symbol}")
def volatility(symbol: str, days: int = Query(30, ge=1, le=365)):
    symbol = symbol.upper()
    if symbol not in VALID_SYMBOLS:
        raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")

    query = f"""
        SELECT
          ANY_VALUE(category) AS category,
          COUNT(daily_return) AS n_returns,
          STDDEV(daily_return) AS daily_vol,
          MIN(price) AS price_min,
          MAX(price) AS price_max,
          MIN(day) AS start_day,
          MAX(day) AS end_day,
          ARRAY_AGG(price ORDER BY day ASC LIMIT 1)[OFFSET(0)] AS first_price,
          ARRAY_AGG(price ORDER BY day DESC LIMIT 1)[OFFSET(0)] AS last_price
        FROM `{RETURNS_VIEW}`
        WHERE symbol = @symbol
          AND day > DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("symbol", "STRING", symbol),
            bigquery.ScalarQueryParameter("days", "INT64", days),
        ]
    )
    row = list(client.query(query, job_config=job_config).result())[0]

    if row["start_day"] is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol} in the last {days} days")

    factor = ANNUALIZATION_DAYS[row["category"]]
    daily_vol = row["daily_vol"]  # None when there are fewer than 2 returns
    annualized = daily_vol * math.sqrt(factor) if daily_vol is not None else None

    notes = []
    if daily_vol is None:
        notes.append("Not enough data points to compute volatility.")
    window_start = date.today() - timedelta(days=days - 1)
    if (row["start_day"] - window_start).days > 4:
        notes.append(f"History starts on {row['start_day'].isoformat()}, so fewer than {days} days were available.")

    return {
        "symbol": symbol,
        "category": row["category"],
        "days_requested": days,
        "start_date": row["start_day"].isoformat(),
        "end_date": row["end_day"].isoformat(),
        "n_returns": row["n_returns"],
        "daily_volatility": round(daily_vol, 6) if daily_vol is not None else None,
        "annualized_volatility": round(annualized, 6) if annualized is not None else None,
        "annualization_days": factor,
        "price_min": round(row["price_min"], 2),
        "price_max": round(row["price_max"], 2),
        "price_change": round(row["last_price"] / row["first_price"] - 1, 6),
        "note": " ".join(notes) if notes else None,
    }