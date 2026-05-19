import os
from pathlib import Path

import duckdb
import streamlit as st

_default_warehouse = str(Path(__file__).resolve().parents[2] / ".warehouse.duckdb")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", _default_warehouse)

st.title("Companies hiring in DACH")


@st.cache_resource
def conn():
    return duckdb.connect(DUCKDB_PATH, read_only=True)


@st.cache_data(ttl=300)
def q(sql):
    return conn().execute(sql).df()


df = q(
    """
    select company_name, posting_count, remote_posting_count,
           de_posting_count, at_posting_count, ch_posting_count,
           last_seen_at
    from gold.dim_company
    order by posting_count desc
    limit 100
    """
)
st.dataframe(df, use_container_width=True, hide_index=True)
