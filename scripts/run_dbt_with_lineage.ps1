# Run dbt with OpenLineage emission to Marquez.
# Usage: .\scripts\run_dbt_with_lineage.ps1 build
param([Parameter(ValueFromRemainingArguments = $true)] $Args)

$env:OPENLINEAGE_URL = if ($env:OPENLINEAGE_URL) { $env:OPENLINEAGE_URL } else { "http://localhost:5000" }
$env:OPENLINEAGE_NAMESPACE = if ($env:OPENLINEAGE_NAMESPACE) { $env:OPENLINEAGE_NAMESPACE } else { "dach-jobs" }

Push-Location dbt
try {
    # `dbt-ol` is provided by openlineage-dbt; it wraps any dbt invocation.
    dbt-ol @Args
} finally {
    Pop-Location
}
