"""
Shared Snowflake connection helper.

Works in both environments:
  - Locally: reads from .env file via os.environ
  - Streamlit Cloud: reads from st.secrets (set in the app settings)
"""
import os
import streamlit as st
import snowflake.connector


def get_snowflake_connection() -> snowflake.connector.SnowflakeConnection:
    try:
        # Streamlit Cloud — secrets configured in app settings
        return snowflake.connector.connect(
            account   = st.secrets["SNOWFLAKE_ACCOUNT"],
            user      = st.secrets["SNOWFLAKE_USER"],
            password  = st.secrets["SNOWFLAKE_PASSWORD"],
            warehouse = st.secrets["SNOWFLAKE_WAREHOUSE"],
            database  = st.secrets["SNOWFLAKE_DATABASE"],
            schema    = st.secrets["SNOWFLAKE_SCHEMA"],
        )
    except Exception:
        # Local — reads from .env
        from dotenv import load_dotenv
        load_dotenv()
        return snowflake.connector.connect(
            account   = os.environ["SNOWFLAKE_ACCOUNT"],
            user      = os.environ["SNOWFLAKE_USER"],
            password  = os.environ["SNOWFLAKE_PASSWORD"],
            warehouse = os.environ["SNOWFLAKE_WAREHOUSE"],
            database  = os.environ["SNOWFLAKE_DATABASE"],
            schema    = os.environ["SNOWFLAKE_SCHEMA"],
        )
