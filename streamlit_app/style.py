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
    xaxis           = dict(gridcolor="#21262d", showgrid=True),
    yaxis           = dict(gridcolor="#21262d", showgrid=True),
    margin          = dict(l=40, r=20, t=50, b=40),
)


def apply_global_css():
    st.markdown("""
    <style>
    /* Hide Streamlit default header */
    #MainMenu, footer {visibility: hidden;}

    /* Page padding */
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}

    /* KPI card style */
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
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricDelta"] svg {display: none;}

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #21262d;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border: 1px solid #21262d;
        border-radius: 8px;
    }

    /* Divider */
    hr {border-color: #21262d !important;}

    /* Info/success boxes */
    [data-testid="stInfo"] {
        background-color: #1c2b1e;
        border-left: 4px solid #00c853;
        border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)


def sidebar_info(last_updated: str = None):
    """Standard sidebar for every page."""
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/Flag_of_Ireland.svg/320px-Flag_of_Ireland.svg.png", width=80)
        st.markdown("## Irish Market Intelligence")
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
