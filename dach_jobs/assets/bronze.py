"""Bronze layer: drain Kafka, persist raw envelopes to MinIO as Parquet.

We partition by ingestion date so silver dedup can scan a bounded slice
when running incrementally. Each materialization writes one file keyed by
the materialization's run_id, which keeps replays idempotent at the file
level.
"""

import io
import json
import os
from datetime import UTC, datetime

import pyarrow as pa
import pyarrow.parquet as pq
from dagster import (
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    asset,
)

from dach_jobs.resources.kafka_consumer import KafkaConsumerResource
from dach_jobs.resources.s3 import S3Resource

BRONZE_BUCKET = os.getenv("BRONZE_BUCKET", "bronze")
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "jobs.raw")


@asset(
    group_name="bronze",
    description="Raw Arbeitnow ingestion envelopes drained from Kafka into MinIO Parquet.",
    compute_kind="kafka+s3",
)
def bronze_arbeitnow_jobs(
    context: AssetExecutionContext,
    kafka: KafkaConsumerResource,
    s3: S3Resource,
) -> MaterializeResult:
    values = kafka.drain(TOPIC_RAW)
    if not values:
        context.log.info("no new messages on %s", TOPIC_RAW)
        return MaterializeResult(metadata={"row_count": 0, "skipped": MetadataValue.bool(True)})

    rows: list[dict] = []
    bad = 0
    for raw in values:
        try:
            env = json.loads(raw)
        except json.JSONDecodeError:
            bad += 1
            continue
        if env.get("source") != "arbeitnow":
            continue
        rows.append(
            {
                "source": env.get("source"),
                "source_id": env.get("source_id"),
                "ingested_at": env.get("ingested_at"),
                "source_payload": json.dumps(env.get("source_payload", {})),
                "typed": json.dumps(env.get("typed")) if env.get("typed") else None,
            }
        )

    if not rows:
        return MaterializeResult(metadata={"row_count": 0, "bad": bad})

    table = pa.Table.from_pylist(rows)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="zstd")
    buf.seek(0)

    now = datetime.now(UTC)
    key = (
        f"arbeitnow/ingest_date={now:%Y-%m-%d}/"
        f"hour={now:%H}/run-{context.run_id}.parquet"
    )
    s3.put_bytes(
        bucket=BRONZE_BUCKET,
        key=key,
        body=buf.getvalue(),
        content_type="application/vnd.apache.parquet",
    )

    return MaterializeResult(
        metadata={
            "row_count": MetadataValue.int(len(rows)),
            "bad_messages": MetadataValue.int(bad),
            "s3_path": MetadataValue.path(f"s3://{BRONZE_BUCKET}/{key}"),
            "bytes_written": MetadataValue.int(buf.getbuffer().nbytes),
        }
    )
