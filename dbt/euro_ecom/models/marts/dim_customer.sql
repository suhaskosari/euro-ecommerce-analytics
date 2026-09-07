select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.gender,
    c.birth_date,
    c.signup_date,
    c.country_code,
    co.country_name,
    co.region,
    c.city,
    c.acquisition_channel,
    c.marketing_opt_in
from {{ ref('stg_customers') }} c
left join {{ ref('dim_country') }} co on c.country_code = co.country_code
