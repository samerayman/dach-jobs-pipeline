{# One row per current posting, denormalized for dashboarding. #}
{{ config(materialized = "table") }}

select
    source_id                        as posting_id,
    title,
    company_name,
    city_normalized                  as city,
    country_code,
    remote,
    url,
    posting_created_at,
    last_seen_at,
    date_trunc('day', posting_created_at) as posting_created_date
from {{ ref('silver_postings') }}
