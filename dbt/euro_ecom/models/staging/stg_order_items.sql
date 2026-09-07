select
    order_id,
    product_id,
    cast(quantity as integer) as quantity,
    cast(unit_price_eur as decimal(10, 2)) as unit_price_eur,
    cast(line_total_eur as decimal(12, 2)) as line_total_eur
from {{ source('raw', 'order_items') }}
