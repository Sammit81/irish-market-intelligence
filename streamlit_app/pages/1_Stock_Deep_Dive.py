"""
Stock Deep Dive — full analysis for one selected asset.

What this page shows:
  - Candlestick chart: shows Open/High/Low/Close for each day
    (green candle = price went up that day, red = went down)
  - Volume bars: how many shares traded — high volume confirms price moves
  - Moving averages: 7-day and 30-day smoothed price lines
  - Key metrics: Sharpe ratio, max drawdown, best/worst day
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import sys
from pathlib import Path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from connection import get_snowflake_connection
from style import apply_global_css, sidebar_info, CHART_LAYOUT, style_axes, GREEN, RED

st.set_page_config(page_title="Stock Deep Dive | IMID", page_icon="🔍", layout="wide")

apply_global_css()
sidebar_info()




@st.cache_data(ttl=21600)
def load_tickers():
    conn = get_snowflake_connection()
    cur  = conn.cursor()
    cur.execute("SELECT DISTINCT TICKER, NAME FROM FINANCIAL_MARKETS.PUBLIC.FCT_RETURNS_HISTORY ORDER BY NAME")
    return cur.fetch_pandas_all()


@st.cache_data(ttl=21600)
def load_ohlcv(ticker: str, days: int) -> pd.DataFrame:
    conn = get_snowflake_connection()
    cur  = conn.cursor()
    cur.execute(f"""
        SELECT p.PRICE_DATE, p.OPEN_PRICE, p.HIGH_PRICE, p.LOW_PRICE,
               p.CLOSE_PRICE, p.VOLUME, r.DAILY_RETURN, r.MA_7D, r.MA_30D,
               r.VOLATILITY_30D, r.CUMULATIVE_RETURN
        FROM FINANCIAL_MARKETS.PUBLIC.STG_PRICES p
        JOIN FINANCIAL_MARKETS.PUBLIC.FCT_RETURNS_HISTORY r
          ON p.TICKER = r.TICKER AND p.PRICE_DATE = r.PRICE_DATE
        WHERE p.TICKER = '{ticker}'
          AND p.PRICE_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
        ORDER BY p.PRICE_DATE
    """)
    return cur.fetch_pandas_all()


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("🔍 Stock Deep Dive")

tickers_df = load_tickers()
names      = tickers_df["NAME"].tolist()

col1, col2 = st.columns([2, 1])
with col1:
    selected_name = st.selectbox("Select asset", names)
with col2:
    days = st.selectbox("Period", [30, 90, 180, 365, 730], index=2,
                        format_func=lambda d: f"{d} days")

ticker = tickers_df[tickers_df["NAME"] == selected_name]["TICKER"].values[0]
df     = load_ohlcv(ticker, days)

if df.empty:
    st.warning("No data available for this asset.")
    st.stop()

# ── KPI metrics ───────────────────────────────────────────────────────────────

latest      = df.iloc[-1]
total_return = df["CUMULATIVE_RETURN"].iloc[-1]
best_day    = df["DAILY_RETURN"].max()
worst_day   = df["DAILY_RETURN"].min()

# Sharpe ratio: annualised return / annualised volatility (risk-free rate ~4%)
avg_daily   = df["DAILY_RETURN"].mean()
std_daily   = df["DAILY_RETURN"].std()
sharpe      = ((avg_daily - 0.04/252) / std_daily * (252**0.5)) if std_daily > 0 else 0

# Max drawdown: biggest peak-to-trough drop in the period
rolling_max = df["CLOSE_PRICE"].cummax()
drawdown    = (df["CLOSE_PRICE"] - rolling_max) / rolling_max
max_drawdown = drawdown.min()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Latest Price",    f"{latest['CLOSE_PRICE']:,.2f}")
m2.metric("Period Return",   f"{total_return*100:+.2f}%")
m3.metric("Sharpe Ratio",    f"{sharpe:.2f}")
m4.metric("Max Drawdown",    f"{max_drawdown*100:.2f}%")
m5.metric("30d Volatility",  f"{latest['VOLATILITY_30D']*100:.1f}%")

st.divider()

# ── Candlestick + Volume chart ────────────────────────────────────────────────

fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.75, 0.25],
    subplot_titles=[f"{selected_name} — Price", "Volume"]
)

# Candlestick
fig.add_trace(go.Candlestick(
    x    = df["PRICE_DATE"],
    open = df["OPEN_PRICE"],
    high = df["HIGH_PRICE"],
    low  = df["LOW_PRICE"],
    close= df["CLOSE_PRICE"],
    name = "OHLC",
    increasing_line_color="green",
    decreasing_line_color="red",
), row=1, col=1)

# Moving averages
fig.add_trace(go.Scatter(
    x=df["PRICE_DATE"], y=df["MA_7D"],
    name="7-day MA", line=dict(color="orange", width=1.5, dash="dot")
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df["PRICE_DATE"], y=df["MA_30D"],
    name="30-day MA", line=dict(color="blue", width=1.5)
), row=1, col=1)

# Volume bars
colors = ["green" if r >= 0 else "red" for r in df["DAILY_RETURN"]]
fig.add_trace(go.Bar(
    x=df["PRICE_DATE"], y=df["VOLUME"],
    name="Volume", marker_color=colors, opacity=0.7
), row=2, col=1)

fig.update_layout(**CHART_LAYOUT,
    height=600,
    xaxis_rangeslider_visible=False,
    showlegend=True,
    legend=dict(orientation="h", y=1.05),
)
style_axes(fig)
st.plotly_chart(fig, use_container_width=True)

# ── Daily return distribution ─────────────────────────────────────────────────

st.subheader("Daily Return Distribution")
st.caption("Shows the spread of daily gains and losses — a wider spread = more volatile asset")

fig2 = go.Figure()
fig2.add_trace(go.Histogram(
    x=df["DAILY_RETURN"] * 100,
    nbinsx=50,
    marker_color="steelblue",
    name="Daily returns"
))
fig2.add_vline(x=0, line_dash="dash", line_color="red")
fig2.update_layout(**CHART_LAYOUT,
    xaxis_title="Daily Return (%)",
    yaxis_title="Frequency",
    height=300,
)
style_axes(fig2)
st.plotly_chart(fig2, use_container_width=True)

col1, col2 = st.columns(2)
col1.metric("Best Day",  f"{best_day*100:+.2f}%")
col2.metric("Worst Day", f"{worst_day*100:+.2f}%")
