# Stocks and crypto pipeline (GCP)

Small data pipeline running on GCP. 
Pulls crypto prices, stocks info and some macro data on a schedule and stores it in BigQuery.
Enables an API endpoint to get this condensed data and some metrics (tbd)

## What it does right now

- Cloud Run functions hit CoinGecko (BTC/ETH/SOL), Alpha Vantage (SPY/QQQ/DIA), and FRED (Fed funds rate, 10Y Treasury) on a schedule
- Writes results into BigQuery tables (`prices`, `stocks`, `macro`)
- Cloud Scheduler triggers each one automatically (daily)
- All functions are locked down — no public access, only authenticated callers (like Scheduler) can trigger them
- ~100 days of history backfilled per source via one-time local scripts


## Architecture (current)

```
CoinGecko / Alpha Vantage / FRED APIs
      ↓
Cloud Run functions (Python, HTTP-triggered)
      ↓
BigQuery (market_data.prices / .stocks / .macro)
      ↑
Cloud Scheduler (daily cron, OIDC-authenticated)
```

## Stack

- **Compute**: Cloud Run functions (Python 3.12)
- **Storage**: BigQuery
- **Scheduling**: Cloud Scheduler
- **Data sources**: CoinGecko (crypto), Alpha Vantage (stocks), FRED (macro)

## Roadmap

- [x] CoinGecko crypto prices → BigQuery, automated
- [x] FRED macro data (Fed funds rate, 10Y Treasury yield) → BigQuery
- [x] Alpha Vantage US stock prices → BigQuery (free tier tight — 25 req/day — stays on daily cron)
- [x] Historical backfill (~100 days) for all three sources
- [ ] Rename function/service (currently a placeholder name from testing)
- [ ] FastAPI layer on Cloud Run, two endpoints to start: `/api/volatility/{symbol}`, `/api/market-snapshot`
- [ ] Looker Studio dashboard (scorecards + time-series), published public
- [ ] Infrastructure as code (Terraform), so the setup steps above become a file instead of a checklist

## Not in scope for v1

Dropped from the original plan to keep this shippable: web scraping (MERVAL, RIPTE), portfolio simulator endpoint, correlation matrix endpoint, web UI. All backlog — the goal right now is a clean, working, cloud-native pipeline end to end, not every feature at once.