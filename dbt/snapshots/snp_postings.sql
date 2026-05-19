{# SCD2 over postings: captures every time title, company_name, remote, or
   location changes upstream. Lets downstream answer "what did this posting
   look like on date X?" #}

{% snapshot snp_postings %}
    {{
        config(
            target_schema = 'snapshots',
            unique_key = "source || '|' || source_id",
            strategy = 'check',
            check_cols = ['title', 'company_name', 'remote', 'location'],
            invalidate_hard_deletes = false,
        )
    }}

    select
        source,
        source_id,
        slug,
        title,
        company_name,
        remote,
        location,
        last_seen_at as snapshot_observed_at
    from {{ ref('silver_postings') }}

{% endsnapshot %}
