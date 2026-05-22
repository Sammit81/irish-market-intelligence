"""
Fetch company fundamentals and analyst recommendations from Yahoo Finance.

What this collects per ticker:
  - Market cap, PE ratio, dividend yield, EPS, revenue, sector
  - Analyst recommendation consensus (buy/hold/sell counts)

Stored in Snowflake: RAW_FUNDAMENTALS
Updated daily via the refresh workflow.

Run from project root:
    uv run data_pipeline/fetch_fundamentals.py
"""
import sys
from pathlib import Path
from datetime import date

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas

sys.path.append(str(Path(__file__).parent.parent))
from data_pipeline.tickers import ALL_TICKERS
from data_pipeline.snowflake_client import get_connection

load_dotenv()


def fetch_info(ticker: str, name: str) -> dict:
    """Fetch fundamentals from yfinance .info dict."""
    try:
        t    = yf.Ticker(ticker)
        info = t.info or {}

        # Analyst recommendations — aggregate last 3 months
        try:
            recs = t.recommendations
            if recs is not None and not recs.empty:
                recent = recs.tail(3)
                strong_buy  = int(recent.get("strongBuy",  pd.Series([0])).sum())
                buy         = int(recent.get("buy",        pd.Series([0])).sum())
                hold        = int(recent.get("hold",       pd.Series([0])).sum())
                sell        = int(recent.get("sell",       pd.Series([0])).sum())
                strong_sell = int(recent.get("strongSell", pd.Series([0])).sum())
            else:
                strong_buy = buy = hold = sell = strong_sell = None
        except Exception:
            strong_buy = buy = hold = sell = strong_sell = None

        return {
            "TICKER":            ticker,
            "NAME":              name,
            "FETCH_DATE":        str(date.today()),
            "MARKET_CAP":        info.get("marketCap"),
            "PE_RATIO":          info.get("trailingPE"),
            "FORWARD_PE":        info.get("forwardPE"),
            "EPS":               info.get("trailingEps"),
            "DIVIDEND_YIELD":    info.get("dividendYield"),
            "REVENUE":           info.get("totalRevenue"),
            "PROFIT_MARGIN":     info.get("profitMargins"),
            "SECTOR":            info.get("sector"),
            "INDUSTRY":          info.get("industry"),
            "COUNTRY":           info.get("country"),
            "EMPLOYEES":         info.get("fullTimeEmployees"),
            "DESCRIPTION":       (info.get("longBusinessSummary") or "")[:500],
            "ANALYST_STRONG_BUY":  strong_buy,
            "ANALYST_BUY":         buy,
            "ANALYST_HOLD":        hold,
            "ANALYST_SELL":        sell,
            "ANALYST_STRONG_SELL": strong_sell,
        }
    except Exception as e:
        print(f"  ERROR {ticker}: {e}")
        return {"TICKER": ticker, "NAME": name, "FETCH_DATE": str(date.today())}


def main():
    print("Connecting to Snowflake...")
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS RAW_FUNDAMENTALS (
            TICKER            VARCHAR,
            NAME              VARCHAR,
            FETCH_DATE        DATE,
            MARKET_CAP        FLOAT,
            PE_RATIO          FLOAT,
            FORWARD_PE        FLOAT,
            EPS               FLOAT,
            DIVIDEND_YIELD    FLOAT,
            REVENUE           FLOAT,
            PROFIT_MARGIN     FLOAT,
            SECTOR            VARCHAR,
            INDUSTRY          VARCHAR,
            COUNTRY           VARCHAR,
            EMPLOYEES         INTEGER,
            DESCRIPTION       VARCHAR(500),
            ANALYST_STRONG_BUY  INTEGER,
            ANALYST_BUY         INTEGER,
            ANALYST_HOLD        INTEGER,
            ANALYST_SELL        INTEGER,
            ANALYST_STRONG_SELL INTEGER
        )
    """)

    rows = []
    for ticker, name in ALL_TICKERS.items():
        print(f"  Fetching {ticker:<12} {name}...", end=" ", flush=True)
        row = fetch_info(ticker, name)
        rows.append(row)
        print("done")

    df = pd.DataFrame(rows)
    df.columns = [c.upper() for c in df.columns]

    cur.execute("DELETE FROM RAW_FUNDAMENTALS WHERE FETCH_DATE = CURRENT_DATE()")

    write_pandas(conn, df, "RAW_FUNDAMENTALS", overwrite=False)
    (n,) = cur.execute("SELECT COUNT(*) FROM RAW_FUNDAMENTALS WHERE FETCH_DATE = CURRENT_DATE()").fetchone()
    print(f"\nLoaded {n} rows → RAW_FUNDAMENTALS")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
