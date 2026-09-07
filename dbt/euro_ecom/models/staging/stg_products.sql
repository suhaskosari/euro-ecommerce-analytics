select
    product_id,
    product_name,
    category,
    brand,
    cast(unit_cost_eur as decimal(10, 2))  as unit_cost_eur,
    cast(unit_price_eur as decimal(10, 2)) as unit_price_eur,
    cast(launch_date as date) as launch_date
from {{ source('raw', 'products') }}
