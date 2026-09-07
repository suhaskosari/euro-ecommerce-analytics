with orders as (
    select * from {{ ref('stg_orders') }}
),
items_agg as (
    select order_id, count(*) as order_item_count
    from {{ ref('stg_order_items') }}
    group by 1
),
fx as (
    select date, currency_code, rate_to_eur
    from {{ ref('stg_exchange_rates') }}
)
select
    o.order_id,
    o.customer_id,
    o.order_date,
    o.country_code,
    o.channel,
    o.status,
    o.currency_code,
    coalesce(fx.rate_to_eur, 1.0) as fx_rate_to_eur,
    o.gross_amount_eur,
    o.discount_amount_eur,
    o.shipping_fee_eur,
    o.net_amount_eur,
    -- amount the customer actually saw charged in their own currency
    round(o.net_amount_eur * coalesce(fx.rate_to_eur, 1.0), 2) as net_amount_local_currency,
    p.payment_method,
    coalesce(items_agg.order_item_count, 0) as order_item_count,
    o.data_quality_flag
from orders o
left join items_agg on o.order_id = items_agg.order_id
left join {{ ref('stg_payments') }} p on o.order_id = p.order_id
left join fx on o.order_date = fx.date and o.currency_code = fx.currency_code
