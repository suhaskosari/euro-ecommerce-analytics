select
    date_trunc('month', return_date) as month,
    return_reason,
    count(*) as returns_count,
    sum(refund_amount_eur) as total_refund_eur,
    round(avg(days_to_return), 1) as avg_days_to_return
from {{ ref('fct_returns') }}
group by 1, 2
order by 1, 2
