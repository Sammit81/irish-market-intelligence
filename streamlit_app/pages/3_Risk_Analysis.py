"""
Risk Analysis — volatility and correlation between assets.

What is correlation?
  If two assets have a correlation of 1.0, they move in exactly the same
  direction every day. Owning both gives you no protection.
  A correlation of -1.0 means they move in opposite directions — when one
  falls, the other rises. That's ideal diversification.
  0.0 means they move completely independently.

What is volatility?
  How much an asset's price swings day to day. Higher volatility = higher
  risk. A volatility of 20% means the price typically moves ±20% per year.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from connection import get_snowflake_connection
from style import apply_global_css, sidebar_info, CHART_LAYOUT, GREEN, RED

st.set_page_config(page_title="Risk Analysis | IMID", page_icon="📉", layout="wide")

apply_global_css()
sidebar_info()


@st.cache_resource
def get_connection():
    return get_snowflake_connection()


@st.cache_data(ttl=3600)
def load_returns(days: int) -> pd.DataFrame:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(f"""
        SELECT NAME, PRICE_DATE, DAILY_RETURN, VOLATILITY_30D
        FROM FINANCIAL_MARKETS.PUBLIC.FCT_RETURNS_HISTORY
        WHERE PRICE_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
          AND DAILY_RETURN IS NOT NULL
        ORDER BY NAME, PRICE_DATE
    """)
    return cur.fetch_pandas_all()


@st.cache_data(ttl=3600)
def load_summary() -> pd.DataFrame:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT NAME, LATEST_PRICE, VOLATILITY_30D, YTD_RETURN, DAILY_RETURN FROM FINANCIAL_MARKETS.PUBLIC.FCT_MARKET_SUMMARY")
    return cur.fetch_pandas_all()


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("📉 Risk Analysis")
st.caption("Understanding how risky each investment is and how they relate to each other")

days = st.selectbox("Analysis period", [90, 180, 365, 730], index=2,
                    format_func=lambda d: {90:"3 Months", 180:"6 Months",
                                           365:"1 Year", 730:"2 Years"}.get(d))

df      = load_returns(days)
summary = load_summary()

# ── Volatility ranking ────────────────────────────────────────────────────────

st.subheader("🌡️ Risk Level by Asset")
st.info(
    "**How to read this:** Longer bar = more volatile = higher risk. "
    "Indices like S&P 500 tend to be less volatile than individual stocks. "
    "Volatility is measured as the annualised standard deviation of daily returns."
)

vol_df = summary.dropna(subset=["VOLATILITY_30D"]).sort_values("VOLATILITY_30D", ascending=True).copy()
vol_df["VOL_PCT"] = vol_df["VOLATILITY_30D"] * 100
vol_df["RISK_LABEL"] = pd.cut(
    vol_df["VOLATILITY_30D"],
    bins  = [0, 0.15, 0.25, 1.0],
    labels= ["🟢 Low Risk", "🟡 Medium Risk", "🔴 High Risk"]
)

fig = px.bar(
    vol_df,
    x     = "VOL_PCT",
    y     = "NAME",
    color = "RISK_LABEL",
    color_discrete_map={
        "🟢 Low Risk":    "green",
        "🟡 Medium Risk": "orange",
        "🔴 High Risk":   "red",
    },
    orientation = "h",
    labels={"VOL_PCT": "Annualised Volatility (%)", "NAME": "", "RISK_LABEL": "Risk Level"},
    text  = vol_df["VOL_PCT"].map(lambda x: f"{x:.1f}%"),
)
fig.update_traces(textposition="outside")
fig.update_layout(**CHART_LAYOUT, height=450, legend_title="Risk Level")
st.plotly_chart(fig, use_container_width=True)

# ── Correlation heatmap ───────────────────────────────────────────────────────

st.subheader("🔗 How Assets Move Together (Correlation)")
st.info(
    "**How to read this:** Dark green = move together (1.0). "
    "Dark red = move in opposite directions (-1.0). "
    "White = no relationship. "
    "**For a healthy portfolio:** you want some red/white cells — assets that don't all fall at the same time."
)

# Pivot to wide format: rows = dates, columns = asset names
pivot = df.pivot_table(index="PRICE_DATE", columns="NAME", values="DAILY_RETURN")
pivot = pivot.dropna(axis=1, thresh=int(len(pivot)*0.5))  # drop assets with >50% missing

corr = pivot.corr().round(2)

fig2 = go.Figure(data=go.Heatmap(
    z           = corr.values,
    x           = corr.columns.tolist(),
    y           = corr.index.tolist(),
    colorscale  = "RdYlGn",
    zmin        = -1,
    zmax        = 1,
    text        = corr.values.round(2),
    texttemplate= "%{text}",
    textfont    = dict(size=10),
    hoverongaps = False,
))
fig2.update_layout(
    height = 550,
    xaxis  = dict(tickangle=-45),
)
st.plotly_chart(fig2, use_container_width=True)

# ── Rolling volatility over time ──────────────────────────────────────────────

st.subheader("📈 How Risk Has Changed Over Time")
st.caption(
    "Volatility spikes during market stress (crashes, rate hikes). "
    "This chart shows when each asset became more or less risky."
)

top_assets = summary.nlargest(6, "VOLATILITY_30D")["NAME"].tolist()
vol_time = df[df["NAME"].isin(top_assets)].copy()

fig3 = px.line(
    vol_time,
    x      = "PRICE_DATE",
    y      = "VOLATILITY_30D",
    color  = "NAME",
    labels = {"VOLATILITY_30D": "30-day Volatility (annualised)", "PRICE_DATE": "", "NAME": "Asset"},
)
fig3.update_layout(
    height       = 350,
    yaxis_tickformat=".0%",
    hovermode    = "x unified",
    legend       = dict(orientation="h", y=1.05),
)
st.plotly_chart(fig3, use_container_width=True)
