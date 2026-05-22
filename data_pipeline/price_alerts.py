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

sys.path.append(str(Path(__file__).parent.parent))
from data_pipeline.snowflake_client import get_connection

load_dotenv()

THRESHOLD = 0.05   # 5% move triggers an alert


def check_alerts() -> list[dict]:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT NAME, TICKER, LATEST_PRICE, DAILY_RETURN
        FROM FINANCIAL_MARKETS.PUBLIC.FCT_MARKET_SUMMARY
        WHERE ABS(DAILY_RETURN) >= %s
          AND DAILY_RETURN IS NOT NULL
        ORDER BY ABS(DAILY_RETURN) DESC
    """, (THRESHOLD,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"name": r[0], "ticker": r[1], "price": r[2], "return": r[3]}
        for r in rows
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
