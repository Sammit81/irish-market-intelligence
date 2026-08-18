# Irish Market Intelligence Dashboard

A live financial markets dashboard tracking 28 assets across Irish, European, and US markets. Data is pulled daily from Yahoo Finance, stored and transformed in BigQuery via dbt, and served through a Streamlit web app.

**Live dashboard**: [irish-market-intelligence.streamlit.app](https://irish-market-intelligence-ngkorhtqqvlho8qdmrsqfs.streamlit.app)

---

## What makes this different from static portfolio projects

The data updates automatically every 6 hours via GitHub Actions (00:00, 06:00, 12:00, 18:00 UTC). The pipeline fetches fresh prices from Yahoo Finance, loads them into BigQuery, runs the dbt transformation layer, and the dashboard reflects current market conditions without any manual work. This is what a production analytics pipeline looks like at a smaller scale.

---

## Architecture

```
Yahoo Finance (yfinance)
    │  Fetches OHLCV prices daily for 28 tickers
    ▼
BigQuery — RAW_PRICES
    │  One row per ticker per trading day
    ▼
dbt transformation layer
    │   stg_prices           — clean and type-cast raw data (view)
    │   int_daily_returns    — daily returns, log returns, 7d/30d MA,
    │                          rolling 30d volatility (view)
    │   fct_market_summary   — one row per ticker, latest price,
    │                          YTD return, 52-week high/low (table)
    │   fct_returns_history  — full price history with cumulative
    │                          returns for charting (table)
    ▼
Streamlit — 4-page web app
    │   Market Overview      — KPI tiles, movers chart, quick chart
    │   Stock Deep Dive      — candlestick, volume, Sharpe ratio
    │   Compare Assets       — normalised growth, risk vs return
    │   Risk Analysis        — volatility ranking, correlation heatmap
```

---

## Assets Tracked

**Irish Market (ISEQ)**

| Ticker | Company |
|--------|---------|
| CRH | CRH (NYSE primary listing) |
| A5G.IR | AIB Group |
| BIRG.IR | Bank of Ireland |
| RYA.IR | Ryanair |
| KYGA.L | Kerry Group |
| FLTR.L | Flutter Entertainment |
| SKG.L | Smurfit Kappa |
| KRX.IR | Kingspan Group |
| GL9.IR | Glanbia |
| GNC.L | Greencore |
| GFTU.L | Grafton Group |
| DPLM.L | Diploma |
| C5H.IR | Cairn Homes |
| IR5B.IR | Irish Continental Group |

**Global Indices**: S&P 500 · FTSE 100 · Euro Stoxx 50 · NASDAQ

**Dublin Tech**: Alphabet · Meta · Microsoft · Apple · Amazon

**ETFs**: SPY · QQQ · VWRL · CSPX

---

## Dashboard Pages

### Market Overview
Live KPI tiles for the 4 major indices. Full asset table with daily return, YTD return, and 30-day volatility. Today's movers bar chart. Quick price chart with 30-day moving average for any selected asset.

### Stock Deep Dive
Candlestick chart (OHLC) with volume bars and moving average overlays. Key metrics: Sharpe ratio, max drawdown, period return, volatility. Daily return distribution histogram showing the spread of gains and losses.

### Compare Assets
Normalised growth chart — all assets start at 100 so performance is directly comparable regardless of price. Head-to-head metrics table. Risk vs. return scatter plot.

### Risk Analysis
Colour-coded volatility ranking (🟢 Low / 🟡 Medium / 🔴 High). Correlation heatmap showing how assets move together — useful for understanding diversification. Rolling 30-day volatility over time.

---

## Tech Stack

| Tool | Role | Why |
|------|------|-----|
| **yfinance** | Data source | Free Yahoo Finance API, no key needed. Incremental loads — only fetches new data on each run. |
| **BigQuery** | Cloud warehouse | Google's flagship data warehouse — heavily used across Dublin's data teams (Google's European HQ is here). Always-free tier (1TB queries/month, 10GB storage), no trial expiry. |
| **dbt** | Transformation | Replaces manual SQL scripts. Manages dependencies, enables testing, generates lineage documentation. Every mart is a tested, documented model. |
| **Streamlit** | Web app | Write Python, get an interactive web app. Free deployment on Streamlit Cloud with a permanent public URL. |
| **GitHub Actions** | Automation | Scheduled workflow runs `fetch_prices.py` + `dbt run` every 6 hours. No manual work needed to keep data current. |

---

## Setup (run locally)

**Prerequisites**: Python 3.9+, `uv`, a Google Cloud project with BigQuery enabled.

```bash
# Install dependencies
uv sync

# Configure credentials
cp .env.example .env
# Fill in GCP_PROJECT_ID, BQ_DATASET, and GOOGLE_APPLICATION_CREDENTIALS in .env
# (GOOGLE_APPLICATION_CREDENTIALS points at your service account JSON key file)

uv run data_pipeline/fetch_prices.py   # load 2 years of price history
uv run data_pipeline/fetch_fundamentals.py

# Run dbt models — dbt doesn't read .env automatically, so export the vars first
# and point it at the profiles.yml checked into dbt_project/ (not the ~/.dbt default)
export $(grep -v '^#' .env | xargs) DBT_PROFILES_DIR=./dbt_project
cd dbt_project && dbt run && dbt test && cd ..

# Launch dashboard locally
uv run streamlit run streamlit_app/app.py
```

Open `http://localhost:8501`.

### One-time GCP setup

1. Create a GCP project at [console.cloud.google.com](https://console.cloud.google.com) and enable the **BigQuery API**.
2. Create a BigQuery dataset named `FINANCIAL_MARKETS` (Data set location: `EU`).
3. Create a service account (**IAM & Admin → Service Accounts**) with the **BigQuery Data Editor** and **BigQuery Job User** roles, then create a JSON key for it and download it as `gcp-key.json` in the project root (already gitignored).
   - If key creation is blocked by an org policy (`iam.disableServiceAccountKeyCreation` / `iam.managed.disableServiceAccountKeyCreation` — common on new free-trial projects), override both the legacy **and** managed versions of that constraint to "Not enforced" under **IAM & Admin → Organization Policies** for the project.
4. Set `GCP_PROJECT_ID`, `BQ_DATASET=FINANCIAL_MARKETS`, and `GOOGLE_APPLICATION_CREDENTIALS=./gcp-key.json` in `.env`.

**Note on column casing**: unlike Snowflake, BigQuery doesn't auto-uppercase unquoted identifiers, and dbt's table materialization doesn't reliably honor case-only rename aliases (e.g. `ticker AS TICKER` can silently stay lowercase in the materialized table). `streamlit_app/connection.py` normalises every result set to uppercase columns after querying — if you add a new query path that bypasses that adapter, either route it through `connection.py` or uppercase the resulting DataFrame's columns yourself.

---

## What I'd Do Next

- **More Irish coverage**: add options data and short interest for Irish stocks to surface sentiment signals
- **Smurfit Kappa ticker**: `SKG.L` stopped returning data after the 2024 WestRock merger (now trades as Smurfit WestRock) — swap to the new ticker to restore full 28-asset coverage
- **Test coverage on `int_daily_returns`**: the intermediate layer has no schema tests yet; the marts built on top of it do
- **Automated pipeline alerting**: GitHub Actions shows failures in the Actions tab, but nothing pushes a notification if a scheduled run fails silently overnight

**Already shipped** (moved out of this list as the project grew): dbt schema tests on every mart, price alerts on >5% daily moves, the portfolio tracker page, and hosted dbt docs via GitHub Pages — all live in the codebase, not just planned.
