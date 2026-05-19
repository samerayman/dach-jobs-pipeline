{# Remote-policy mix per day per country.

   Arbeitnow exposes a boolean `remote` flag per posting; we aggregate the
   share over a rolling window of new postings. Dashboards show this as
   "what fraction of new DACH postings allow remote, by week?" #}
{{ config(materialized = "table") }}

select
    date_trunc('day', posting_created_at) as posting_date,
    coalesce(country_code, 'XX')          as country_code,
    count(*)                              as posting_count,
    count_if(remote)                      as remote_count,
    count_if(remote)::double / nullif(count(*), 0) as remote_share
from {{ ref('silver_postings') }}
where posting_created_at is not null
group by posting_date, country_code
