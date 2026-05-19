"""Arbeitnow ingestion: API client + entrypoint that ships to Kafka.

The client paginates the public job board API, validates each posting against
our Pydantic contract, wraps it in an IngestionEnvelope, and produces it to
the `jobs.raw` topic. Designed to be safe to run repeatedly (idempotency is
enforced downstream on (source, source_id, created_at)).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
import structlog
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ingestion.contracts import ArbeitnowJob, IngestionEnvelope
from ingestion.kafka_producer import JobsProducer

load_dotenv()

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
log = structlog.get_logger()


ARBEITNOW_BASE_URL = os.getenv(
    "ARBEITNOW_BASE_URL", "https://www.arbeitnow.com/api/job-board-api"
)


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type((httpx.HTTPError,)),
)
def _fetch_page(client: httpx.Client, page: int) -> dict:
    resp = client.get(ARBEITNOW_BASE_URL, params={"page": page}, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


def iter_jobs(max_pages: int = 10) -> Iterator[IngestionEnvelope]:
    """Yield envelopes page by page. Stops when the API returns no data."""
    with httpx.Client(headers={"User-Agent": "dach-jobs-pipeline/0.1"}) as client:
        for page in range(1, max_pages + 1):
            payload = _fetch_page(client, page)
            data = payload.get("data") or []
            if not data:
                log.info("arbeitnow.page.empty", page=page)
                break
            log.info("arbeitnow.page.fetched", page=page, count=len(data))
            for raw in data:
                try:
                    typed = ArbeitnowJob.model_validate(raw)
                except Exception as e:  # validation drift = bronze still keeps raw
                    log.warning("arbeitnow.validation.failed", error=str(e), slug=raw.get("slug"))
                    typed = None

                yield IngestionEnvelope(
                    source="arbeitnow",
                    source_id=str(raw.get("slug", "")),
                    ingested_at=datetime.now(UTC),
                    source_payload=raw,
                    typed=typed,
                )


def run(max_pages: int = 10) -> int:
    """Fetch and publish. Returns count of messages produced."""
    producer = JobsProducer()
    n = 0
    for env in iter_jobs(max_pages=max_pages):
        producer.produce(
            key=env.source_id.encode("utf-8") or b"unknown",
            value=env.model_dump_json().encode("utf-8"),
        )
        n += 1
        if n % 100 == 0:
            producer.flush(timeout=5.0)
            log.info("arbeitnow.flushed", produced=n)
    producer.flush(timeout=30.0)
    log.info("arbeitnow.done", produced=n)
    return n


if __name__ == "__main__":
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    count = run(max_pages=pages)
    print(json.dumps({"produced": count}))
