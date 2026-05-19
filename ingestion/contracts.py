"""Data contracts at the ingestion boundary.

These shapes define what we promise downstream layers. Any drift in upstream
APIs is caught here, not in bronze SQL three layers later.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ArbeitnowJob(BaseModel):
    """One job posting as returned by https://www.arbeitnow.com/api/job-board-api.

    Fields that the upstream sometimes omits are Optional with sane defaults.
    Unknown fields are *kept* on the raw payload (we store full JSON in bronze),
    but typed access goes through this model.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    slug: str
    company_name: str
    title: str
    description: str = ""
    remote: bool = False
    url: str
    tags: list[str] = Field(default_factory=list)
    job_types: list[str] = Field(default_factory=list)
    location: str = ""
    created_at: int  # unix seconds from Arbeitnow

    @field_validator("tags", "job_types", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        return [str(v)]

    @property
    def created_at_dt(self) -> datetime:
        return datetime.fromtimestamp(self.created_at, tz=UTC)


class IngestionEnvelope(BaseModel):
    """Wrapper we publish to Kafka. Source + ingestion metadata + raw payload.

    Keeping the raw payload (`source_payload`) means bronze is replayable even
    if our typed contract evolves. The typed fields make downstream SQL cheap.
    """

    model_config = ConfigDict(extra="forbid")

    source: str  # e.g. "arbeitnow"
    source_id: str  # stable id from the source (slug for Arbeitnow)
    ingested_at: datetime
    source_payload: dict[str, Any]
    typed: ArbeitnowJob | None = None
