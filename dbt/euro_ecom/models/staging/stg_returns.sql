select
    return_id,
    order_id,
    cast(return_date as date) as return_date,
    return_reason,
    cast(refund_amount_eur as decimal(12, 2)) as refund_amount_eur
from {{ source('raw', 'returns') }}
