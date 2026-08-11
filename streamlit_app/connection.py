"""
Shared BigQuery connection helper.

Works in both environments:
  - Locally: reads GOOGLE_APPLICATION_CREDENTIALS (service account key file path)
    plus GCP_PROJECT_ID / BQ_DATASET from .env
  - Streamlit Cloud: reads the service account key from st.secrets["gcp_service_account"]
    plus st.secrets["GCP_PROJECT_ID"] / st.secrets["BQ_DATASET"]

Includes retry logic so the app recovers silently from transient BigQuery
connection hiccups.
"""
import os
import time
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account


@st.cache_resource
def _credentials():
    """Return (project_id, dataset, google.auth.Credentials|None) from st.secrets (cloud)
    or .env (local). None credentials means fall back to Application Default Credentials."""
    try:
        info    = dict(st.secrets["gcp_service_account"])
        project = st.secrets.get("GCP_PROJECT_ID", info["project_id"])
        dataset = st.secrets["BQ_DATASET"]
        creds   = service_account.Credentials.from_service_account_info(info)
        return project, dataset, creds
    except Exception:
        from dotenv import load_dotenv
        load_dotenv()
        project = os.environ["GCP_PROJECT_ID"]
        dataset = os.environ["BQ_DATASET"]
        return project, dataset, None


def qualified(table: str) -> str:
    """Fully-qualified, backtick-quoted `project.dataset.table` for use in SQL."""
    project, dataset, _ = _credentials()
    return f"`{project}.{dataset}.{table}`"


class _CursorAdapter:
    """Mimics the snowflake-connector cursor interface the app pages are written against."""
    def __init__(self, client: bigquery.Client):
        self._client = client
        self._df = None

    def execute(self, query: str):
        # BigQuery doesn't uppercase unquoted identifiers the way Snowflake did, and dbt's
        # table materialization doesn't reliably honor case-only rename aliases either — so
        # normalise here to match what every page in this app expects.
        self._df = self._client.query(query).to_dataframe()
        self._df.columns = self._df.columns.str.upper()
        return self

    def fetch_pandas_all(self):
        return self._df

    def close(self):
        pass


class _ConnectionAdapter:
    def __init__(self, client: bigquery.Client):
        self._client = client

    def cursor(self):
        return _CursorAdapter(self._client)

    def close(self):
        pass


@st.cache_resource
def get_bigquery_connection(
    max_retries: int = 4,
    retry_delay: int = 15,
) -> _ConnectionAdapter:
    """
    Connect to BigQuery, retrying up to max_retries times on transient errors.
    Shows a spinner so the user knows the app is working rather than broken.
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            project, _, creds = _credentials()
            client = bigquery.Client(project=project, credentials=creds)
            return _ConnectionAdapter(client)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                with st.spinner(
                    f"Connecting to data warehouse… (attempt {attempt}/{max_retries})"
                ):
                    time.sleep(retry_delay)

    st.error(
        "Could not connect to the data warehouse after several attempts. "
        "Check that the BigQuery service account and secrets are configured correctly."
    )
    st.stop()
