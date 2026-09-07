-- Lifecycle staging is relative to the last observed order date in the dataset
-- (not wall-clock "today"), so the demo reflects the state of the business at
-- the end of the simulated period rather than drifting stale as time passes.
with as_of as (
    select max(order_date) as as_of_date from {{ ref('fct_orders') }} where status = 'completed'
),
orders as (
    select * from {{ ref('fct_orders') }} where status = 'completed'
),
agg as (
    select
        customer_id,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        count(distinct order_id) as total_orders,
        sum(net_amount_eur) as total_net_revenue_eur,
        round(sum(net_amount_eur) / nullif(count(distinct order_id), 0), 2) as avg_order_value_eur
    from orders
    group by 1
)
select
    c.customer_id,
    c.country_code,
    c.region,
    c.acquisition_channel,
    c.signup_date,
    a.first_order_date,
    a.last_order_date,
    coalesce(a.total_orders, 0) as total_orders,
    coalesce(a.total_net_revenue_eur, 0) as total_net_revenue_eur,
    a.avg_order_value_eur,
    date_diff('day', a.first_order_date, a.last_order_date) as customer_lifespan_days,
    case
        when a.total_orders is null then 'never_purchased'
        when date_diff('day', a.last_order_date, (select as_of_date from as_of)) <= 90 then 'active'
        when date_diff('day', a.last_order_date, (select as_of_date from as_of)) <= 180 then 'at_risk'
        else 'churned'
    end as lifecycle_stage
from {{ ref('dim_customer') }} c
left join agg a on c.customer_id = a.customer_id
