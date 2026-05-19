"""Streamlit dashboard — DACH tech job market.

Reads gold tables straight from DuckDB. Pages live in `pages/`.
Run: streamlit run streamlit_app/Home.py
"""

import os
from pathlib import Path

import duckdb
import streamlit as st

_default_warehouse = str(Path(__file__).resolve().parents[1] / ".warehouse.duckdb")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", _default_warehouse)

st.set_page_config(page_title="DACH Tech Job Market", page_icon="📊", layout="wide")
st.title("DACH Tech Job Market Intelligence")
st.caption("Live view over gold tables built by dbt from Arbeitnow ingestion.")


@st.cache_resource
def get_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DUCKDB_PATH, read_only=True)


@st.cache_data(ttl=300)
def query(sql: str):
    return get_conn().execute(sql).df()


if not Path(DUCKDB_PATH).exists():
    st.warning(
        f"Warehouse not found at {DUCKDB_PATH}. "
        "Run `dbt build` first to populate gold tables."
    )
    st.stop()

col1, col2, col3, col4 = st.columns(4)
try:
    totals = query(
        "select count(*) as postings, count_if(remote) as remote_count, "
        "count(distinct company_name) as companies, "
        "count(distinct country_code) as countries from gold.fct_postings"
    ).iloc[0]
    col1.metric("Postings", f"{totals['postings']:,}")
    col2.metric("Remote", f"{totals['remote_count']:,}")
    col3.metric("Companies", f"{totals['companies']:,}")
    col4.metric("Countries", f"{totals['countries']:,}")
except duckdb.CatalogException:
    st.error("gold.fct_postings is missing. Run `dbt build` to create it.")
    st.stop()

st.subheader("Top skills in DACH (last 30 days)")
top_skills = query(
    """
    select skill, sum(posting_count) as postings
    from gold.fct_skill_demand_daily
    where posting_date >= current_date - interval 30 day
    group by skill
    order by postings desc
    limit 20
    """
)
if top_skills.empty:
    st.info("No skill data yet. Run a fresh ingest + `dbt build`.")
else:
    st.bar_chart(top_skills, x="skill", y="postings")

st.subheader("Remote share over time")
remote = query(
    """
    select date_trunc('week', posting_date) as week, country_code,
           sum(remote_count)::double / nullif(sum(posting_count), 0) as remote_share
    from gold.fct_remote_policy_daily
    where country_code in ('DE','AT','CH')
    group by 1, 2
    order by 1
    """
)
if not remote.empty:
    st.line_chart(remote.pivot(index="week", columns="country_code", values="remote_share"))
