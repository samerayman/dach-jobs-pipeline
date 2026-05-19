# Backfill story

## The problem

Arbeitnow's public board exposes ~10 pages of *currently active* postings.
The first useful backfill is "6 months of recent state, captured daily and
deduped." Running ingest once gives a snapshot; running it daily for ~180
days gives a longitudinal record — *and* an idempotency test, because the
same `(source_id)` appears across many runs.

## Strategy

1. **Daily snapshot ingestion.** Schedule `bronze_every_15m` keeps the
   stream warm; the bronze layer accumulates one parquet per drain.
2. **Idempotent silver.** `silver_postings` deduplicates with
   `row_number() over (partition by (source, source_id) order by
   ingested_at desc)`, so re-running silver on identical bronze produces
   identical output.
3. **SCD2 capture.** `snp_postings` records each time a posting's
   `title`, `company_name`, `remote`, or `location` changes between runs.
   This is the longitudinal value: "this posting was first listed in
   Hamburg, moved to Hamburg+remote two weeks later."
4. **Replay surface.** Bronze keeps the raw upstream JSON on
   `source_payload`. If the typed contract changes (new field, type
   change), we re-derive silver without re-fetching from upstream.

## Idempotency proof

Run the following twice; the assertion at the end holds.

```powershell
python -m ingestion.arbeitnow 3   # produce
dagster asset materialize -m dach_jobs --select bronze_arbeitnow_jobs
cd dbt; dbt build --target dev; cd ..

duckdb .warehouse.duckdb "
  -- Save current snapshot.
  create or replace table _proof as
  select * from gold.fct_postings order by posting_id;
"

# Second run with no new upstream data:
python -m ingestion.arbeitnow 3
dagster asset materialize -m dach_jobs --select bronze_arbeitnow_jobs
cd dbt; dbt build --target dev; cd ..

duckdb .warehouse.duckdb "
  -- Same row count, same content?
  select
    (select count(*) from _proof) = (select count(*) from gold.fct_postings) as row_count_stable,
    (select count(*) from (select * from _proof except select * from gold.fct_postings)) as new_rows_in_old,
    (select count(*) from (select * from gold.fct_postings except select * from _proof)) as new_rows_in_new;
"
```

Expected: `row_count_stable = true`, both `new_rows_in_*` = 0.

If the upstream board updated between runs, `new_rows_in_new > 0` reflects
*real* new postings, not duplication — and you can verify by inspecting
`silver_posting_tags` for the new `source_id`s.

## Historical fill from outside Arbeitnow

When we add a second source (Adzuna offers a generous free tier with 6
months of history), the same shape applies: producer → `jobs.raw` →
bronze. Silver dedup uses `(source, source_id)` so cross-source duplicates
stay separate; gold can blend them with `union all`.
