"""
Fetch historical and latest price data from Yahoo Finance → Snowflake.

What this does and why:
  - yfinance pulls OHLCV (Open, High, Low, Close, Volume) data for each ticker
  - We store it in Snowflake as RAW_PRICES — one row per ticker per day
  - On first run it fetches 2 years of history
  - On subsequent runs it fetches only new data (incremental load)
  - This is what makes the project dynamic — run this daily and the dashboard
    always shows current data

Run from project root:
    uv run data_pipeline/fetch_prices.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

sys.path.append(str(Path(__file__).parent.parent))
from data_pipeline.tickers import ALL_TICKERS
from data_pipeline.snowflake_client import get_connection

load_dotenv()

HISTORY_DAYS = 730   # 2 years on first run
TABLE_NAME   = "RAW_PRICES"


def get_last_loaded_date(conn) -> dict[str, str]:
    """Return the most recent date loaded per ticker — for incremental loads."""
    cur = conn.cursor()
    try:
        cur.execute(f"""
            SELECT TICKER, MAX(PRICE_DATE)
            FROM {TABLE_NAME}
            GROUP BY TICKER
        """)
        return {row[0]: row[1] for row in cur.fetchall()}
    except Exception:
        return {}
    finally:
        cur.close()


def fetch_ticker(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Download OHLCV data for one ticker and return a clean DataFrame."""
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()
        df.columns = [c.upper().replace(" ", "_") for c in df.columns]
        df["TICKER"] = ticker
        df["NAME"]   = ALL_TICKERS.get(ticker, ticker)
        df = df.rename(columns={"DATE": "PRICE_DATE"})
        df["PRICE_DATE"] = pd.to_datetime(df["PRICE_DATE"]).dt.date.astype(str)

        return df[["TICKER", "NAME", "PRICE_DATE", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]]
    except Exception as e:
        print(f"  ERROR fetching {ticker}: {e}")
        return pd.DataFrame()


def main():
    print("Connecting to Snowflake...")
    conn = get_connection()

    # Create table if it doesn't exist
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            TICKER     VARCHAR,
            NAME       VARCHAR,
            PRICE_DATE DATE,
            OPEN       FLOAT,
            HIGH       FLOAT,
            LOW        FLOAT,
            CLOSE      FLOAT,
            VOLUME     FLOAT,
            LOADED_AT  TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
            PRIMARY KEY (TICKER, PRICE_DATE)
        )
    """)
    cur.close()

    last_dates = get_last_loaded_date(conn)
    end_date   = datetime.today().strftime("%Y-%m-%d")
    all_frames = []

    for ticker, name in ALL_TICKERS.items():
        if ticker in last_dates:
            # Incremental: fetch from day after last loaded date
            last = pd.to_datetime(last_dates[ticker])
            start_date = (last + timedelta(days=1)).strftime("%Y-%m-%d")
            mode = "incremental"
        else:
            # First run: fetch full history
            start_date = (datetime.today() - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
            mode = "full"

        print(f"  {ticker:<12} {name:<30} [{mode}] {start_date} → {end_date}", end=" ")
        df = fetch_ticker(ticker, start_date, end_date)

        if df.empty:
            print("no data")
            continue

        all_frames.append(df)
        print(f"{len(df)} rows")

    if not all_frames:
        print("No new data to load.")
        conn.close()
        return

    combined = pd.concat(all_frames, ignore_index=True)

    # Upsert: delete existing rows for the same ticker+date then insert
    cur = conn.cursor()
    for ticker in combined["TICKER"].unique():
        dates = combined[combined["TICKER"] == ticker]["PRICE_DATE"].tolist()
        dates_str = ", ".join(f"'{d}'" for d in dates)
        cur.execute(f"""
            DELETE FROM {TABLE_NAME}
            WHERE TICKER = '{ticker}' AND PRICE_DATE IN ({dates_str})
        """)
    cur.close()

    success, _, nrows, _ = write_pandas(conn, combined, TABLE_NAME, overwrite=False)
    print(f"\nLoaded {nrows:,} rows → {TABLE_NAME}")
    conn.close()


if __name__ == "__main__":
    main()
