select
    cast(date as date) as date,
    country_code,
    channel,
    cast(spend_eur as decimal(12, 2)) as spend_eur,
    cast(impressions as bigint) as impressions,
    cast(clicks as bigint) as clicks,
    cast(conversions as integer) as conversions
from {{ source('raw', 'marketing_spend') }}
