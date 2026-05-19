"""Great Expectations checks against the gold layer.

dbt tests catch row-level issues at build time. This adds *suite-level*
expectations — column-level distributions, multi-table invariants — that
we run as a post-build gate. Failing here breaks CI.

Run: python -m ge.validate
"""

import os
import sys
from pathlib import Path

import duckdb
import great_expectations as gx

_default_warehouse = str(Path(__file__).resolve().parents[1] / ".warehouse.duckdb")
DUCKDB_PATH = os.getenv("DUCKDB_PATH", _default_warehouse)


def main() -> int:
    if not Path(DUCKDB_PATH).exists():
        print(f"warehouse missing: {DUCKDB_PATH} — run dbt build first")
        return 2

    conn = duckdb.connect(DUCKDB_PATH, read_only=True)

    context = gx.get_context(mode="ephemeral")

    fct_postings = conn.execute("select * from gold.fct_postings").df()
    fct_skill = conn.execute("select * from gold.fct_skill_demand_daily").df()
    fct_remote = conn.execute("select * from gold.fct_remote_policy_daily").df()

    failures: list[str] = []

    def check(df, name: str, fn, *args, **kwargs):
        batch = context.data_sources.pandas_default.read_dataframe(df, asset_name=name)
        result = fn(batch, *args, **kwargs)
        if not result.success:
            failures.append(f"{name}: {fn.__name__} -> {result.result}")

    # fct_postings invariants
    check(
        fct_postings, "fct_postings",
        lambda b: b.expect_column_values_to_not_be_null("posting_id"),
    )
    check(
        fct_postings, "fct_postings",
        lambda b: b.expect_column_values_to_be_unique("posting_id"),
    )
    check(
        fct_postings, "fct_postings",
        lambda b: b.expect_column_values_to_be_in_set(
            "country_code", ["DE", "AT", "CH", None]
        ),
    )

    # fct_skill_demand_daily invariants
    check(
        fct_skill, "fct_skill_demand_daily",
        lambda b: b.expect_column_values_to_be_between("posting_count", min_value=1),
    )
    check(
        fct_skill, "fct_skill_demand_daily",
        lambda b: b.expect_column_pair_values_a_to_be_greater_than_b(
            "posting_count", "remote_posting_count", or_equal=True
        ),
    )

    # fct_remote_policy_daily invariants
    check(
        fct_remote, "fct_remote_policy_daily",
        lambda b: b.expect_column_values_to_be_between(
            "remote_share", min_value=0, max_value=1
        ),
    )

    if failures:
        print("GE FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print(f"GE OK — {len(fct_postings):,} postings, {len(fct_skill):,} skill rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
