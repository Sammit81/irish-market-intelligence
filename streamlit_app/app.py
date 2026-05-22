"""
Irish Market Intelligence Dashboard — main overview page.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from connection import get_snowflake_connection
from style import apply_global_css, sidebar_info, CHART_LAYOUT, GREEN, RED

st.set_page_config(
    page_title="Irish Market Intelligence Dashboard",
    page_icon="📈",
    layout="wide",
)

apply_global_css()


@st.cache_resource
def get_connection():
    return get_snowflake_connection()


@st.cache_data(ttl=21600)
def load_summary() -> pd.DataFrame:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM FINANCIAL_MARKETS.PUBLIC.FCT_MARKET_SUMMARY ORDER BY TICKER")
    df = cur.fetch_pandas_all()
    cur.close()
    return df


@st.cache_data(ttl=21600)
def load_history(ticker: str, days: int = 365) -> pd.DataFrame:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(f"""
        SELECT * FROM FINANCIAL_MARKETS.PUBLIC.FCT_RETURNS_HISTORY
        WHERE TICKER = '{ticker}'
          AND PRICE_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
        ORDER BY PRICE_DATE
    """)
    df = cur.fetch_pandas_all()
    cur.close()
    return df


# ── Sidebar ───────────────────────────────────────────────────────────────────

df = load_summary()
last_date = df["LATEST_DATE"].max() if not df.empty else "—"
sidebar_info(str(last_date))

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("## 📈 Irish Market Intelligence Dashboard")
st.caption("Live data · Yahoo Finance · Snowflake · dbt · Updated daily")
st.divider()

if df.empty:
    st.warning("No data loaded yet. Run `uv run data_pipeline/fetch_prices.py` first.")
    st.stop()

# ── Index KPI tiles ───────────────────────────────────────────────────────────

st.markdown("### Global Indices")
indices = df[df["TICKER"].str.startswith("^")]
cols    = st.columns(len(indices))
for col, (_, row) in zip(cols, indices.iterrows()):
    delta = f"{row['DAILY_RETURN']*100:+.2f}%" if pd.notna(row["DAILY_RETURN"]) else "N/A"
    col.metric(label=row["NAME"], value=f"{row['LATEST_PRICE']:,.2f}", delta=delta)

st.divider()

# ── Irish stocks KPI strip ────────────────────────────────────────────────────

st.markdown("### Irish Market")
irish = df[~df["TICKER"].str.startswith("^") &
           ~df["TICKER"].isin(["GOOGL","META","MSFT","AAPL","AMZN","SPY","QQQ","VWRL.L","CSPX.L"])]
i_cols = st.columns(min(len(irish), 7))
for col, (_, row) in zip(i_cols, irish.head(7).iterrows()):
    delta = f"{row['DAILY_RETURN']*100:+.2f}%" if pd.notna(row["DAILY_RETURN"]) else "N/A"
    col.metric(label=row["NAME"], value=f"{row['LATEST_PRICE']:,.2f}", delta=delta)

st.divider()

# ── Today's movers ────────────────────────────────────────────────────────────

col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown("### Today's Movers")
    movers = df.dropna(subset=["DAILY_RETURN"]).copy()
    movers["DAILY_RETURN_PCT"] = movers["DAILY_RETURN"] * 100
    movers = movers.sort_values("DAILY_RETURN_PCT")

    fig = px.bar(
        movers,
        x="DAILY_RETURN_PCT",
        y="NAME",
        orientation="h",
        color="DAILY_RETURN_PCT",
        color_continuous_scale=["#ff1744", "#21262d", "#00c853"],
        color_continuous_midpoint=0,
        labels={"DAILY_RETURN_PCT": "Daily Return (%)", "NAME": ""},
    )
    fig.update_layout(**CHART_LAYOUT, height=500, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown("### YTD Performance")
    ytd = df.dropna(subset=["YTD_RETURN"]).copy()
    ytd["YTD_PCT"] = ytd["YTD_RETURN"] * 100
    ytd = ytd.sort_values("YTD_PCT", ascending=False).head(10)

    fig2 = px.bar(
        ytd,
        x="NAME",
        y="YTD_PCT",
        color="YTD_PCT",
        color_continuous_scale=["#ff1744", "#21262d", "#00c853"],
        color_continuous_midpoint=0,
        labels={"YTD_PCT": "YTD Return (%)", "NAME": ""},
    )
    fig2.update_layout(**CHART_LAYOUT, height=500, coloraxis_showscale=False)
    fig2.update_xaxes(tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Quick chart ───────────────────────────────────────────────────────────────

st.markdown("### Price Chart")
c1, c2 = st.columns([3, 1])
with c1:
    selected = st.selectbox("Select asset", df["NAME"].tolist())
with c2:
    days = st.selectbox("Period", [30, 90, 180, 365, 730],
                        format_func=lambda d: {30:"1M",90:"3M",180:"6M",365:"1Y",730:"2Y"}.get(d),
                        index=2)

ticker = df[df["NAME"] == selected]["TICKER"].values[0]
hist   = load_history(ticker, days)

if not hist.empty:
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=hist["PRICE_DATE"], y=hist["CLOSE_PRICE"],
        name="Price", fill="tozeroy",
        line=dict(color=GREEN, width=2),
        fillcolor="rgba(0,200,83,0.08)",
    ))
    fig3.add_trace(go.Scatter(
        x=hist["PRICE_DATE"], y=hist["MA_30D"],
        name="30-day MA", line=dict(color="orange", width=1.5, dash="dash")
    ))
    fig3.update_layout(**CHART_LAYOUT,
                       title=f"{selected}",
                       height=350,
                       xaxis_title="",
                       yaxis_title="Price",
                       legend=dict(orientation="h", y=1.05))
    st.plotly_chart(fig3, use_container_width=True)

# ── Full asset table ──────────────────────────────────────────────────────────

with st.expander("📋 Full Asset Table", expanded=False):
    display = df[["TICKER","NAME","LATEST_PRICE","DAILY_RETURN",
                  "YTD_RETURN","VOLATILITY_30D","WEEK52_HIGH","WEEK52_LOW"]].copy()
    display["DAILY_RETURN"]   = display["DAILY_RETURN"].map(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")
    display["YTD_RETURN"]     = display["YTD_RETURN"].map(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")
    display["VOLATILITY_30D"] = display["VOLATILITY_30D"].map(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—")
    display.columns = ["Ticker","Name","Price","Today","YTD","Volatility","52W High","52W Low"]
    st.dataframe(display, use_container_width=True, hide_index=True)
