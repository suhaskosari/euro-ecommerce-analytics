# Architecture

## Pipeline overview

```mermaid
flowchart LR
    subgraph Generate["1. Generate / Extract"]
        A1[generate_data.py<br/>synthetic customers, orders,<br/>products, returns, marketing]
        A2[fetch_exchange_rates.py<br/>live ECB rates via<br/>Frankfurter REST API]
    end

    subgraph Clean["2. Clean & Type (pandas)"]
        B1[etl_clean_transform.py<br/>dedupe, parse mixed dates,<br/>standardize casing, impute,<br/>flag bad values]
    end

    subgraph Load["3. Load"]
        C1[load_warehouse.py<br/>-> DuckDB raw schema]
    end

    subgraph Transform["4. Transform (dbt)"]
        D1[staging models<br/>typed passthroughs]
        D2[dimensional marts<br/>dim_*, fct_*]
        D3[analytics marts<br/>customer_ltv, cohort_retention,<br/>monthly_revenue_kpis,<br/>product_performance,<br/>marketing_roi, returns_analysis]
        D4[23 dbt tests<br/>unique / not_null / relationships]
    end

    subgraph Analyze["5. Statistics & AI"]
        E1[stats_anomaly_detection.py<br/>seasonal z-score anomalies,<br/>RFM segmentation]
        E2[ai_insights.py<br/>evidence-grounded narrative<br/>rule-based or Claude-enhanced]
    end

    subgraph Serve["6. Serve"]
        F1[export_for_powerbi.py<br/>-> CSV exports]
        F2[Power BI<br/>DAX measures + dashboards]
    end

    A1 --> B1
    A2 --> B1
    B1 --> C1
    C1 --> D1 --> D2 --> D3
    D2 -.-> D4
    D3 --> E1 --> E2
    D3 --> F1 --> F2
    E1 --> F1
```

## Why this shape

- **ELT, not ETL**: raw data is loaded into DuckDB largely as-is after a *light* Python cleaning pass (fixing genuine data-quality defects: duplicates, mixed date formats, bad casing, sign errors), and the *business* transformation (star schema, KPIs, segmentation logic) lives in dbt SQL, version-controlled and tested. This mirrors how a production warehouse (Snowflake/BigQuery/Postgres + dbt) is typically organized, just swapping in DuckDB so the whole thing runs locally with zero infrastructure.
- **DuckDB locally, PostgreSQL-shaped in `sql/schema.sql`**: the dimensional model is documented as standard Postgres DDL for a production deployment; DuckDB is used here purely so the repo is runnable by anyone who clones it, with no database server to stand up.
- **Statistics before AI**: anomaly detection and RFM segmentation are done with pandas/numpy/scipy against the dbt marts -- these are the "evidence." The AI layer is only ever asked to phrase evidence that's already been computed, never to originate a number. This is the same grounding pattern used in production LLM analytics tools, and it's what makes the AI layer safe to trust: the burden of correctness is on the deterministic statistics, not the model.
- **Reproducible by construction**: `generate_data.py` and the RFM/z-score logic are seeded/deterministic, so re-running the whole pipeline from scratch always reproduces the same numbers referenced in [docs/sample_insights.md](sample_insights.md).

## Data quality issues deliberately injected (and how they're caught)

| Issue | Where it's introduced | Where it's caught/fixed |
|---|---|---|
| Duplicate customer/order rows (simulated re-run export) | `generate_data.py` | `etl_clean_transform.py` dedupes on primary key, logged in `outputs/data_quality_report.md` |
| Mixed date formats (`YYYY-MM-DD` vs `DD/MM/YYYY`) | `generate_data.py` | `etl_clean_transform.py::parse_mixed_date` |
| Inconsistent casing/whitespace in country codes & categories | `generate_data.py` | `etl_clean_transform.py` standardization + category lookup |
| Missing product cost | `generate_data.py` | imputed via median cost-to-price ratio per category |
| Negative order amounts (sign errors) | `generate_data.py` | corrected + flagged via `data_quality_flag` column, carried through to `fct_orders` |
| Checkout outage (3 days near-zero orders, June 2024) | `generate_data.py::gen_orders_and_items` | `stats_anomaly_detection.py` seasonal z-score |
| Flash-sale demand spike (March 2025) | `generate_data.py::gen_orders_and_items` | `stats_anomaly_detection.py` seasonal z-score |
| Paid-search overspend with weak ROI (Jan 2025) | `generate_data.py::gen_marketing_spend` | `marketing_efficiency_scan` in `stats_anomaly_detection.py` |
