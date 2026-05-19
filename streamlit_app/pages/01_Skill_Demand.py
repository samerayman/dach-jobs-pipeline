import os
from pathlib import Path

import altair as alt
import duckdb
import streamlit as st

_default_warehouse = str(Path(__file__).resolve().parents[2] / ".warehouse.duckdb")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", _default_warehouse)

st.title("Skill Demand")
st.caption("How many postings mention each canonical skill?")


@st.cache_resource
def conn():
    return duckdb.connect(DUCKDB_PATH, read_only=True)


@st.cache_data(ttl=300)
def q(sql):
    return conn().execute(sql).df()


_skills_df = q("select distinct skill from gold.fct_skill_demand_daily order by skill")
skills = _skills_df["skill"].tolist()
selected = st.multiselect("Skills", skills, default=skills[:6] if skills else [])
country = st.selectbox("Country", ["All", "DE", "AT", "CH"])

if not selected:
    st.info("Pick at least one skill.")
    st.stop()

where = "where skill in ({})".format(",".join(f"'{s}'" for s in selected))
if country != "All":
    where += f" and country_code = '{country}'"

# `where` is built only from values present in our own gold tables
# (skills selected from a dropdown populated by a previous query, and a
# fixed country whitelist). No user-supplied free text reaches the SQL.
_sql = f"""
    select posting_date, skill, sum(posting_count) as postings
    from gold.fct_skill_demand_daily
    {where}
    group by 1, 2
    order by 1
"""  # noqa: S608
df = q(_sql)
chart = (
    alt.Chart(df)
    .mark_line()
    .encode(x="posting_date:T", y="postings:Q", color="skill:N")
    .properties(height=400)
)
st.altair_chart(chart, use_container_width=True)
