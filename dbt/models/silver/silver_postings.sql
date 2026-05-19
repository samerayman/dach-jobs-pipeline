{# Silver: one row per unique posting (latest ingestion wins on conflict).

   "Same posting" = same (source, source_id). We keep the most recently
   ingested version. Edits over time are captured by snp_postings (SCD2).
#}
{{ config(materialized = "table") }}

with deduped as (
    select
        *,
        row_number() over (
            partition by source, source_id
            order by ingested_at desc, posting_created_at desc
        ) as rn
    from {{ ref('stg_arbeitnow_postings') }}
),

latest as (
    select
        source,
        source_id,
        slug,
        company_name,
        title,
        description,
        url,
        location,
        remote,
        tags_json,
        job_types_json,
        posting_created_at,
        ingested_at as last_seen_at
    from deduped
    where rn = 1
),

enriched as (
    select
        *,
        case
            when lower(location) like '%berlin%'    then 'Berlin'
            when lower(location) like '%munich%'    or lower(location) like '%münchen%' then 'Munich'
            when lower(location) like '%hamburg%'   then 'Hamburg'
            when lower(location) like '%frankfurt%' then 'Frankfurt'
            when lower(location) like '%cologne%'   or lower(location) like '%köln%'    then 'Cologne'
            when lower(location) like '%vienna%'    or lower(location) like '%wien%'    then 'Vienna'
            when lower(location) like '%zurich%'    or lower(location) like '%zürich%'  then 'Zurich'
            when lower(location) like '%berlin, germany%' then 'Berlin'
            else nullif(trim(location), '')
        end as city_normalized,
        case
            when lower(location) like '%germany%'      or lower(location) like '%berlin%' or lower(location) like '%munich%'
              or lower(location) like '%münchen%'      or lower(location) like '%hamburg%' or lower(location) like '%köln%'
              or lower(location) like '%frankfurt%'    or lower(location) like '%cologne%'
              then 'DE'
            when lower(location) like '%austria%'  or lower(location) like '%vienna%' or lower(location) like '%wien%' then 'AT'
            when lower(location) like '%switzerland%' or lower(location) like '%zurich%' or lower(location) like '%zürich%' then 'CH'
            else null
        end as country_code
    from latest
)

select * from enriched
