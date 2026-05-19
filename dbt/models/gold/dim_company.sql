{{ config(materialized = "table") }}

select
    company_name,
    count(*)                                 as posting_count,
    count_if(remote)                         as remote_posting_count,
    count_if(country_code = 'DE')            as de_posting_count,
    count_if(country_code = 'AT')            as at_posting_count,
    count_if(country_code = 'CH')            as ch_posting_count,
    min(posting_created_at)                  as first_seen_at,
    max(last_seen_at)                        as last_seen_at
from {{ ref('silver_postings') }}
where company_name is not null
group by company_name
