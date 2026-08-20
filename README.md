# Stocks and crypto pipeline (GCP)

Small data pipeline running on GCP. 
Pulls crypto prices, stocks info and some macro data on a schedule and stores it in BigQuery.
Enables an API endpoint to get this condensed data and some metrics (tbd)

## What it does right now

- A Cloud Run function hits the CoinGecko API for BTC/ETH/SOL prices
- Writes the results into a BigQuery table
- Cloud Scheduler triggers it automatically (currently hourly, will drop to daily once things are stable)
- The function is locked down — no public access, only authenticated callers (like Scheduler) can trigger it


## Architecture (current)

```
CoinGecko API
      ↓
Cloud Run function (Python, HTTP-triggered)
      ↓
BigQuery (market_data.prices)
      ↑
Cloud Scheduler (hourly cron, OIDC-authenticated)
```

## Stack

- **Compute**: Cloud Run functions (Python 3.12)
- **Storage**: BigQuery
- **Scheduling**: Cloud Scheduler
- **Data source**: CoinGecko public API (crypto)

## Roadmap

- [x] CoinGecko crypto prices → BigQuery, automated
- [ ] FRED macro data (Fed funds rate, 10Y Treasury yield) → new BigQuery table
- [ ] Alpha Vantage US stock prices (note: free tier is tight — 25 req/day — so this one stays on a daily cron, not hourly)
- [ ] Rename function/service (currently a placeholder name from testing)
- [ ] FastAPI layer on Cloud Run, two endpoints to start: `/api/volatility/{symbol}`, `/api/macro-context`
- [ ] Infrastructure as code (Terraform), so the setup steps above become a file instead of a checklist

## Not in scope for v1

Dropped from the original plan to keep this shippable: web scraping (MERVAL, RIPTE), portfolio simulator endpoint, correlation matrix endpoint, web UI. All backlog — the goal right now is a clean, working, cloud-native pipeline end to end, not every feature at once.