with orders as (
    select customer_id, order_date from {{ ref('fct_orders') }} where status = 'completed'
),
first_order as (
    select customer_id, date_trunc('month', min(order_date)) as cohort_month
    from orders
    group by 1
),
activity as (
    select o.customer_id, f.cohort_month, date_trunc('month', o.order_date) as order_month
    from orders o
    join first_order f on o.customer_id = f.customer_id
),
cohort_activity as (
    select
        cohort_month,
        order_month,
        date_diff('month', cohort_month, order_month) as months_since_first_order,
        count(distinct customer_id) as active_customers
    from activity
    group by 1, 2, 3
),
cohort_size as (
    select cohort_month, active_customers as cohort_size
    from cohort_activity
    where months_since_first_order = 0
)
select
    ca.cohort_month,
    ca.order_month,
    ca.months_since_first_order,
    ca.active_customers,
    cs.cohort_size,
    round(ca.active_customers::float / nullif(cs.cohort_size, 0) * 100, 2) as retention_rate_pct
from cohort_activity ca
join cohort_size cs on ca.cohort_month = cs.cohort_month
order by ca.cohort_month, ca.months_since_first_order
