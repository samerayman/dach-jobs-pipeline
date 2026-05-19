{# Canonical skill dimension built from the seed taxonomy.
   The aliases column is pipe-delimited so a posting's free-text tag like
   "py" rolls up to canonical "python". #}
{{ config(materialized = "table") }}

with exploded as (
    select
        canonical,
        unnest(string_split(aliases, '|')) as alias
    from {{ ref('skill_taxonomy') }}
)

select distinct
    canonical                 as skill,
    lower(trim(alias))        as alias
from exploded
