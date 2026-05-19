{# Best-effort salary extraction from free-text descriptions.

   Arbeitnow does not expose a structured salary field. We regex for the
   common EU pattern "€NN,NNN – €NN,NNN" or "NN,NNN EUR" and surface what
   we find. Coverage is intentionally low; this fact powers a "% of postings
   that publish salary" KPI more than a precise distribution. #}
{{ config(materialized = "table") }}

with extracted as (
    select
        source_id,
        title,
        country_code,
        description,
        regexp_extract(
            description,
            '(\d{2,3}[\.,]?\d{3})\s*(?:€|EUR|euro)',
            1
        ) as raw_salary
    from {{ ref('silver_postings') }}
    where description is not null
),

parsed as (
    select
        source_id,
        title,
        country_code,
        try_cast(replace(replace(raw_salary, '.', ''), ',', '') as integer) as salary_eur
    from extracted
    where raw_salary is not null and raw_salary != ''
)

select
    source_id,
    title,
    country_code,
    salary_eur,
    case
        when salary_eur < 40000  then '<40k'
        when salary_eur < 60000  then '40-60k'
        when salary_eur < 80000  then '60-80k'
        when salary_eur < 100000 then '80-100k'
        when salary_eur < 130000 then '100-130k'
        else '130k+'
    end as salary_band
from parsed
where salary_eur is not null
  and salary_eur between 20000 and 400000
