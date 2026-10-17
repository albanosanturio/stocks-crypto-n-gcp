# Stocks and crypto pipeline (GCP)

Small data pipeline on GCP. It pulls crypto prices, stock prices and some macro data every day, stores them in BigQuery, and serves them through a public API and a dashboard.

Live: https://market-data-api-621108396421.us-central1.run.app (landing page with the dashboard, `/docs` for the API)

This is a portfolio project built to practice GCP (Cloud Run, BigQuery, Cloud Scheduler, IAM). Nobody depends on it and it is not financial advice.

## What it does

- Three Cloud Run functions call CoinGecko (BTC/ETH/SOL), Alpha Vantage (SPY/QQQ/DIA) and FRED (Fed funds rate, 10Y Treasury) once a day and write to BigQuery (`prices`, `stocks`, `macro`)
- Cloud Scheduler triggers each function with an OIDC token. The functions are private, only authenticated callers can trigger them
- About 100 days of history were backfilled per source with one-time local scripts (fetch to CSV, load to a staging table, merge)
- SQL views sit on top of the tables and feed both the dashboard and the API
- A FastAPI service on Cloud Run serves two endpoints and a landing page with the embedded Data Studio dashboard

## Architecture

```
CoinGecko, Alpha Vantage, FRED
            |
Cloud Scheduler --> Cloud Run functions (Python)
            |
BigQuery (prices, stocks, macro) --> SQL views
                                        |
                          +-------------+-------------+
                          |                           |
                 Data Studio dashboard       FastAPI on Cloud Run
```

## API

`GET /api/market-snapshot`: latest price per symbol, grouped by category.

`GET /api/volatility/{symbol}?days=30`: daily and annualized volatility, price range and price change over the last N days (1 to 365). Valid symbols: BTC, ETH, SOL, SPY, QQQ, DIA.

Annualization uses 365 days for crypto and 252 for stocks. The response includes the number of returns used and the real start and end dates, with a note when there is less history than requested.

The service is public but read only. It runs as its own service account with query access to the `market_data` dataset and nothing else, user input is passed as query parameters and checked against the symbol list, and max instances is capped to limit cost.

## Stack

Cloud Run (functions and service), BigQuery, Cloud Scheduler, Data Studio (formerly Looker Studio), FastAPI, Python 3.12.

## Things that broke

- **Silent outage.** After renaming the crypto service, the Scheduler job still had the old service URL as its OIDC audience, so every call got a 401 before reaching the code. No crypto data between Aug 26 and Oct 14. The audience has to match the target URL. This is why a Slack alert is on the roadmap.
- **Duplicate rows.** During testing the crypto job ran on an hourly cron, which gave 24 rows per symbol per day for a week. Fixed with a window function into a staging table, checked, then swapped in.
- **Weekend stock rows.** The stocks job runs daily and stores ingestion time, so Saturday and Sunday repeat Friday's close. That understated SPY's volatility by about 16%. The returns view now keeps only weekdays for stocks.
- **Container crashes on startup.** A missing library and a missing import each crashed the service. Cloud Run reports both as "failed to listen on the port", and the real error is in the stderr log.
- **CoinGecko current day.** The current day comes back at finer than daily granularity, so the backfill dedupes by date.

## Known limitations

- Market holidays still show up as zero-return days for stocks
- Macro data is collected but not in the API or dashboard yet, and the FRED history has not been deduplicated
- Volatility describes the past window only, it is not a forecast
- The first request after a quiet period takes a few seconds (cold start)

## Roadmap

- [x] CoinGecko crypto prices to BigQuery, automated
- [x] FRED macro data to BigQuery
- [x] Alpha Vantage stock prices to BigQuery (free tier is 25 requests/day, so it stays on a daily cron)
- [x] Historical backfill (~100 days) for all three sources
- [x] Rename the placeholder service
- [x] FastAPI layer with `/api/market-snapshot` and `/api/volatility/{symbol}`
- [x] Dashboard, published public
- [ ] Slack alert when a day's data is missing
- [ ] CoinGecko API key (the endpoint works without one for now)
- [ ] Dedupe FRED history
- [ ] Returns endpoint, and a comparison chart that can be re-indexed to any start date
- [ ] Secret Manager for API keys

## Not in scope for v1

Everything was set up by hand in the console to keep the MVP small. Terraform is the first thing I would add. Also left out: MERVAL/RIPTE/ARS-USD scraping, portfolio simulator, correlation matrix, full web UI.