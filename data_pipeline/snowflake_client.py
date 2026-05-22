"""Snowflake connection — reads credentials from .env."""
import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection() -> snowflake.connector.SnowflakeConnection:
    warehouse = os.environ["SNOWFLAKE_WAREHOUSE"].strip()
    database  = os.environ["SNOWFLAKE_DATABASE"].strip()
    schema    = os.environ["SNOWFLAKE_SCHEMA"].strip()

    conn = snowflake.connector.connect(
        account   = os.environ["SNOWFLAKE_ACCOUNT"].strip(),
        user      = os.environ["SNOWFLAKE_USER"].strip(),
        password  = os.environ["SNOWFLAKE_PASSWORD"].strip(),
        warehouse = warehouse,
        database  = database,
        schema    = schema,
    )
    # Explicitly set context in case connection parameters aren't honoured
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {warehouse}")
    cur.execute(f"USE DATABASE {database}")
    cur.execute(f"USE SCHEMA {schema}")
    cur.close()
    return conn
