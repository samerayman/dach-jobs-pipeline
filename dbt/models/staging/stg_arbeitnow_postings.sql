{{ config(materialized = "view") }}

with raw as (
    select * from {{ read_bronze() }}
),

parsed as (
    select
        source,
        source_id,
        cast(ingested_at as timestamp) as ingested_at,
        cast(json_extract_string(typed, '$.slug')         as varchar)   as slug,
        cast(json_extract_string(typed, '$.company_name') as varchar)   as company_name,
        cast(json_extract_string(typed, '$.title')        as varchar)   as title,
        cast(json_extract_string(typed, '$.description')  as varchar)   as description,
        cast(json_extract_string(typed, '$.url')          as varchar)   as url,
        cast(json_extract_string(typed, '$.location')     as varchar)   as location,
        cast(json_extract(typed, '$.remote')              as boolean)   as remote,
        cast(json_extract(typed, '$.tags')                as varchar)   as tags_json,
        cast(json_extract(typed, '$.job_types')           as varchar)   as job_types_json,
        cast(json_extract(typed, '$.created_at')          as bigint)    as created_at_epoch,
        to_timestamp(cast(json_extract(typed, '$.created_at') as bigint)) as posting_created_at
    from raw
    where typed is not null
)

select * from parsed
