"""
Loads the cleaned tables from data/processed/ into a local DuckDB warehouse
file (warehouse.duckdb) under a `raw` schema. dbt then reads these as sources
and builds the dimensional model + analytics marts on top.

DuckDB is used as the local/demo warehouse because it is file-based and needs
no server -- sql/schema.sql documents the same shapes as PostgreSQL DDL for a
production deployment.

Run:
    python python/load_warehouse.py
"""
from pathlib import Path

import duckdb
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
PROCESSED = BASE / "data" / "processed"
DB_PATH = BASE / "warehouse.duckdb"

TABLES = [
    "customers", "products", "orders", "order_items",
    "payments", "returns", "marketing_spend", "exchange_rates",
]


def main():
    con = duckdb.connect(str(DB_PATH))
    con.execute("create schema if not exists raw")
    for table in TABLES:
        csv_path = PROCESSED / f"{table}.csv"
        df = pd.read_csv(csv_path)
        con.execute(f"create or replace table raw.{table} as select * from df")
        count = con.execute(f"select count(*) from raw.{table}").fetchone()[0]
        print(f"raw.{table:<16} {count:>7,} rows  <- {csv_path.name}")
    con.close()
    print(f"\nWarehouse ready at {DB_PATH}")


if __name__ == "__main__":
    main()
