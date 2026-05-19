# Architecture

## Layers

**Bronze** — raw ingestion envelopes, partitioned by `ingest_date/hour`.
Schema: `(source, source_id, ingested_at, source_payload, typed)`. The full
upstream JSON is retained on `source_payload`, so the typed contract can
evolve without re-ingesting history.

**Silver** — `silver_postings` (one row per current posting; latest ingest
wins) and `silver_posting_tags` (long-format). City and country are
heuristic-normalized. dbt contracts enforce schema. `snp_postings` snapshot
captures SCD2 history.

**Gold** — denormalized facts and dims: `fct_postings`, `fct_skill_demand_daily`,
`fct_remote_policy_daily`, `fct_salary_mentions`, `dim_company`, `dim_skill`.
Contracts enforced; `dbt_expectations` adds distribution checks.

## Flow

1. `ingestion.arbeitnow` pulls pages, validates each posting via Pydantic
   (`ArbeitnowJob`), wraps it in an `IngestionEnvelope`, and produces JSON
   to Kafka `jobs.raw`.
2. Dagster asset `bronze_arbeitnow_jobs` drains the topic on schedule
   (every 15m), batches rows into a single Parquet file per run, writes to
   `s3://bronze/arbeitnow/ingest_date=YYYY-MM-DD/hour=HH/run-<id>.parquet`.
3. dagster-dbt orchestrates `dbt build` — staging → silver → snapshot →
   gold. dbt-duckdb reads bronze parquet through httpfs.
4. Streamlit and FastAPI read gold from the same DuckDB warehouse file.

## Lineage

`openlineage-dbt` (run via `dbt-ol`) emits events to Marquez at
`http://localhost:5000`; UI at `http://localhost:3001`. Dagster's own UI
shows asset-graph lineage including the bronze → dbt boundary.

## Idempotency

- **Bronze**: each materialization writes a fresh `run-<run_id>.parquet`
  and commits Kafka offsets only after the upload succeeds. A failed run
  leaves no file and replays the same offsets next run.
- **Silver**: pure SQL on bronze — fully reproducible from inputs.
- **Snapshot**: dbt's `check` strategy only writes on actual column drift.
- **Gold**: rebuilt from silver every run; tables are full re-materializations.

## Why DuckDB locally and BigQuery in cloud

DuckDB on a local file is the fastest possible dev loop for dbt-based stacks
in 2026. BigQuery in cloud is the path of least friction inside GCP's
always-free tier. dbt's adapter abstraction means model SQL is shared
verbatim between the two; only `profiles.yml` changes.
