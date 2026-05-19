"""Read-only FastAPI over the gold layer.

Why: proves the same data that powers the dashboard can be served as JSON to
arbitrary consumers (mobile apps, alerting, downstream notebooks). DuckDB is
opened read-only so the API and the dashboard can run side-by-side against
the same warehouse file.

Run: uvicorn api.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import duckdb
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

_default_warehouse = str(Path(__file__).resolve().parents[1] / ".warehouse.duckdb")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", _default_warehouse)

_conn: duckdb.DuckDBPyConnection | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _conn
    if Path(DUCKDB_PATH).exists():
        _conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    yield
    if _conn is not None:
        _conn.close()


app = FastAPI(
    title="DACH Jobs API",
    description="Read API over the gold layer.",
    version="0.1.0",
    lifespan=lifespan,
)


def get_conn() -> duckdb.DuckDBPyConnection:
    if _conn is None:
        raise HTTPException(
            503, f"Warehouse not initialized at {DUCKDB_PATH}. Run dbt build first."
        )
    return _conn


class Posting(BaseModel):
    posting_id: str
    title: str
    company_name: str | None
    city: str | None
    country_code: str | None
    remote: bool
    url: str | None


class SkillDemand(BaseModel):
    posting_date: str
    skill: str
    country_code: str | None
    posting_count: int


@app.get("/health")
def health():
    return {"status": "ok", "warehouse_present": Path(DUCKDB_PATH).exists()}


@app.get("/postings", response_model=list[Posting])
def list_postings(
    conn: Annotated[duckdb.DuckDBPyConnection, Depends(get_conn)],
    country: str | None = Query(None, pattern="^(DE|AT|CH)$"),
    remote: bool | None = None,
    skill: str | None = None,
    limit: int = Query(50, ge=1, le=500),
):
    sql = """
        select p.posting_id, p.title, p.company_name, p.city, p.country_code,
               p.remote, p.url
        from gold.fct_postings p
    """
    params: list = []
    where: list[str] = []
    if country:
        where.append("p.country_code = ?")
        params.append(country)
    if remote is not None:
        where.append("p.remote = ?")
        params.append(remote)
    if skill:
        sql += """
            join silver.silver_posting_tags t on t.source_id = p.posting_id
            join gold.dim_skill s on s.alias = t.tag
        """
        where.append("s.skill = ?")
        params.append(skill.lower())
    if where:
        sql += " where " + " and ".join(where)
    sql += " order by p.posting_created_at desc nulls last limit ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    cols = ["posting_id", "title", "company_name", "city", "country_code", "remote", "url"]
    return [dict(zip(cols, r, strict=False)) for r in rows]


@app.get("/skills/top", response_model=list[SkillDemand])
def top_skills(
    conn: Annotated[duckdb.DuckDBPyConnection, Depends(get_conn)],
    days: int = Query(30, ge=1, le=365),
    country: str | None = Query(None, pattern="^(DE|AT|CH)$"),
    limit: int = Query(20, ge=1, le=200),
):
    sql = """
        select cast(posting_date as varchar) as posting_date, skill, country_code,
               sum(posting_count)::int as posting_count
        from gold.fct_skill_demand_daily
        where posting_date >= current_date - cast(? as integer) * interval 1 day
    """
    params: list = [days]
    if country:
        sql += " and country_code = ?"
        params.append(country)
    sql += " group by 1, 2, 3 order by posting_count desc limit ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    cols = ["posting_date", "skill", "country_code", "posting_count"]
    return [dict(zip(cols, r, strict=False)) for r in rows]
