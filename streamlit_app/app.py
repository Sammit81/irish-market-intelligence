"""
Financial Markets Analytics Dashboard — main entry point.

What Streamlit does:
  Every time a user interacts with a widget (dropdown, slider, button),
  Streamlit re-runs this script from top to bottom and updates the page.
  This is what makes it interactive without needing JavaScript or a backend.

Pages:
  app.py              — Market Overview (this file)
  pages/1_stocks.py   — Individual stock deep dive
  pages/2_compare.py  — Compare multiple assets
  pages/3_risk.py     — Volatility and correlation analysis
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from connection import get_snowflake_connection

st.set_page_config(
    page_title="Irish Market Intelligence Dashboard",
    page_icon="📈",
    layout="wide",
)


@st.cache_resource
def get_connection():
    return get_snowflake_connection()


@st.cache_data(ttl=3600)
def load_summary() -> pd.DataFrame:
    """Load market summary — cached for 1 hour so we don't hammer Snowflake."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM FCT_MARKET_SUMMARY ORDER BY TICKER")
    df = cur.fetch_pandas_all()
    cur.close()
    return df


@st.cache_data(ttl=3600)
def load_history(ticker: str, days: int = 365) -> pd.DataFrame:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(f"""
        SELECT * FROM FCT_RETURNS_HISTORY
        WHERE TICKER = '{ticker}'
          AND PRICE_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
        ORDER BY PRICE_DATE
    """)
    df = cur.fetch_pandas_all()
    cur.close()
    return df


# ── Page layout ──────────────────────────────────────────────────────────────

st.title("📈 Irish Market Intelligence Dashboard")
st.caption("Live data via Yahoo Finance · Irish & global markets · Powered by Snowflake + dbt")

df = load_summary()

if df.empty:
    st.warning("No data loaded yet. Run `uv run data_pipeline/fetch_prices.py` first.")
    st.stop()

# ── KPI tiles ────────────────────────────────────────────────────────────────

st.subheader("Market Snapshot")

# Show indices as top KPIs
indices = df[df["TICKER"].str.startswith("^")]
cols = st.columns(len(indices))
for col, (_, row) in zip(cols, indices.iterrows()):
    delta_pct = f"{row['DAILY_RETURN']*100:+.2f}%" if pd.notna(row['DAILY_RETURN']) else "N/A"
    col.metric(
        label = row["NAME"],
        value = f"{row['LATEST_PRICE']:,.2f}",
        delta = delta_pct,
    )

st.divider()

# ── Full summary table ────────────────────────────────────────────────────────

st.subheader("All Assets")

display = df[[
    "TICKER", "NAME", "LATEST_PRICE", "DAILY_RETURN",
    "YTD_RETURN", "VOLATILITY_30D", "WEEK52_HIGH", "WEEK52_LOW"
]].copy()

display["DAILY_RETURN"]  = display["DAILY_RETURN"].map(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")
display["YTD_RETURN"]    = display["YTD_RETURN"].map(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")
display["VOLATILITY_30D"]= display["VOLATILITY_30D"].map(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—")

st.dataframe(display, use_container_width=True, hide_index=True)

# ── Top movers chart ──────────────────────────────────────────────────────────

st.subheader("Today's Movers")

movers = df.dropna(subset=["DAILY_RETURN"]).copy()
movers["DAILY_RETURN_PCT"] = movers["DAILY_RETURN"] * 100
movers = movers.sort_values("DAILY_RETURN_PCT")

fig = px.bar(
    movers,
    x="DAILY_RETURN_PCT",
    y="NAME",
    orientation="h",
    color="DAILY_RETURN_PCT",
    color_continuous_scale=["red", "lightgrey", "green"],
    color_continuous_midpoint=0,
    labels={"DAILY_RETURN_PCT": "Daily Return (%)", "NAME": ""},
    title="Daily Return by Asset",
)
fig.update_layout(showlegend=False, coloraxis_showscale=False)
st.plotly_chart(fig, use_container_width=True)

# ── Quick price chart for selected ticker ─────────────────────────────────────

st.subheader("Quick Chart")
selected = st.selectbox("Select asset", df["NAME"].tolist())
ticker   = df[df["NAME"] == selected]["TICKER"].values[0]
days     = st.slider("Days of history", 30, 730, 180)

hist = load_history(ticker, days)
if not hist.empty:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=hist["PRICE_DATE"], y=hist["CLOSE_PRICE"],
        name="Price", line=dict(color="#1f77b4")
    ))
    fig2.add_trace(go.Scatter(
        x=hist["PRICE_DATE"], y=hist["MA_30D"],
        name="30-day MA", line=dict(color="orange", dash="dash")
    ))
    fig2.update_layout(title=f"{selected} — {days} days", xaxis_title="Date", yaxis_title="Price")
    st.plotly_chart(fig2, use_container_width=True)
