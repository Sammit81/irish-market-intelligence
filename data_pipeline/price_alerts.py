"""
Price alerts — checks for stocks that moved more than 5% today.

How it works:
  Queries FCT_MARKET_SUMMARY for the latest daily return per ticker.
  If any asset moved >5% (up or down), logs it to the GitHub Actions
  output and optionally sends an email if ALERT_EMAIL and SMTP_PASSWORD
  are set as GitHub secrets.

Email setup (optional):
  Add two GitHub secrets:
    ALERT_EMAIL   — your Gmail address (e.g. you@gmail.com)
    SMTP_PASSWORD — a Gmail App Password (not your main password)
                    Create one at: myaccount.google.com/apppasswords

Run from project root:
    uv run data_pipeline/price_alerts.py
"""
import os
import sys
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

sys.path.append(str(Path(__file__).parent.parent))
from data_pipeline.bigquery_client import get_connection, table_ref

load_dotenv()

THRESHOLD = 0.05   # 5% move triggers an alert


def check_alerts() -> list[dict]:
    client = get_connection()
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("threshold", "FLOAT64", THRESHOLD)]
    )
    df = client.query(f"""
        SELECT NAME, TICKER, LATEST_PRICE, DAILY_RETURN
        FROM {table_ref('fct_market_summary')}
        WHERE ABS(DAILY_RETURN) >= @threshold
          AND DAILY_RETURN IS NOT NULL
        ORDER BY ABS(DAILY_RETURN) DESC
    """, job_config=job_config).result().to_dataframe()
    df.columns = df.columns.str.upper()
    return [
        {"name": r.NAME, "ticker": r.TICKER, "price": r.LATEST_PRICE, "return": r.DAILY_RETURN}
        for _, r in df.iterrows()
    ]


def send_email(alerts: list[dict]) -> None:
    email    = os.environ.get("ALERT_EMAIL", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()

    if not email or not password:
        print("  No ALERT_EMAIL or SMTP_PASSWORD set — skipping email.")
        return

    lines = ["The following assets moved more than 5% today:\n"]
    for a in alerts:
        direction = "📈 UP" if a["return"] > 0 else "📉 DOWN"
        lines.append(f"  {direction}  {a['name']} ({a['ticker']}): {a['return']*100:+.2f}%  @ {a['price']:,.2f}")

    lines.append("\nView dashboard: https://irish-market-intelligence-ngkorhtqqvlho8qdmrsqfs.streamlit.app")
    body = "\n".join(lines)

    msg = MIMEText(body)
    msg["Subject"] = f"🚨 Irish Market Alert — {len(alerts)} asset(s) moved >5% today"
    msg["From"]    = email
    msg["To"]      = email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(email, password)
        server.send_message(msg)
    print(f"  Alert email sent to {email}")


def main():
    print("Checking for price alerts...")
    alerts = check_alerts()

    if not alerts:
        print("  No alerts — no asset moved more than 5% today.")
        return

    print(f"\n🚨 {len(alerts)} alert(s) — assets that moved >5%:")
    for a in alerts:
        direction = "UP  " if a["return"] > 0 else "DOWN"
        print(f"  {direction}  {a['name']:<35} {a['return']*100:+.2f}%")

    send_email(alerts)


if __name__ == "__main__":
    main()
