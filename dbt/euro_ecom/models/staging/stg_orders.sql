select
    order_id,
    customer_id,
    cast(order_date as date) as order_date,
    country_code,
    channel,
    status,
    currency_code,
    cast(gross_amount_eur as decimal(12, 2))    as gross_amount_eur,
    cast(discount_amount_eur as decimal(12, 2)) as discount_amount_eur,
    cast(shipping_fee_eur as decimal(12, 2))    as shipping_fee_eur,
    cast(net_amount_eur as decimal(12, 2))      as net_amount_eur,
    data_quality_flag
from {{ source('raw', 'orders') }}
