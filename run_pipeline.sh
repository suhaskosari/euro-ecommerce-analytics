#!/bin/sh
# Runs the whole pipeline end to end: ingest -> clean -> load -> dbt -> analytics -> AI insights -> eval -> tests
set -e
python python/generate_data.py
python python/fetch_exchange_rates.py
python python/etl_clean_transform.py
python python/load_warehouse.py
dbt seed --project-dir dbt/euro_ecom
dbt run  --project-dir dbt/euro_ecom
dbt test --project-dir dbt/euro_ecom
python python/stats_anomaly_detection.py
python python/ai_insights.py
python python/export_for_powerbi.py
python python/eval_groundedness.py
python python/eval_anomaly_detection.py
python python/build_dashboard.py
pytest -q
