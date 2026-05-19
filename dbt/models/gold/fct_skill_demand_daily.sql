{# Daily count of postings mentioning each canonical skill.

   We join tags → dim_skill via the alias column, so 'py' folds into 'python'.
   This is the headline metric the dashboard exposes. #}
{{ config(materialized = "table") }}

with tagged as (
    select
        t.source_id,
        s.skill,
        date_trunc('day', p.posting_created_at) as posting_date,
        p.country_code,
        p.remote
    from {{ ref('silver_posting_tags') }} t
    join {{ ref('silver_postings')     }} p using (source, source_id)
    join {{ ref('dim_skill')           }} s on t.tag = s.alias
)

select
    posting_date,
    skill,
    country_code,
    count(distinct source_id)                          as posting_count,
    count(distinct source_id) filter (where remote)    as remote_posting_count
from tagged
group by posting_date, skill, country_code
