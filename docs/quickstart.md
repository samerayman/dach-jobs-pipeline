# Quickstart

End-to-end in ~5 minutes on a laptop.

```powershell
cd C:\Users\Samer\dach-jobs-pipeline

# 1. infra
docker compose up -d

# 2. python env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,serve,quality,lineage]"
Copy-Item .env.example .env

# 3. ingest 3 pages of DACH jobs → Kafka → MinIO
python -m ingestion.arbeitnow 3
dagster asset materialize -m dach_jobs --select bronze_arbeitnow_jobs

# 4. build the warehouse with dbt (lineage events go to Marquez)
cd dbt
dbt deps --profiles-dir .
$env:DBT_PROFILES_DIR = "."
.\..\scripts\run_dbt_with_lineage.ps1 build
cd ..

# 5. data-quality gate
python -m ge.validate

# 6. dashboard + API
streamlit run streamlit_app/Home.py        # http://localhost:8501
uvicorn api.main:app --reload --port 8000  # http://localhost:8000/docs
```

## UIs you can open

| Service           | URL                          | Credentials              |
| ----------------- | ---------------------------- | ------------------------ |
| Dagster           | http://localhost:3000        | —                        |
| MinIO console     | http://localhost:9001        | minioadmin / minioadmin  |
| Redpanda console  | http://localhost:8080        | —                        |
| Marquez (lineage) | http://localhost:3001        | —                        |
| Streamlit         | http://localhost:8501        | —                        |
| FastAPI docs      | http://localhost:8000/docs   | —                        |

## What runs where

- `dagster dev -m dach_jobs` — orchestration UI; materialize assets, watch
  schedules, browse lineage.
- `streamlit run streamlit_app/Home.py` — the demo dashboard.
- `uvicorn api.main:app` — the read API.
- `dbt-ol build` (from `dbt/`) — transforms with OpenLineage emission.
- `python -m ge.validate` — data-quality gate on gold.
- `pytest` — unit tests (hermetic, no infra needed).
- `ruff check .` — lint.
