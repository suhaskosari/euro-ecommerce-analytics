select
    r.return_id,
    r.order_id,
    r.return_date,
    r.return_reason,
    r.refund_amount_eur,
    o.order_date,
    date_diff('day', o.order_date, r.return_date) as days_to_return
from {{ ref('stg_returns') }} r
left join {{ ref('stg_orders') }} o on r.order_id = o.order_id
