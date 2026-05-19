from datetime import UTC

from ingestion.contracts import ArbeitnowJob


def test_arbeitnow_job_minimal():
    job = ArbeitnowJob.model_validate(
        {
            "slug": "x",
            "company_name": "y",
            "title": "z",
            "url": "https://example.com",
            "created_at": 1_700_000_000,
        }
    )
    assert job.tags == []
    assert job.job_types == []
    assert job.remote is False
    assert job.created_at_dt.tzinfo == UTC


def test_arbeitnow_job_coerces_non_list_tags():
    job = ArbeitnowJob.model_validate(
        {
            "slug": "x",
            "company_name": "y",
            "title": "z",
            "url": "https://example.com",
            "created_at": 1_700_000_000,
            "tags": "python",  # upstream sometimes sends a single string
        }
    )
    assert job.tags == ["python"]
