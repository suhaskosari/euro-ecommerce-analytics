"""
Synthetic data generator for the European E-Commerce Intelligence platform.

Simulates two years of activity (2024-01-01 -> 2025-12-31) for a multi-country
European e-commerce retailer: customers, products, orders, order line items,
payments, returns, and marketing spend.

The raw CSVs are deliberately messy (inconsistent casing, mixed date formats,
duplicate rows, stray whitespace, a handful of bad values) to mirror what a
real source-system export looks like and to give the cleaning step in
python/etl_clean_transform.py real work to do.

Run:
    python python/generate_data.py
"""
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)
ALL_DATES = pd.date_range(START_DATE, END_DATE, freq="D")

COUNTRIES = {
    "DE": {"name": "Germany", "currency": "EUR", "weight": 0.25, "locale": "de_DE"},
    "FR": {"name": "France", "currency": "EUR", "weight": 0.20, "locale": "fr_FR"},
    "GB": {"name": "United Kingdom", "currency": "GBP", "weight": 0.20, "locale": "en_GB"},
    "NL": {"name": "Netherlands", "currency": "EUR", "weight": 0.10, "locale": "nl_NL"},
    "ES": {"name": "Spain", "currency": "EUR", "weight": 0.12, "locale": "es_ES"},
    "IT": {"name": "Italy", "currency": "EUR", "weight": 0.08, "locale": "it_IT"},
    "SE": {"name": "Sweden", "currency": "SEK", "weight": 0.05, "locale": "sv_SE"},
}
COUNTRY_CODES = list(COUNTRIES.keys())
COUNTRY_WEIGHTS = [COUNTRIES[c]["weight"] for c in COUNTRY_CODES]

ACQUISITION_CHANNELS = ["organic_search", "paid_search", "social_media", "email", "referral", "direct"]
ORDER_CHANNELS = ["website", "mobile_app", "marketplace"]
PAYMENT_METHODS = ["credit_card", "paypal", "klarna", "bank_transfer", "apple_pay"]
RETURN_REASONS = ["wrong_size", "damaged", "not_as_described", "changed_mind", "late_delivery", "quality_issue"]
MARKETING_CHANNELS = ["paid_search", "social_media", "email", "affiliate"]

CATEGORIES = {
    "Electronics": (25, 900),
    "Fashion": (10, 220),
    "Home & Garden": (8, 400),
    "Beauty & Health": (5, 90),
    "Sports & Outdoors": (12, 350),
    "Toys & Kids": (6, 120),
    "Books & Media": (4, 45),
    "Grocery": (2, 35),
}

N_CUSTOMERS = 4000
N_PRODUCTS = 220

fakers = {c: Faker(cfg["locale"]) for c, cfg in COUNTRIES.items()}
Faker.seed(SEED)


def messy_case(s: str) -> str:
    """Randomly mangle casing/whitespace the way a sloppy CSV export would."""
    r = random.random()
    if r < 0.15:
        return f" {s.upper()} "
    if r < 0.30:
        return s.lower()
    if r < 0.35:
        return f"{s}  "
    return s


def gen_customers():
    rows = []
    signup_start = START_DATE - timedelta(days=365)  # some customers pre-date the analysis window
    for i in range(1, N_CUSTOMERS + 1):
        country = np.random.choice(COUNTRY_CODES, p=COUNTRY_WEIGHTS)
        fk = fakers[country]
        signup_date = signup_start + timedelta(days=random.randint(0, (END_DATE - signup_start).days))
        email = fk.unique.email() if random.random() > 0.03 else None  # ~3% missing emails
        first, last = fk.first_name(), fk.last_name()
        rows.append({
            "customer_id": f"CUST{i:06d}",
            "first_name": first if random.random() > 0.02 else f"  {first}",
            "last_name": last,
            "email": email,
            "gender": random.choice(["F", "M", "Undisclosed"]),
            "birth_date": fk.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
            "signup_date": signup_date.isoformat(),
            "country_code": messy_case(country),
            "city": fk.city(),
            "acquisition_channel": random.choice(ACQUISITION_CHANNELS),
            "marketing_opt_in": random.choice([True, False]),
        })
    df = pd.DataFrame(rows)
    # inject a few duplicate rows (simulating a re-run export)
    dupes = df.sample(frac=0.01, random_state=SEED)
    df = pd.concat([df, dupes], ignore_index=True)
    return df


def gen_products():
    rows = []
    cats = list(CATEGORIES.keys())
    for i in range(1, N_PRODUCTS + 1):
        cat = random.choice(cats)
        lo, hi = CATEGORIES[cat]
        price = round(np.random.uniform(lo, hi), 2)
        cost = round(price * np.random.uniform(0.35, 0.65), 2)
        rows.append({
            "product_id": f"PROD{i:05d}",
            "product_name": f"{cat.split(' ')[0]} Item {i}",
            "category": messy_case(cat),
            "brand": random.choice(["Nordwell", "Solari", "Kavea", "Rovelle", "Lindmark", "Terravue"]),
            "unit_cost_eur": cost if random.random() > 0.02 else None,  # ~2% missing cost
            "unit_price_eur": price,
            "launch_date": (START_DATE - timedelta(days=random.randint(30, 900))).isoformat(),
        })
    return pd.DataFrame(rows)


def daily_demand_multiplier(d: date) -> float:
    """Growth trend + yearly seasonality (Nov/Dec peak, summer dip) + weekend lift."""
    days_elapsed = (d - START_DATE).days
    growth = 1 + 0.015 * (days_elapsed / 30)  # ~1.5% MoM growth
    month = d.month
    seasonal = {11: 1.55, 12: 1.75, 1: 0.85, 7: 0.75, 8: 0.80}.get(month, 1.0)
    weekend = 1.2 if d.weekday() >= 5 else 1.0
    return growth * seasonal * weekend


def gen_orders_and_items(customers_df, products_df):
    valid_customers = customers_df.drop_duplicates("customer_id")
    cust_country = dict(zip(valid_customers["customer_id"], valid_customers["country_code"].str.strip().str.upper()))
    cust_ids = list(cust_country.keys())
    product_ids = products_df["product_id"].tolist()
    product_price = dict(zip(products_df["product_id"], products_df["unit_price_eur"]))

    order_rows, item_rows, payment_rows = [], [], []
    order_seq = 1
    for d in ALL_DATES:
        d_date = d.date()
        base_orders = 22 * daily_demand_multiplier(d_date)

        # injected anomaly: checkout outage, near-zero orders for 3 days
        if date(2024, 6, 10) <= d_date <= date(2024, 6, 12):
            base_orders *= 0.08
        # injected anomaly: flash-sale demand spike
        if date(2025, 3, 3) <= d_date <= date(2025, 3, 4):
            base_orders *= 2.8

        n_orders = np.random.poisson(max(base_orders, 0.5))
        for _ in range(n_orders):
            customer_id = random.choice(cust_ids)
            country = cust_country[customer_id]
            currency = COUNTRIES.get(country, {"currency": "EUR"})["currency"]
            status = np.random.choice(["completed", "cancelled"], p=[0.94, 0.06])
            channel = random.choices(ORDER_CHANNELS, weights=[0.55, 0.35, 0.10])[0]
            n_items = random.choices([1, 2, 3, 4], weights=[0.5, 0.3, 0.15, 0.05])[0]
            items = random.sample(product_ids, k=n_items)

            gross = 0.0
            for p in items:
                qty = random.choices([1, 2, 3], weights=[0.75, 0.2, 0.05])[0]
                unit_price = product_price[p]
                line_total = round(unit_price * qty, 2)
                gross += line_total
                item_rows.append({
                    "order_id": f"ORD{order_seq:07d}",
                    "product_id": p,
                    "quantity": qty,
                    "unit_price_eur": unit_price,
                    "line_total_eur": line_total,
                })

            discount = round(gross * random.choice([0, 0, 0, 0.05, 0.1, 0.15]), 2)
            shipping = 0.0 if gross > 50 else round(random.uniform(2.99, 6.99), 2)
            net = round(gross - discount + shipping, 2)

            # a small number of data-entry errors: negative net amount
            if random.random() < 0.003:
                net = -abs(net)

            order_date_str = d_date.isoformat()
            if random.random() < 0.08:  # ~8% of rows use a different date format (raw export mess)
                order_date_str = d_date.strftime("%d/%m/%Y")

            order_rows.append({
                "order_id": f"ORD{order_seq:07d}",
                "customer_id": customer_id,
                "order_date": order_date_str,
                "country_code": messy_case(country),
                "channel": channel,
                "status": status,
                "currency_code": currency if random.random() > 0.1 else currency.lower(),
                "gross_amount_local": gross,
                "discount_amount_eur": discount,
                "shipping_fee_eur": shipping,
                "net_amount_eur": net,
            })
            payment_rows.append({
                "order_id": f"ORD{order_seq:07d}",
                "payment_method": random.choices(
                    PAYMENT_METHODS, weights=[0.45, 0.25, 0.15, 0.05, 0.10]
                )[0],
                "payment_status": "paid" if status == "completed" else "refunded",
            })
            order_seq += 1

    orders_df = pd.DataFrame(order_rows)
    # duplicate a small batch of order rows (simulating a retried export job)
    dupes = orders_df.sample(frac=0.005, random_state=SEED)
    orders_df = pd.concat([orders_df, dupes], ignore_index=True)

    return orders_df, pd.DataFrame(item_rows), pd.DataFrame(payment_rows)


def gen_returns(orders_df):
    completed = orders_df[orders_df["status"] == "completed"].drop_duplicates("order_id")
    sampled = completed.sample(frac=0.07, random_state=SEED)
    rows = []
    for i, row in enumerate(sampled.itertuples(), start=1):
        try:
            order_date = pd.to_datetime(row.order_date, dayfirst="/" in row.order_date)
        except Exception:
            order_date = pd.Timestamp(START_DATE)
        return_date = order_date + timedelta(days=random.randint(2, 21))
        date_str = return_date.date().isoformat()
        if random.random() < 0.2:
            date_str = return_date.strftime("%d-%m-%Y")
        rows.append({
            "return_id": f"RET{i:06d}",
            "order_id": row.order_id,
            "return_date": date_str,
            "return_reason": random.choice(RETURN_REASONS) if random.random() > 0.04 else None,
            "refund_amount_eur": round(abs(row.net_amount_eur) * random.uniform(0.4, 1.0), 2),
        })
    return pd.DataFrame(rows)


def gen_marketing_spend():
    rows = []
    for d in ALL_DATES:
        d_date = d.date()
        for country in COUNTRY_CODES:
            for channel in MARKETING_CHANNELS:
                base = {"paid_search": 220, "social_media": 180, "email": 40, "affiliate": 90}[channel]
                mult = daily_demand_multiplier(d_date) * COUNTRIES[country]["weight"] * 3
                spend = round(max(np.random.normal(base * mult, base * mult * 0.15), 5), 2)
                # injected anomaly: overspend with weak ROI on a paid_search push
                if date(2025, 1, 15) <= d_date <= date(2025, 1, 21) and channel == "paid_search":
                    spend *= 2.2
                impressions = int(spend * np.random.uniform(80, 140))
                clicks = int(impressions * np.random.uniform(0.01, 0.04))
                conversions = int(clicks * np.random.uniform(0.02, 0.08))
                rows.append({
                    "date": d_date.isoformat(),
                    "country_code": country,
                    "channel": channel,
                    "spend_eur": spend,
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                })
    return pd.DataFrame(rows)


def main():
    print("Generating customers...")
    customers_df = gen_customers()
    print("Generating products...")
    products_df = gen_products()
    print("Generating orders, items & payments...")
    orders_df, items_df, payments_df = gen_orders_and_items(customers_df, products_df)
    print("Generating returns...")
    returns_df = gen_returns(orders_df)
    print("Generating marketing spend...")
    marketing_df = gen_marketing_spend()

    customers_df.to_csv(RAW_DIR / "customers_raw.csv", index=False)
    products_df.to_csv(RAW_DIR / "products_raw.csv", index=False)
    orders_df.to_csv(RAW_DIR / "orders_raw.csv", index=False)
    items_df.to_csv(RAW_DIR / "order_items_raw.csv", index=False)
    payments_df.to_csv(RAW_DIR / "payments_raw.csv", index=False)
    returns_df.to_csv(RAW_DIR / "returns_raw.csv", index=False)
    marketing_df.to_csv(RAW_DIR / "marketing_spend_raw.csv", index=False)

    print(f"""
Done. Row counts:
  customers        {len(customers_df):>7,}
  products         {len(products_df):>7,}
  orders           {len(orders_df):>7,}
  order_items      {len(items_df):>7,}
  payments         {len(payments_df):>7,}
  returns          {len(returns_df):>7,}
  marketing_spend  {len(marketing_df):>7,}
Written to {RAW_DIR}
""")


if __name__ == "__main__":
    main()
