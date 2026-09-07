select
    date,
    country_code,
    channel,
    spend_eur,
    impressions,
    clicks,
    conversions,
    round(clicks::float / nullif(impressions, 0), 4) as ctr,
    round(conversions::float / nullif(clicks, 0), 4) as click_to_conversion_rate,
    round(spend_eur / nullif(conversions, 0), 2) as cost_per_conversion_eur
from {{ ref('stg_marketing_spend') }}
