select
    customer_id,
    first_name,
    last_name,
    email,
    gender,
    cast(birth_date as date)  as birth_date,
    cast(signup_date as date) as signup_date,
    country_code,
    city,
    acquisition_channel,
    marketing_opt_in
from {{ source('raw', 'customers') }}
