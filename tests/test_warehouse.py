"""Sanity checks on the built warehouse (skipped if the pipeline has not been run)."""
from pathlib import Path

import duckdb
import pytest

DB = Path(__file__).resolve().parent.parent / "warehouse.duckdb"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="warehouse.duckdb not built")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(DB), read_only=True)
    yield c
    c.close()


def test_no_duplicate_orders(con):
    dupes = con.execute("select count(*) - count(distinct order_id) from main_marts.fct_orders").fetchone()[0]
    assert dupes == 0


def test_no_negative_revenue_after_cleaning(con):
    neg = con.execute("select count(*) from main_marts.fct_orders where net_amount_eur < 0").fetchone()[0]
    assert neg == 0


def test_every_order_has_a_known_customer(con):
    orphans = con.execute("""
        select count(*) from main_marts.fct_orders o
        left join main_marts.dim_customer c using (customer_id) where c.customer_id is null
    """).fetchone()[0]
    assert orphans == 0
