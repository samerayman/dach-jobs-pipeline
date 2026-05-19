"""Dagster Definitions: assets + resources + schedules."""

import shutil
import sys
from pathlib import Path

from dagster import (
    AssetSelection,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    load_assets_from_modules,
)
from dagster_dbt import DbtCliResource
from dotenv import load_dotenv

from dach_jobs import assets
from dach_jobs.assets import dbt_project
from dach_jobs.resources import KafkaConsumerResource, S3Resource

load_dotenv()


def _resolve_dbt_executable() -> str:
    """Find dbt.exe in the active venv first, then fall back to PATH.

    DbtCliResource validates the executable exists at construction time; on
    Windows `dbt` isn't on PATH unless the venv is activated, but the venv's
    Scripts/dbt.exe always exists once `pip install dbt-core` has run.
    """
    venv_bin = Path(sys.executable).parent
    for name in ("dbt.exe", "dbt"):
        candidate = venv_bin / name
        if candidate.exists():
            return str(candidate)
    found = shutil.which("dbt")
    if not found:
        raise RuntimeError("dbt executable not found in venv or on PATH")
    return found

all_assets = load_assets_from_modules([assets])

bronze_job = define_asset_job(
    name="bronze_job",
    selection=AssetSelection.groups("bronze"),
)

full_refresh_job = define_asset_job(
    name="full_refresh_job",
    selection=AssetSelection.all(),
)

bronze_schedule = ScheduleDefinition(
    job=bronze_job,
    cron_schedule="*/15 * * * *",
    name="bronze_every_15m",
)

dbt_schedule = ScheduleDefinition(
    job=full_refresh_job,
    cron_schedule="0 * * * *",
    name="full_refresh_hourly",
)

defs = Definitions(
    assets=all_assets,
    jobs=[bronze_job, full_refresh_job],
    schedules=[bronze_schedule, dbt_schedule],
    resources={
        "kafka": KafkaConsumerResource(),
        "s3": S3Resource(),
        "dbt": DbtCliResource(project_dir=dbt_project, dbt_executable=_resolve_dbt_executable()),
    },
)
