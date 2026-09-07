select
    product_id,
    product_name,
    category,
    brand,
    unit_cost_eur,
    unit_price_eur,
    round(unit_price_eur - unit_cost_eur, 2) as unit_margin_eur,
    round((unit_price_eur - unit_cost_eur) / nullif(unit_price_eur, 0) * 100, 2) as unit_margin_pct,
    launch_date
from {{ ref('stg_products') }}
