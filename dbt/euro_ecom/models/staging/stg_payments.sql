select
    order_id,
    payment_method,
    payment_status
from {{ source('raw', 'payments') }}
