select
    oi.order_id,
    oi.product_id,
    oi.quantity,
    oi.unit_price_eur,
    oi.line_total_eur,
    round(oi.quantity * p.unit_cost_eur, 2) as line_cost_eur,
    round(oi.line_total_eur - (oi.quantity * p.unit_cost_eur), 2) as line_margin_eur
from {{ ref('stg_order_items') }} oi
left join {{ ref('stg_products') }} p on oi.product_id = p.product_id
