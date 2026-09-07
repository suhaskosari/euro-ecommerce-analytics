"""
Pulls historical EUR base exchange rates (GBP, SEK) from the free Frankfurter
REST API (https://frankfurter.dev, ECB reference rates, no API key required).

Falls back to a small deterministic synthetic-rate generator if the API is
unreachable (offline environment, rate limit, etc.) so the rest of the
pipeline never blocks on network access.

Run:
    python python/fetch_exchange_rates.py
"""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = "2024-01-01"
END_DATE = "2025-12-31"
TARGET_CURRENCIES = ["GBP", "SEK"]
API_URL = f"https://api.frankfurter.dev/v1/{START_DATE}..{END_DATE}"


def fetch_from_api() -> pd.DataFrame:
    resp = requests.get(API_URL, params={"base": "EUR", "symbols": ",".join(TARGET_CURRENCIES)}, timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    rows = []
    for day, rates in payload["rates"].items():
        for ccy in TARGET_CURRENCIES:
            if ccy in rates:
                rows.append({"date": day, "currency_code": ccy, "rate_to_eur": rates[ccy]})
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("API returned no rates")
    return df


def generate_synthetic() -> pd.DataFrame:
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    rng = np.random.default_rng(42)
    base_rates = {"GBP": 0.86, "SEK": 11.30}
    rows = []
    for ccy, base in base_rates.items():
        drift = np.cumsum(rng.normal(0, 0.0015, size=len(dates)))
        for d, dr in zip(dates, drift):
            rows.append({"date": d.date().isoformat(), "currency_code": ccy, "rate_to_eur": round(base + dr, 4)})
    return pd.DataFrame(rows)


def main():
    try:
        print(f"Fetching ECB reference rates from {API_URL} ...")
        df = fetch_from_api()
        print(f"Fetched {len(df):,} rate rows from Frankfurter API.")
    except Exception as exc:
        print(f"API fetch failed ({exc}); falling back to synthetic exchange rates.", file=sys.stderr)
        df = generate_synthetic()

    # fill any missing calendar days (weekends/holidays have no ECB fixing) via forward-fill per currency
    full_dates = pd.date_range(START_DATE, END_DATE, freq="D").date.astype(str)
    filled = []
    for ccy, grp in df.groupby("currency_code"):
        grp = grp.set_index("date").reindex(full_dates).ffill().bfill()
        grp["currency_code"] = ccy
        grp.index.name = "date"
        filled.append(grp.reset_index())
    out = pd.concat(filled, ignore_index=True)
    out.to_csv(RAW_DIR / "exchange_rates_raw.csv", index=False)
    print(f"Wrote {len(out):,} rows to {RAW_DIR / 'exchange_rates_raw.csv'}")


if __name__ == "__main__":
    main()
