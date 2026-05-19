{# Long-format tags table: one row per (posting, tag).
   Built from the JSON array on silver_postings. #}
{{ config(materialized = "table") }}

with unnested as (
    select
        source,
        source_id,
        last_seen_at,
        unnest(
            cast(json_extract(tags_json, '$') as varchar[])
        ) as tag_raw
    from {{ ref('silver_postings') }}
    where tags_json is not null and tags_json != '[]'
)

select
    source,
    source_id,
    last_seen_at,
    lower(trim(both '"' from tag_raw)) as tag
from unnested
where tag_raw is not null
