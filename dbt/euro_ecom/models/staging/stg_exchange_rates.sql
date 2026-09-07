select
    cast(date as date) as date,
    currency_code,
    cast(rate_to_eur as decimal(10, 4)) as rate_to_eur
from {{ source('raw', 'exchange_rates') }}
