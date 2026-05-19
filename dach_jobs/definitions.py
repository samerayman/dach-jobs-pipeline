"""Dagster Definitions: assets + resources + schedules."""

from __future__ import annotations

from dagster import (
    AssetSelection,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    load_assets_from_modules,
)
from dotenv import load_dotenv

from dach_jobs import assets
from dach_jobs.resources import KafkaConsumerResource, S3Resource

load_dotenv()

all_assets = load_assets_from_modules([assets])

bronze_job = define_asset_job(
    name="bronze_job",
    selection=AssetSelection.groups("bronze"),
)

# Runs every 15 minutes — frequent enough to feel streaming, cheap on local infra.
bronze_schedule = ScheduleDefinition(
    job=bronze_job,
    cron_schedule="*/15 * * * *",
    name="bronze_every_15m",
)

defs = Definitions(
    assets=all_assets,
    jobs=[bronze_job],
    schedules=[bronze_schedule],
    resources={
        "kafka": KafkaConsumerResource(),
        "s3": S3Resource(),
    },
)
