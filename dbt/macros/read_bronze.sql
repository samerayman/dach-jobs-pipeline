{# Reads bronze parquet directly from MinIO via DuckDB httpfs.

   We don't use {{ source() }} for the read because dbt-duckdb's source-as-
   external-location convention varies by version; reading via read_parquet
   with a glob is unambiguous and lets dbt parse the model with no infra
   available (the SELECT only fires at run time).
#}
{% macro read_bronze() %}
    read_parquet('{{ var("bronze_glob") }}', hive_partitioning = true)
{% endmacro %}
