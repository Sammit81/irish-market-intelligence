"""
Shared styling for the Irish Market Intelligence Dashboard.
Import this in every page to keep the look consistent.
"""
import streamlit as st

PLOTLY_TEMPLATE = "plotly_dark"
GREEN  = "#00c853"
RED    = "#ff1744"
GREY   = "#8b949e"
BG     = "#0d1117"
CARD_BG = "#161b22"

CHART_LAYOUT = dict(
    template        = PLOTLY_TEMPLATE,
    paper_bgcolor   = CARD_BG,
    plot_bgcolor    = CARD_BG,
    font            = dict(family="sans-serif", color="#e6edf3"),
    margin          = dict(l=40, r=20, t=50, b=40),
)

# Call this on every figure after update_layout — keeps grid colours consistent
# without putting xaxis/yaxis inside CHART_LAYOUT (which would conflict any time
# a chart also passes xaxis= or yaxis= to update_layout).
def style_axes(fig):
    fig.update_xaxes(gridcolor="#21262d", showgrid=True)
    fig.update_yaxes(gridcolor="#21262d", showgrid=True)
    return fig


CSS = """
<style>
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 3.5rem; padding-bottom: 2rem;}
[data-testid="metric-container"] {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 16px 20px;
}
[data-testid="metric-container"] label {
    color: #8b949e !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {font-size: 1.6rem !important; font-weight: 700 !important;}
[data-testid="stMetricDelta"] svg {display: none;}
[data-testid="stSidebar"] {background-color: #161b22; border-right: 1px solid #21262d;}
[data-testid="stDataFrame"] {border: 1px solid #21262d; border-radius: 8px;}
hr {border-color: #21262d !important;}
[data-testid="stInfo"] {background-color: #1c2b1e; border-left: 4px solid #00c853; border-radius: 4px;}
</style>
"""


def apply_global_css():
    st.html(CSS)


def sidebar_info(last_updated: str = None):
    """Standard sidebar for every page."""
    with st.sidebar:
        st.markdown("## 🇮🇪 Irish Market Intelligence")
        st.caption("Live data · Snowflake · dbt")
        st.divider()
        st.markdown("**Pages**")
        st.markdown("📈 Market Overview")
        st.markdown("🔍 Stock Deep Dive")
        st.markdown("⚖️ Compare Assets")
        st.markdown("📉 Risk Analysis")
        st.divider()
        if last_updated:
            st.caption(f"Last updated: {last_updated}")
        st.caption("Data: Yahoo Finance via yfinance")
        st.caption("Warehouse: Snowflake")
        st.caption("Models: dbt")
