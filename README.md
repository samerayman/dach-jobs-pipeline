# DACH Tech Job Market Intelligence Pipeline

An end-to-end lakehouse that ingests, transforms, and analyzes tech job postings
across Germany, Austria, and Switzerland.

Built as a portfolio project — and used in practice to target the very
applications it analyzes.

## Architecture

```
                 ┌──────────────────┐
                 │  Arbeitnow API   │  (DACH jobs, free, no auth)
                 │  + future:       │
                 │  Adzuna, scrapes │
                 └────────┬─────────┘
                          │
                  ┌───────▼────────┐
                  │ Python producer│
                  └───────┬────────┘
                          │
                 ┌────────▼────────┐
                 │ Redpanda (Kafka)│   topic: jobs.raw
                 └────────┬────────┘
                          │
              ┌───────────▼──────────┐
              │ Dagster: bronze sink │  raw JSON → MinIO (Parquet/Iceberg)
              └───────────┬──────────┘
                          │
              ┌───────────▼──────────┐
              │ dbt (DuckDB on lake) │  silver → gold (SCD2, contracts, tests)
              └───────────┬──────────┘
                          │
              ┌───────────▼──────────┐
              │ FastAPI + Streamlit  │  serve insights
              └──────────────────────┘
```

## Stack

| Layer          | Tool                                  |
| -------------- | ------------------------------------- |
| Streaming      | Redpanda (Kafka API)                  |
| Object store   | MinIO (S3-compatible)                 |
| Table format   | Apache Iceberg (via PyIceberg)        |
| Orchestration  | Dagster                               |
| Transform      | dbt-core + dbt-duckdb                 |
| Quality        | dbt tests + Great Expectations        |
| Lineage        | OpenLineage → Marquez                 |
| Serving        | FastAPI + Streamlit                   |
| Infra          | Docker Compose (local), Terraform/GCP |
| CI             | GitHub Actions                        |

## Quickstart

```powershell
# 1. start infra
docker compose up -d

# 2. install python deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# 3. one-shot ingest from Arbeitnow → Kafka → MinIO bronze
python -m ingestion.arbeitnow

# 4. launch Dagster UI
dagster dev -m dach_jobs

# 5. (later) run dbt
cd dbt && dbt build
```

## Roadmap

- [x] Bronze layer: Arbeitnow → Kafka → MinIO
- [x] Silver: dedup, SCD2 via dbt snapshot on title/company/remote/location edits
- [x] Gold: skill demand, remote-policy facts, salary mentions, companies
- [x] dbt contracts on silver_postings, fct_postings, fct_skill_demand_daily
- [x] OpenLineage + Marquez wiring (via openlineage-dbt / `dbt-ol`)
- [x] Streamlit dashboard (`streamlit_app/`)
- [x] FastAPI read API (`api/`)
- [x] GitHub Actions CI (ruff, pytest, dagster load, dbt parse + compile, serve smoke)
- [x] Terraform GCP free-tier deploy (GCS + BigQuery + Cloud Run + Pub/Sub)
- [x] Backfill story (`docs/backfill.md`) with idempotency proof
- [x] Postmortem (`docs/postmortem.md`) — real Dagster + PEP 563 bug

## Why this exists

Most DE portfolio projects stop at "I moved a CSV with Airflow." This one solves
a real personal problem (targeting tech roles in DACH) end-to-end, with the
production hygiene a hiring manager actually scans for: contracts, tests,
lineage, idempotency, IaC, CI.
