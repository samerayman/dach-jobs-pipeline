"""Expose dbt models as Dagster assets.

Wiring dbt through dagster-dbt means a Dagster run can rebuild bronze, then
silver, then gold in a single DAG — and every dbt model shows up in the
Dagster UI with lineage, runtimes, and per-model status. This is the
upstream → downstream story you walk through in interviews.
"""

import os
from pathlib import Path

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

DBT_PROJECT_DIR = Path(__file__).resolve().parents[2] / "dbt"

# dbt looks here for profiles.yml. We co-locate it with the project so the
# whole thing is self-contained (no ~/.dbt/profiles.yml needed).
os.environ.setdefault("DBT_PROFILES_DIR", str(DBT_PROJECT_DIR))

dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
    target="dev",
)
# Regenerate manifest.json on import in dev mode if it's stale or missing.
# No-op in CI / packaged deploys where the manifest is pre-built.
dbt_project.prepare_if_dev()


@dbt_assets(manifest=dbt_project.manifest_path)
def dach_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
