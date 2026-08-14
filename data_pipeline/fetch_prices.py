"""
Fetch historical and latest price data from Yahoo Finance → BigQuery.

What this does and why:
  - yfinance pulls OHLCV (Open, High, Low, Close, Volume) data for each ticker
  - We store it in BigQuery as RAW_PRICES — one row per ticker per day
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
from google.cloud import bigquery

sys.path.append(str(Path(__file__).parent.parent))
from data_pipeline.tickers import ALL_TICKERS
from data_pipeline.bigquery_client import get_connection, table_ref

load_dotenv()

HISTORY_DAYS = 730   # 2 years on first run
TABLE_NAME   = "RAW_PRICES"


def get_last_loaded_date(client: bigquery.Client) -> dict[str, str]:
    """Return the most recent date loaded per ticker — for incremental loads."""
    try:
        rows = client.query(f"""
            SELECT TICKER, MAX(PRICE_DATE) AS MAX_DATE
            FROM {table_ref(TABLE_NAME)}
            GROUP BY TICKER
        """).result()
        return {row.TICKER: row.MAX_DATE for row in rows}
    except Exception:
        return {}


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
    print("Connecting to BigQuery...")
    client = get_connection()

    # Create table if it doesn't exist
    client.query(f"""
        CREATE TABLE IF NOT EXISTS {table_ref(TABLE_NAME)} (
            TICKER     STRING,
            NAME       STRING,
            PRICE_DATE DATE,
            OPEN       FLOAT64,
            HIGH       FLOAT64,
            LOW        FLOAT64,
            CLOSE      FLOAT64,
            VOLUME     FLOAT64,
            LOADED_AT  TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
    """).result()

    last_dates = get_last_loaded_date(client)
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
        return

    combined = pd.concat(all_frames, ignore_index=True)

    # Upsert: delete existing rows in the date range about to be reloaded, then insert.
    # BigQuery strictly rate-limits DML mutations per table, so this must be ONE DELETE
    # statement covering every ticker rather than one DELETE per ticker.
    min_dates = pd.to_datetime(combined["PRICE_DATE"]).groupby(combined["TICKER"]).min()
    conditions, params = [], []
    for i, (ticker, min_date) in enumerate(min_dates.items()):
        conditions.append(f"(TICKER = @ticker_{i} AND PRICE_DATE >= @date_{i})")
        params.append(bigquery.ScalarQueryParameter(f"ticker_{i}", "STRING", ticker))
        params.append(bigquery.ScalarQueryParameter(f"date_{i}", "DATE", min_date.date()))

    client.query(
        f"DELETE FROM {table_ref(TABLE_NAME)} WHERE {' OR '.join(conditions)}",
        job_config=bigquery.QueryJobConfig(query_parameters=params),
    ).result()

    load_df = combined.copy()
    load_df["PRICE_DATE"] = pd.to_datetime(load_df["PRICE_DATE"]).dt.date

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        schema=[
            bigquery.SchemaField("TICKER", "STRING"),
            bigquery.SchemaField("NAME", "STRING"),
            bigquery.SchemaField("PRICE_DATE", "DATE"),
            bigquery.SchemaField("OPEN", "FLOAT64"),
            bigquery.SchemaField("HIGH", "FLOAT64"),
            bigquery.SchemaField("LOW", "FLOAT64"),
            bigquery.SchemaField("CLOSE", "FLOAT64"),
            bigquery.SchemaField("VOLUME", "FLOAT64"),
        ],
    )
    job = client.load_table_from_dataframe(load_df, table_ref(TABLE_NAME).strip("`"), job_config=job_config)
    job.result()
    print(f"\nLoaded {len(combined):,} rows → {TABLE_NAME}")


if __name__ == "__main__":
    main()
