select
    p.product_id,
    p.product_name,
    p.category,
    p.brand,
    count(distinct oi.order_id) as orders_count,
    sum(oi.quantity) as units_sold,
    sum(oi.line_total_eur) as gross_revenue_eur,
    sum(oi.line_margin_eur) as gross_margin_eur,
    round(sum(oi.line_margin_eur) / nullif(sum(oi.line_total_eur), 0) * 100, 2) as margin_pct,
    count(distinct r.return_id) as returns_count,
    round(count(distinct r.return_id)::float / nullif(count(distinct oi.order_id), 0) * 100, 2) as return_rate_pct
from {{ ref('dim_product') }} p
left join {{ ref('fct_order_items') }} oi on p.product_id = oi.product_id
left join {{ ref('fct_returns') }} r on oi.order_id = r.order_id
group by 1, 2, 3, 4
