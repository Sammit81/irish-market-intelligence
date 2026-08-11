"""
Fetch company fundamentals and analyst recommendations from Yahoo Finance.

What this collects per ticker:
  - Market cap, PE ratio, dividend yield, EPS, revenue, sector
  - Analyst recommendation consensus (buy/hold/sell counts)

Stored in BigQuery: RAW_FUNDAMENTALS
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
from google.cloud import bigquery

sys.path.append(str(Path(__file__).parent.parent))
from data_pipeline.tickers import ALL_TICKERS
from data_pipeline.bigquery_client import get_connection, table_ref

load_dotenv()

TABLE_NAME = "RAW_FUNDAMENTALS"


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
    print("Connecting to BigQuery...")
    client = get_connection()

    client.query(f"""
        CREATE TABLE IF NOT EXISTS {table_ref(TABLE_NAME)} (
            TICKER            STRING,
            NAME              STRING,
            FETCH_DATE        DATE,
            MARKET_CAP        FLOAT64,
            PE_RATIO          FLOAT64,
            FORWARD_PE        FLOAT64,
            EPS               FLOAT64,
            DIVIDEND_YIELD    FLOAT64,
            REVENUE           FLOAT64,
            PROFIT_MARGIN     FLOAT64,
            SECTOR            STRING,
            INDUSTRY          STRING,
            COUNTRY           STRING,
            EMPLOYEES         INTEGER,
            DESCRIPTION       STRING,
            ANALYST_STRONG_BUY  INTEGER,
            ANALYST_BUY         INTEGER,
            ANALYST_HOLD        INTEGER,
            ANALYST_SELL        INTEGER,
            ANALYST_STRONG_SELL INTEGER
        )
    """).result()

    rows = []
    for ticker, name in ALL_TICKERS.items():
        print(f"  Fetching {ticker:<12} {name}...", end=" ", flush=True)
        row = fetch_info(ticker, name)
        rows.append(row)
        print("done")

    df = pd.DataFrame(rows)
    df.columns = [c.upper() for c in df.columns]
    df["FETCH_DATE"] = pd.to_datetime(df["FETCH_DATE"]).dt.date

    client.query(f"DELETE FROM {table_ref(TABLE_NAME)} WHERE FETCH_DATE = CURRENT_DATE()").result()

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        schema=[
            bigquery.SchemaField("TICKER", "STRING"),
            bigquery.SchemaField("NAME", "STRING"),
            bigquery.SchemaField("FETCH_DATE", "DATE"),
            bigquery.SchemaField("MARKET_CAP", "FLOAT64"),
            bigquery.SchemaField("PE_RATIO", "FLOAT64"),
            bigquery.SchemaField("FORWARD_PE", "FLOAT64"),
            bigquery.SchemaField("EPS", "FLOAT64"),
            bigquery.SchemaField("DIVIDEND_YIELD", "FLOAT64"),
            bigquery.SchemaField("REVENUE", "FLOAT64"),
            bigquery.SchemaField("PROFIT_MARGIN", "FLOAT64"),
            bigquery.SchemaField("SECTOR", "STRING"),
            bigquery.SchemaField("INDUSTRY", "STRING"),
            bigquery.SchemaField("COUNTRY", "STRING"),
            bigquery.SchemaField("EMPLOYEES", "INTEGER"),
            bigquery.SchemaField("DESCRIPTION", "STRING"),
            bigquery.SchemaField("ANALYST_STRONG_BUY", "INTEGER"),
            bigquery.SchemaField("ANALYST_BUY", "INTEGER"),
            bigquery.SchemaField("ANALYST_HOLD", "INTEGER"),
            bigquery.SchemaField("ANALYST_SELL", "INTEGER"),
            bigquery.SchemaField("ANALYST_STRONG_SELL", "INTEGER"),
        ],
    )
    job = client.load_table_from_dataframe(df, table_ref(TABLE_NAME).strip("`"), job_config=job_config)
    job.result()

    (row,) = client.query(
        f"SELECT COUNT(*) AS N FROM {table_ref(TABLE_NAME)} WHERE FETCH_DATE = CURRENT_DATE()"
    ).result()
    print(f"\nLoaded {row.N} rows → {TABLE_NAME}")


if __name__ == "__main__":
    main()
