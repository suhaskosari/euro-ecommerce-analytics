-- ============================================================================
-- European E-Commerce Intelligence Platform - Dimensional Warehouse Schema
-- Target: PostgreSQL (production). Locally, dbt/DuckDB materializes the same
-- shapes for a zero-infrastructure demo -- see dbt/euro_ecom/models/marts.
-- Star schema: one wide fact per business process, conformed dimensions.
-- ============================================================================

create schema if not exists warehouse;
set search_path to warehouse;

-- ----------------------------------------------------------------------------
-- Dimensions
-- ----------------------------------------------------------------------------

create table if not exists dim_country (
    country_code        char(2)      primary key,
    country_name        text         not null,
    currency_code       char(3)      not null,
    region               text        not null            -- Western, Nordic, Southern
);

create table if not exists dim_customer (
    customer_id          text         primary key,
    first_name           text         not null,
    last_name            text         not null,
    email                text,
    gender                text,
    birth_date            date,
    signup_date           date         not null,
    country_code          char(2)      references dim_country (country_code),
    city                   text,
    acquisition_channel    text         not null,
    marketing_opt_in       boolean      not null default false
);

create table if not exists dim_product (
    product_id            text         primary key,
    product_name          text         not null,
    category               text        not null,
    brand                  text,
    unit_cost_eur          numeric(10, 2),
    unit_price_eur         numeric(10, 2) not null,
    launch_date            date
);

create table if not exists dim_date (
    date_day               date         primary key,
    year                    int         not null,
    quarter                 int         not null,
    month                   int         not null,
    month_name              text        not null,
    iso_week                int         not null,
    day_of_week             int         not null,        -- 1=Mon ... 7=Sun
    is_weekend               boolean     not null
);

-- ----------------------------------------------------------------------------
-- Facts
-- ----------------------------------------------------------------------------

create table if not exists fct_orders (
    order_id                text         primary key,
    customer_id             text         references dim_customer (customer_id),
    order_date              date         not null references dim_date (date_day),
    country_code            char(2)      references dim_country (country_code),
    channel                  text        not null,        -- website, mobile_app, marketplace
    status                   text        not null,        -- completed, cancelled
    currency_code            char(3)     not null,
    fx_rate_to_eur            numeric(10, 4) not null default 1,
    gross_amount_eur          numeric(12, 2) not null,
    discount_amount_eur       numeric(12, 2) not null default 0,
    shipping_fee_eur          numeric(12, 2) not null default 0,
    net_amount_eur            numeric(12, 2) not null,
    payment_method             text,
    order_item_count            int        not null
);

create table if not exists fct_order_items (
    order_id                 text        references fct_orders (order_id),
    product_id               text        references dim_product (product_id),
    quantity                  int        not null,
    unit_price_eur            numeric(10, 2) not null,
    line_total_eur             numeric(12, 2) not null,
    primary key (order_id, product_id)
);

create table if not exists fct_returns (
    return_id                 text        primary key,
    order_id                  text        references fct_orders (order_id),
    return_date                date       not null,
    return_reason               text,
    refund_amount_eur            numeric(12, 2) not null
);

create table if not exists fct_marketing_spend (
    date                        date       not null references dim_date (date_day),
    country_code                char(2)    references dim_country (country_code),
    channel                      text      not null,
    spend_eur                    numeric(12, 2) not null,
    impressions                   bigint   not null,
    clicks                        bigint   not null,
    conversions                    int     not null,
    primary key (date, country_code, channel)
);

create table if not exists fct_exchange_rates (
    date                          date     not null,
    currency_code                 char(3)  not null,
    rate_to_eur                    numeric(10, 4) not null,
    primary key (date, currency_code)
);

-- ----------------------------------------------------------------------------
-- Indexes for common analytical access paths
-- ----------------------------------------------------------------------------
create index if not exists ix_orders_customer     on fct_orders (customer_id);
create index if not exists ix_orders_date          on fct_orders (order_date);
create index if not exists ix_orders_country       on fct_orders (country_code);
create index if not exists ix_returns_order        on fct_returns (order_id);
create index if not exists ix_marketing_date       on fct_marketing_spend (date);
