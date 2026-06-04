"""
Portfolio Tracker — input your holdings and see live P&L.

What this page does:
  You enter how many shares you own and at what price you bought them.
  The dashboard shows your current value, profit/loss, and how each
  holding is performing — updated every time the data refreshes.

Your holdings are stored in the browser session only (not saved anywhere).
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from connection import get_snowflake_connection
from style import apply_global_css, sidebar_info, CHART_LAYOUT, style_axes, GREEN, RED

st.set_page_config(page_title="Portfolio Tracker | IMID", page_icon="💼", layout="wide")
apply_global_css()




@st.cache_data(ttl=21600)
def load_prices() -> pd.DataFrame:
    conn = get_snowflake_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT TICKER, NAME, LATEST_PRICE, DAILY_RETURN, YTD_RETURN, WEEK52_HIGH, WEEK52_LOW
        FROM FINANCIAL_MARKETS.PUBLIC.FCT_MARKET_SUMMARY
        ORDER BY NAME
    """)
    df = cur.fetch_pandas_all()
    cur.close()
    return df


@st.cache_data(ttl=21600)
def load_history_multi(tickers: tuple) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    ticker_list = ", ".join(f"'{t}'" for t in tickers)
    conn = get_snowflake_connection()
    cur  = conn.cursor()
    cur.execute(f"""
        SELECT TICKER, NAME, PRICE_DATE, CLOSE_PRICE
        FROM FINANCIAL_MARKETS.PUBLIC.FCT_RETURNS_HISTORY
        WHERE TICKER IN ({ticker_list})
          AND PRICE_DATE >= DATEADD('day', -365, CURRENT_DATE())
        ORDER BY TICKER, PRICE_DATE
    """)
    df = cur.fetch_pandas_all()
    cur.close()
    return df


sidebar_info()
st.markdown("## 💼 Portfolio Tracker")
st.caption("Enter your holdings to see live profit & loss against current market prices")
st.divider()

prices_df = load_prices()
asset_names = prices_df["NAME"].tolist()

# ── Holdings input ────────────────────────────────────────────────────────────

st.markdown("### Add Your Holdings")
st.info("Select an asset, enter how many shares you hold and the price you paid. Your data stays in this browser session only.")

if "holdings" not in st.session_state:
    st.session_state.holdings = []

col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1])
with col1:
    asset     = st.selectbox("Asset", asset_names, key="asset_select")
with col2:
    quantity  = st.number_input("Shares / Units", min_value=0.001, value=10.0, step=1.0)
with col3:
    buy_price = st.number_input("Buy Price", min_value=0.01, value=100.0, step=0.01)
with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Add", use_container_width=True):
        ticker = prices_df[prices_df["NAME"] == asset]["TICKER"].values[0]
        st.session_state.holdings.append({
            "name": asset, "ticker": ticker,
            "quantity": quantity, "buy_price": buy_price
        })
        st.rerun()

if st.session_state.holdings:
    if st.button("Clear all holdings", type="secondary"):
        st.session_state.holdings = []
        st.rerun()

st.divider()

if not st.session_state.holdings:
    st.markdown("*No holdings added yet. Use the form above to add your first position.*")
    st.stop()

# ── Build portfolio table ─────────────────────────────────────────────────────

rows = []
for h in st.session_state.holdings:
    match = prices_df[prices_df["TICKER"] == h["ticker"]]
    if match.empty:
        continue
    current = match.iloc[0]
    current_price  = current["LATEST_PRICE"]
    cost_basis     = h["quantity"] * h["buy_price"]
    current_value  = h["quantity"] * current_price
    pnl            = current_value - cost_basis
    pnl_pct        = pnl / cost_basis * 100

    rows.append({
        "Asset":          h["name"],
        "Ticker":         h["ticker"],
        "Shares":         h["quantity"],
        "Buy Price":      h["buy_price"],
        "Current Price":  current_price,
        "Cost Basis":     cost_basis,
        "Current Value":  current_value,
        "P&L (£)":        pnl,
        "P&L (%)":        pnl_pct,
        "Today":          current["DAILY_RETURN"],
    })

portfolio = pd.DataFrame(rows)

# ── Portfolio KPIs ────────────────────────────────────────────────────────────

total_cost    = portfolio["Cost Basis"].sum()
total_value   = portfolio["Current Value"].sum()
total_pnl     = total_value - total_cost
total_pnl_pct = total_pnl / total_cost * 100

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Invested",  f"£{total_cost:,.2f}")
k2.metric("Current Value",   f"£{total_value:,.2f}")
k3.metric("Total P&L",       f"£{total_pnl:+,.2f}", f"{total_pnl_pct:+.2f}%")
k4.metric("Positions",       len(portfolio))

st.divider()

# ── Holdings table ────────────────────────────────────────────────────────────

st.markdown("### Holdings Breakdown")

display = portfolio.copy()
display["Buy Price"]     = display["Buy Price"].map(lambda x: f"{x:,.2f}")
display["Current Price"] = display["Current Price"].map(lambda x: f"{x:,.2f}")
display["Cost Basis"]    = display["Cost Basis"].map(lambda x: f"£{x:,.2f}")
display["Current Value"] = display["Current Value"].map(lambda x: f"£{x:,.2f}")
display["P&L (£)"]       = display["P&L (£)"].map(lambda x: f"£{x:+,.2f}")
display["P&L (%)"]       = display["P&L (%)"].map(lambda x: f"{x:+.2f}%")
display["Today"]         = display["Today"].map(lambda x: f"{x*100:+.2f}%" if pd.notna(x) else "—")

st.dataframe(display.drop(columns=["Ticker"]), use_container_width=True, hide_index=True)

# ── P&L bar chart ─────────────────────────────────────────────────────────────

st.markdown("### P&L by Position")
st.caption("Green = profit, Red = loss")

fig = px.bar(
    portfolio,
    x="Asset", y="P&L (%)",
    color="P&L (%)",
    color_continuous_scale=["#ff1744", "#21262d", "#00c853"],
    color_continuous_midpoint=0,
    text=portfolio["P&L (%)"].map(lambda x: f"{x:+.1f}%"),
)
fig.update_layout(**CHART_LAYOUT, height=350, coloraxis_showscale=False)
style_axes(fig)
fig.update_traces(textposition="outside")
st.plotly_chart(fig, use_container_width=True)

# ── Portfolio value over time ─────────────────────────────────────────────────

st.markdown("### Portfolio Value Over Time")
st.caption("Shows what your portfolio would be worth each day over the past year based on your current holdings")

tickers = tuple(portfolio["Ticker"].tolist())
hist    = load_history_multi(tickers)

if not hist.empty:
    portfolio_lookup = portfolio.set_index("Ticker")[["Shares", "Buy Price"]].to_dict("index")
    hist["VALUE"] = hist.apply(
        lambda r: r["CLOSE_PRICE"] * portfolio_lookup.get(r["TICKER"], {}).get("Shares", 0),
        axis=1
    )
    daily_total = hist.groupby("PRICE_DATE")["VALUE"].sum().reset_index()
    daily_total.columns = ["Date", "Portfolio Value"]

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=daily_total["Date"], y=daily_total["Portfolio Value"],
        fill="tozeroy", name="Portfolio Value",
        line=dict(color=GREEN, width=2),
        fillcolor="rgba(0,200,83,0.08)",
    ))
    fig2.add_hline(y=total_cost, line_dash="dash", line_color="orange",
                   annotation_text=f"Cost basis: £{total_cost:,.0f}")
    fig2.update_layout(**CHART_LAYOUT, height=350,
                       yaxis_title="Portfolio Value (£)", xaxis_title="")
    style_axes(fig2)
    st.plotly_chart(fig2, use_container_width=True)
