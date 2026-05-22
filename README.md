# Irish Market Intelligence Dashboard

A live financial markets dashboard tracking 28 assets across Irish, European, and US markets. Data is pulled daily from Yahoo Finance, stored and transformed in Snowflake via dbt, and served through a Streamlit web app.

**Live dashboard**: [irish-market-intelligence.streamlit.app](https://irish-market-intelligence-ngkorhtqqvlho8qdmrsqfs.streamlit.app)

---

## What makes this different from static portfolio projects

The data updates automatically every 6 hours via GitHub Actions (00:00, 06:00, 12:00, 18:00 UTC). The pipeline fetches fresh prices from Yahoo Finance, loads them into Snowflake, runs the dbt transformation layer, and the dashboard reflects current market conditions without any manual work. This is what a production analytics pipeline looks like at a smaller scale.

---

## Architecture

```
Yahoo Finance (yfinance)
    │  Fetches OHLCV prices daily for 28 tickers
    ▼
Snowflake — RAW_PRICES
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
| **Snowflake** | Cloud warehouse | Industry standard in Dublin. Native Streamlit connector, scales without configuration. |
| **dbt** | Transformation | Replaces manual SQL scripts. Manages dependencies, enables testing, generates lineage documentation. Every mart is a tested, documented model. |
| **Streamlit** | Web app | Write Python, get an interactive web app. Free deployment on Streamlit Cloud with a permanent public URL. |
| **GitHub Actions** | Automation | Scheduled workflow runs `fetch_prices.py` + `dbt run` every 6 hours. No manual work needed to keep data current. |

---

## Setup (run locally)

**Prerequisites**: Python 3.9+, `uv`, Snowflake account, Kaggle account (for dataset).

```bash
# Install dependencies
uv sync

# Configure credentials
cp .env.example .env
# Fill in SNOWFLAKE_* values in .env

# Create FINANCIAL_MARKETS database in Snowflake, then:
uv run data_pipeline/fetch_prices.py   # load 2 years of price history

# Run dbt models
cd dbt_project
dbt run

# Launch dashboard locally
cd ..
uv run streamlit run streamlit_app/app.py
```

Open `http://localhost:8501`.

---

## What I'd Do Next

- **dbt tests**: add schema tests (`not_null`, `unique`, `accepted_values`) to catch data quality issues automatically before they reach the dashboard
- **Price alerts**: email or Slack notification when any Irish stock moves >5% in a day
- **Portfolio tracker**: let users input their own holdings and track P&L against current prices
- **dbt documentation**: run `dbt docs generate` and host the lineage graph — shows the full dependency chain from raw data to dashboard
- **More Irish coverage**: add options data and short interest for Irish stocks to surface sentiment signals
