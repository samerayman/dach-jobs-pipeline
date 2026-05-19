"""Smoke tests for the Arbeitnow ingestion path.

We mock the HTTP layer with respx so this is hermetic and fast — no live API,
no Kafka, no Docker dependency. Tests the two things that matter at this layer:
1. Pagination terminates when a page returns no data.
2. Validation drift is tolerated (bad rows still produce envelopes with raw payload).
"""

from __future__ import annotations

import httpx
import respx

from ingestion.arbeitnow import ARBEITNOW_BASE_URL, iter_jobs
from ingestion.contracts import ArbeitnowJob, IngestionEnvelope


def _good_row(slug: str = "senior-data-engineer-berlin") -> dict:
    return {
        "slug": slug,
        "company_name": "Acme GmbH",
        "title": "Senior Data Engineer",
        "description": "Build pipelines.",
        "remote": True,
        "url": f"https://www.arbeitnow.com/view/{slug}",
        "tags": ["python", "dbt"],
        "job_types": ["full-time"],
        "location": "Berlin",
        "created_at": 1_700_000_000,
    }


@respx.mock
def test_iter_jobs_paginates_then_stops():
    respx.get(ARBEITNOW_BASE_URL, params={"page": 1}).mock(
        return_value=httpx.Response(200, json={"data": [_good_row("a"), _good_row("b")]})
    )
    respx.get(ARBEITNOW_BASE_URL, params={"page": 2}).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    envelopes = list(iter_jobs(max_pages=5))

    assert len(envelopes) == 2
    assert all(isinstance(e, IngestionEnvelope) for e in envelopes)
    assert {e.source_id for e in envelopes} == {"a", "b"}
    assert all(isinstance(e.typed, ArbeitnowJob) for e in envelopes)


@respx.mock
def test_iter_jobs_tolerates_validation_drift():
    bad_row = {"slug": "broken"}  # missing required fields
    respx.get(ARBEITNOW_BASE_URL, params={"page": 1}).mock(
        return_value=httpx.Response(200, json={"data": [bad_row, _good_row("ok")]})
    )
    respx.get(ARBEITNOW_BASE_URL, params={"page": 2}).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    envelopes = list(iter_jobs(max_pages=5))

    assert len(envelopes) == 2  # both rows produce envelopes
    broken, good = envelopes
    assert broken.typed is None
    assert broken.source_payload == bad_row  # raw payload preserved for replay
    assert good.typed is not None
