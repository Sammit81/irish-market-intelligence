"""
Shared Snowflake connection helper.

Works in both environments:
  - Locally: reads from .env file via os.environ
  - Streamlit Cloud: reads from st.secrets (set in the app settings)

Includes retry logic so the app recovers silently if the Snowflake
warehouse is auto-suspended and needs a moment to resume.
"""
import os
import time
import streamlit as st
import snowflake.connector


def _credentials() -> dict:
    """Return connection kwargs from st.secrets (cloud) or .env (local)."""
    try:
        return dict(
            account   = st.secrets["SNOWFLAKE_ACCOUNT"],
            user      = st.secrets["SNOWFLAKE_USER"],
            password  = st.secrets["SNOWFLAKE_PASSWORD"],
            warehouse = st.secrets["SNOWFLAKE_WAREHOUSE"],
            database  = st.secrets["SNOWFLAKE_DATABASE"],
            schema    = st.secrets["SNOWFLAKE_SCHEMA"],
        )
    except Exception:
        from dotenv import load_dotenv
        load_dotenv()
        return dict(
            account   = os.environ["SNOWFLAKE_ACCOUNT"],
            user      = os.environ["SNOWFLAKE_USER"],
            password  = os.environ["SNOWFLAKE_PASSWORD"],
            warehouse = os.environ["SNOWFLAKE_WAREHOUSE"],
            database  = os.environ["SNOWFLAKE_DATABASE"],
            schema    = os.environ["SNOWFLAKE_SCHEMA"],
        )


def get_snowflake_connection(
    max_retries: int = 3,
    retry_delay: int = 5,
) -> snowflake.connector.SnowflakeConnection:
    """
    Connect to Snowflake, retrying up to max_retries times if the warehouse
    is resuming from auto-suspend. Shows a spinner so the user knows the app
    is working rather than broken.
    """
    creds = _credentials()
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return snowflake.connector.connect(**creds)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                with st.spinner(
                    f"Connecting to data warehouse… (attempt {attempt}/{max_retries})"
                ):
                    time.sleep(retry_delay)

    # All retries exhausted — show a friendly message instead of a raw traceback
    st.error(
        "Could not connect to the data warehouse after several attempts. "
        "This usually means Snowflake is resuming from a cold start. "
        "Please refresh the page in 30 seconds."
    )
    st.stop()
