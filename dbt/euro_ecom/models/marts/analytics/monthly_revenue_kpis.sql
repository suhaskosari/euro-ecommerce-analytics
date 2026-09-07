with completed_orders as (
    select * from {{ ref('fct_orders') }} where status = 'completed'
),
monthly as (
    select
        date_trunc('month', order_date) as month,
        country_code,
        count(distinct order_id) as orders_count,
        count(distinct customer_id) as active_customers,
        sum(net_amount_eur) as net_revenue_eur,
        round(sum(net_amount_eur) / nullif(count(distinct order_id), 0), 2) as avg_order_value_eur
    from completed_orders
    group by 1, 2
)
select
    *,
    lag(net_revenue_eur) over (partition by country_code order by month) as prev_month_revenue_eur,
    round(
        (net_revenue_eur - lag(net_revenue_eur) over (partition by country_code order by month))
        / nullif(lag(net_revenue_eur) over (partition by country_code order by month), 0) * 100, 2
    ) as mom_revenue_growth_pct
from monthly
order by country_code, month
