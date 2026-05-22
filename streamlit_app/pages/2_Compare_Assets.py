"""
Compare Assets — side-by-side performance comparison.

All assets are normalised to start at 100 so you can compare them
regardless of their actual price. If an asset ends at 120, it gained 20%.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

st.set_page_config(page_title="Compare Assets | IMID", page_icon="⚖️", layout="wide")


@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account   = os.environ["SNOWFLAKE_ACCOUNT"],
        user      = os.environ["SNOWFLAKE_USER"],
        password  = os.environ["SNOWFLAKE_PASSWORD"],
        warehouse = os.environ["SNOWFLAKE_WAREHOUSE"],
        database  = os.environ["SNOWFLAKE_DATABASE"],
        schema    = os.environ["SNOWFLAKE_SCHEMA"],
    )


@st.cache_data(ttl=3600)
def load_all_history(days: int) -> pd.DataFrame:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(f"""
        SELECT TICKER, NAME, PRICE_DATE, CLOSE_PRICE, DAILY_RETURN, VOLATILITY_30D
        FROM FCT_RETURNS_HISTORY
        WHERE PRICE_DATE >= DATEADD('day', -{days}, CURRENT_DATE())
        ORDER BY TICKER, PRICE_DATE
    """)
    return cur.fetch_pandas_all()


@st.cache_data(ttl=3600)
def load_summary() -> pd.DataFrame:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM FCT_MARKET_SUMMARY")
    return cur.fetch_pandas_all()


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("⚖️ Compare Assets")
st.caption("See how different investments would have performed over the same period")

summary = load_summary()
all_names = summary["NAME"].tolist()

col1, col2 = st.columns([3, 1])
with col1:
    selected_names = st.multiselect(
        "Pick assets to compare (select 2 or more)",
        options=all_names,
        default=all_names[:4] if len(all_names) >= 4 else all_names,
    )
with col2:
    days = st.selectbox("Period", [30, 90, 180, 365, 730], index=3,
                        format_func=lambda d: {30:"1 Month", 90:"3 Months",
                                               180:"6 Months", 365:"1 Year",
                                               730:"2 Years"}.get(d, f"{d}d"))

if len(selected_names) < 2:
    st.info("Select at least 2 assets to compare.")
    st.stop()

selected_tickers = summary[summary["NAME"].isin(selected_names)]["TICKER"].tolist()
df = load_all_history(days)
df = df[df["NAME"].isin(selected_names)]

# ── Normalised growth chart ───────────────────────────────────────────────────

st.subheader("📈 Growth of £100 Invested")
st.caption(
    "All assets start at 100. If a line ends at 120, that investment grew 20% "
    "over this period. Higher line = better performance."
)

# Normalise each ticker to start at 100
fig = go.Figure()
colors = px.colors.qualitative.Set2

for i, name in enumerate(selected_names):
    asset = df[df["NAME"] == name].sort_values("PRICE_DATE").copy()
    if asset.empty:
        continue
    first_price = asset["CLOSE_PRICE"].iloc[0]
    asset["NORMALISED"] = (asset["CLOSE_PRICE"] / first_price) * 100

    final_val = asset["NORMALISED"].iloc[-1]
    gain      = final_val - 100

    fig.add_trace(go.Scatter(
        x    = asset["PRICE_DATE"],
        y    = asset["NORMALISED"],
        name = f"{name} ({gain:+.1f}%)",
        line = dict(color=colors[i % len(colors)], width=2.5),
        hovertemplate=f"<b>{name}</b><br>Value: £%{{y:.1f}}<br>Date: %{{x}}<extra></extra>"
    ))

fig.add_hline(y=100, line_dash="dot", line_color="grey", opacity=0.5,
              annotation_text="Starting point")
fig.update_layout(
    height=450,
    yaxis_title="Value of £100 invested",
    xaxis_title="",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ── Side-by-side comparison table ────────────────────────────────────────────

st.subheader("📊 Head-to-Head Metrics")
st.caption("Quick comparison of key numbers across your selected assets")

compare = summary[summary["NAME"].isin(selected_names)][[
    "NAME", "LATEST_PRICE", "DAILY_RETURN", "YTD_RETURN",
    "VOLATILITY_30D", "WEEK52_HIGH", "WEEK52_LOW", "FROM_52W_HIGH"
]].copy()

compare["DAILY_RETURN"]   = compare["DAILY_RETURN"].map(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")
compare["YTD_RETURN"]     = compare["YTD_RETURN"].map(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")
compare["VOLATILITY_30D"] = compare["VOLATILITY_30D"].map(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—")
compare["FROM_52W_HIGH"]  = compare["FROM_52W_HIGH"].map(lambda x: f"{x*100:.1f}%" if pd.notna(x) else "—")
compare.columns = ["Asset", "Latest Price", "Today", "Year-to-Date",
                   "Risk (Volatility)", "52-Week High", "52-Week Low", "Below Peak"]

st.dataframe(compare, use_container_width=True, hide_index=True)

# ── Risk vs Return scatter ────────────────────────────────────────────────────

st.subheader("🎯 Risk vs. Return")
st.caption(
    "The ideal investment is top-left: high return, low risk. "
    "Assets bottom-right are high risk with low reward — avoid those."
)

risk_return = summary[summary["NAME"].isin(selected_names)].copy()
risk_return = risk_return.dropna(subset=["VOLATILITY_30D", "YTD_RETURN"])

fig2 = px.scatter(
    risk_return,
    x     = "VOLATILITY_30D",
    y     = "YTD_RETURN",
    text  = "NAME",
    color = "YTD_RETURN",
    color_continuous_scale=["red", "lightgrey", "green"],
    color_continuous_midpoint=0,
    labels={
        "VOLATILITY_30D": "Risk (30-day Volatility)",
        "YTD_RETURN":     "Return This Year (YTD)",
    },
)
fig2.update_traces(
    textposition="top center",
    marker=dict(size=14),
)
fig2.add_hline(y=0, line_dash="dash", line_color="grey", opacity=0.5)
fig2.update_layout(
    height=400,
    xaxis_tickformat=".0%",
    yaxis_tickformat=".0%",
    coloraxis_showscale=False,
)
st.plotly_chart(fig2, use_container_width=True)
