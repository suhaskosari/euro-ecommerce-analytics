-- NOTE: revenue is joined at the country x month grain, not attributed
-- order-by-order to a channel (we don't have click-to-order tracking in this
-- dataset). blended_roas = total net revenue / total spend for that
-- country-month, a standard "blended" view -- not multi-touch attribution.
with spend as (
    select
        country_code,
        date_trunc('month', date) as month,
        channel,
        sum(spend_eur) as spend_eur,
        sum(impressions) as impressions,
        sum(clicks) as clicks,
        sum(conversions) as conversions
    from {{ ref('fct_marketing_spend') }}
    group by 1, 2, 3
),
revenue as (
    select
        country_code,
        date_trunc('month', order_date) as month,
        sum(net_amount_eur) as net_revenue_eur,
        count(distinct order_id) as orders_count
    from {{ ref('fct_orders') }}
    where status = 'completed'
    group by 1, 2
)
select
    s.country_code,
    s.month,
    s.channel,
    s.spend_eur,
    s.impressions,
    s.clicks,
    s.conversions,
    round(s.spend_eur / nullif(s.conversions, 0), 2) as cost_per_conversion_eur,
    r.net_revenue_eur,
    r.orders_count,
    round(r.net_revenue_eur / nullif(s.spend_eur, 0), 2) as blended_roas
from spend s
left join revenue r on s.country_code = r.country_code and s.month = r.month
order by s.country_code, s.month, s.channel
