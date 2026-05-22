"""
Irish Market Intelligence — news, analyst ratings, and fundamentals.

Three sections:
  1. News feed — live headlines from Yahoo Finance for selected stock
  2. Analyst consensus — buy/hold/sell breakdown across all Irish stocks
  3. Fundamentals — PE ratio, market cap, dividend yield, employees
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from connection import get_snowflake_connection
from style import apply_global_css, sidebar_info, CHART_LAYOUT, GREEN

st.set_page_config(page_title="Irish Intelligence | IMID", page_icon="🇮🇪", layout="wide")
apply_global_css()


@st.cache_resource
def get_connection():
    return get_snowflake_connection()


@st.cache_data(ttl=21600)
def load_intelligence() -> pd.DataFrame:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM FINANCIAL_MARKETS.PUBLIC.FCT_IRISH_INTELLIGENCE ORDER BY NAME")
    df = cur.fetch_pandas_all()
    cur.close()
    return df


def fetch_news(ticker: str) -> list:
    """Fetch live news headlines — not cached since they update hourly."""
    try:
        t = yf.Ticker(ticker)
        return t.news or []
    except Exception:
        return []


sidebar_info()
st.markdown("## 🇮🇪 Irish Market Intelligence")
st.caption("Analyst ratings, company fundamentals, and live news")
st.divider()

df = load_intelligence()

# Filter to stocks with meaningful data (not indices/ETFs)
stocks = df[df["SECTOR"].notna()].copy()

# ── Analyst consensus overview ────────────────────────────────────────────────

st.markdown("### 📊 Analyst Consensus")
st.caption("Buy/Hold/Sell breakdown from analyst recommendations over the last 3 months")

rated = stocks[stocks["TOTAL_ANALYSTS"] > 0].copy()

if rated.empty:
    st.info("No analyst ratings available at this time.")
else:
    col1, col2 = st.columns([2, 1])

    with col1:
        # Stacked bar of buy/hold/sell per company
        rated_sorted = rated.sort_values("ANALYST_CONSENSUS")
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Strong Buy", x=rated_sorted["NAME"],
                             y=rated_sorted["ANALYST_STRONG_BUY"],
                             marker_color="#00c853"))
        fig.add_trace(go.Bar(name="Buy",        x=rated_sorted["NAME"],
                             y=rated_sorted["ANALYST_BUY"],
                             marker_color="#69f0ae"))
        fig.add_trace(go.Bar(name="Hold",       x=rated_sorted["NAME"],
                             y=rated_sorted["ANALYST_HOLD"],
                             marker_color="#ffd740"))
        fig.add_trace(go.Bar(name="Sell",       x=rated_sorted["NAME"],
                             y=rated_sorted["ANALYST_SELL"],
                             marker_color="#ff6e40"))
        fig.add_trace(go.Bar(name="Strong Sell",x=rated_sorted["NAME"],
                             y=rated_sorted["ANALYST_STRONG_SELL"],
                             marker_color="#ff1744"))
        fig.update_layout(**CHART_LAYOUT, barmode="stack", height=380,
                          legend=dict(orientation="h", y=1.05))
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Consensus summary**")
        for _, row in rated.iterrows():
            colour = {"Strong Buy":"🟢","Buy":"🟢","Hold":"🟡",
                      "Sell":"🔴","No Rating":"⚪"}.get(row["ANALYST_CONSENSUS"],"⚪")
            st.markdown(f"{colour} **{row['NAME']}** — {row['ANALYST_CONSENSUS']}")

st.divider()

# ── Fundamentals table ────────────────────────────────────────────────────────

st.markdown("### 📋 Company Fundamentals")
st.caption("Key financial metrics — updated daily")

fund = stocks[[
    "NAME","SECTOR","MARKET_CAP","PE_RATIO","FORWARD_PE",
    "DIVIDEND_YIELD","EPS","PROFIT_MARGIN","EMPLOYEES"
]].copy()

fund["MARKET_CAP"]     = fund["MARKET_CAP"].map(
    lambda x: f"£{x/1e9:.1f}B" if pd.notna(x) and x >= 1e9
    else (f"£{x/1e6:.0f}M" if pd.notna(x) else "—"))
fund["PE_RATIO"]       = fund["PE_RATIO"].map(lambda x: f"{x:.1f}x" if pd.notna(x) else "—")
fund["FORWARD_PE"]     = fund["FORWARD_PE"].map(lambda x: f"{x:.1f}x" if pd.notna(x) else "—")
fund["DIVIDEND_YIELD"] = fund["DIVIDEND_YIELD"].map(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "—")
fund["EPS"]            = fund["EPS"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
fund["PROFIT_MARGIN"]  = fund["PROFIT_MARGIN"].map(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—")
fund["EMPLOYEES"]      = fund["EMPLOYEES"].map(lambda x: f"{int(x):,}" if pd.notna(x) else "—")

fund.columns = ["Company","Sector","Market Cap","P/E","Fwd P/E",
                "Div Yield","EPS","Net Margin","Employees"]
st.dataframe(fund, use_container_width=True, hide_index=True)

st.divider()

# ── Live news feed ────────────────────────────────────────────────────────────

st.markdown("### 📰 Live News")
st.caption("Latest headlines — fetched directly from Yahoo Finance")

all_names   = stocks["NAME"].tolist()
selected    = st.selectbox("Select company", all_names)
ticker      = stocks[stocks["NAME"] == selected]["TICKER"].values[0]

# Show company description if available
desc = stocks[stocks["NAME"] == selected]["DESCRIPTION"].values[0]
if desc and str(desc).strip():
    with st.expander("About this company"):
        st.write(str(desc))

news = fetch_news(ticker)

if not news:
    st.info("No recent news found for this stock.")
else:
    for item in news[:10]:
        title     = item.get("title", "No title")
        link      = item.get("link", "#")
        publisher = item.get("publisher", "")
        pub_time  = pd.to_datetime(item.get("providerPublishTime", 0), unit="s")
        time_str  = pub_time.strftime("%d %b %Y %H:%M") if pub_time.year > 2000 else ""

        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px 18px;margin-bottom:10px;">
            <a href="{link}" target="_blank" style="color:#e6edf3;text-decoration:none;font-weight:600;font-size:0.95rem;">{title}</a>
            <br><span style="color:#8b949e;font-size:0.78rem;">{publisher} · {time_str}</span>
        </div>
        """, unsafe_allow_html=True)
