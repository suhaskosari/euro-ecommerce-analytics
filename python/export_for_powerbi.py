"""
Exports the final dbt marts to CSV so they can be imported directly into
Power BI Desktop (Get Data -> Text/CSV) without needing a live DuckDB ODBC
connection. Run this after `dbt run`.

Run:
    python python/export_for_powerbi.py
"""
from pathlib import Path

import duckdb

BASE = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "warehouse.duckdb"
OUT_DIR = BASE / "powerbi" / "exports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TABLES = {
    "dim_customer": "main_marts.dim_customer",
    "dim_product": "main_marts.dim_product",
    "dim_country": "main_marts.dim_country",
    "dim_date": "main_marts.dim_date",
    "fct_orders": "main_marts.fct_orders",
    "fct_order_items": "main_marts.fct_order_items",
    "fct_returns": "main_marts.fct_returns",
    "fct_marketing_spend": "main_marts.fct_marketing_spend",
    "monthly_revenue_kpis": "main_analytics.monthly_revenue_kpis",
    "customer_ltv": "main_analytics.customer_ltv",
    "cohort_retention": "main_analytics.cohort_retention",
    "product_performance": "main_analytics.product_performance",
    "marketing_roi": "main_analytics.marketing_roi",
    "returns_analysis": "main_analytics.returns_analysis",
}


def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    for name, ref in TABLES.items():
        out_path = OUT_DIR / f"{name}.csv"
        con.execute(f"copy (select * from {ref}) to '{out_path.as_posix()}' (header, delimiter ',')")
        rows = con.execute(f"select count(*) from {ref}").fetchone()[0]
        print(f"{name:<24} {rows:>7,} rows -> {out_path.relative_to(BASE)}")
    con.close()


if __name__ == "__main__":
    main()
