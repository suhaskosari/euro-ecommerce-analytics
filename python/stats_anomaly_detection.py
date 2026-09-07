"""
Statistical analysis layer on top of the dbt marts: daily revenue anomaly
detection (IQR + z-score), RFM customer segmentation, and a marketing-spend
efficiency scan. Writes CSV outputs + PNG charts to outputs/ so they can be
picked up by the AI-insights layer and referenced from Power BI / the README.

Run (after `dbt run`):
    python python/stats_anomaly_detection.py
"""
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "warehouse.duckdb"
OUT = BASE / "outputs"
OUT.mkdir(exist_ok=True)


def get_con():
    return duckdb.connect(str(DB_PATH), read_only=True)


def detect_revenue_anomalies(con) -> pd.DataFrame:
    daily = con.execute("""
        select order_date as date, sum(net_amount_eur) as net_revenue_eur, count(distinct order_id) as orders_count
        from main_marts.fct_orders
        where status = 'completed'
        group by 1
        order by 1
    """).df()

    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.set_index("date").asfreq("D").fillna(0).reset_index()
    daily = daily.sort_values("date").reset_index(drop=True)

    # Naive day-of-week decomposition: revenue swings ~2x between weekday and
    # weekend, which would drown out real anomalies in a plain rolling
    # z-score. Instead compare each day to a trailing robust baseline of the
    # *same weekday* (median of the prior 8 occurrences), then z-score the
    # residual using the same weekday's spread (MAD-based std proxy).
    daily["dow"] = daily["date"].dt.dayofweek
    baseline, resid_std = pd.Series(index=daily.index, dtype=float), pd.Series(index=daily.index, dtype=float)
    for _, grp in daily.groupby("dow"):
        vals = grp["net_revenue_eur"]
        baseline.loc[grp.index] = vals.shift(1).rolling(8, min_periods=4).median()
        resid_std.loc[grp.index] = vals.shift(1).rolling(8, min_periods=4).std()

    daily["seasonal_baseline"] = baseline
    daily["residual"] = daily["net_revenue_eur"] - daily["seasonal_baseline"]
    daily["seasonal_zscore"] = daily["residual"] / resid_std.replace(0, np.nan)

    # IQR method on the raw series, kept as a secondary cross-check
    q1, q3 = daily["net_revenue_eur"].quantile([0.25, 0.75])
    iqr = q3 - q1
    daily["iqr_anomaly"] = ~daily["net_revenue_eur"].between(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    daily["zscore_anomaly"] = daily["seasonal_zscore"].abs() > 2.5

    # seasonal z-score is the primary signal; raw IQR is kept only as a
    # secondary cross-check column since it ignores day-of-week seasonality
    daily["is_anomaly"] = daily["zscore_anomaly"].fillna(False)
    daily["direction"] = np.where(daily["residual"].fillna(0) >= 0, "spike", "drop")

    anomalies = daily[daily["is_anomaly"]].copy()
    anomalies.to_csv(OUT / "revenue_anomalies.csv", index=False)
    daily.to_csv(OUT / "daily_revenue_with_flags.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.plot(daily["date"], daily["net_revenue_eur"], color="#3b6fa0", linewidth=1, label="Daily net revenue (EUR)")
    ax.scatter(anomalies["date"], anomalies["net_revenue_eur"], color="#d1495b", zorder=5, label="Flagged anomaly")
    ax.set_title("Daily Net Revenue with Statistically Flagged Anomalies")
    ax.set_ylabel("EUR")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "revenue_anomalies.png", dpi=140)
    plt.close(fig)

    return anomalies


def rfm_segmentation(con) -> pd.DataFrame:
    df = con.execute("""
        select customer_id, country_code, total_orders, total_net_revenue_eur,
               last_order_date, first_order_date
        from main_analytics.customer_ltv
        where total_orders > 0
    """).df()

    as_of = pd.to_datetime(df["last_order_date"]).max()
    df["recency_days"] = (as_of - pd.to_datetime(df["last_order_date"])).dt.days
    df["frequency"] = df["total_orders"]
    df["monetary"] = df["total_net_revenue_eur"]

    # score 1 (worst) - 5 (best) per RFM dimension using quintiles
    df["r_score"] = pd.qcut(df["recency_days"], 5, labels=[5, 4, 3, 2, 1], duplicates="drop").astype(int)
    df["f_score"] = pd.qcut(df["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
    df["m_score"] = pd.qcut(df["monetary"], 5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
    df["rfm_score"] = df["r_score"] + df["f_score"] + df["m_score"]

    def segment(row):
        if row["rfm_score"] >= 13:
            return "Champions"
        if row["r_score"] >= 4 and row["f_score"] >= 3:
            return "Loyal"
        if row["r_score"] <= 2 and row["f_score"] >= 3:
            return "At Risk"
        if row["r_score"] <= 2 and row["f_score"] <= 2:
            return "Hibernating"
        return "Potential Loyalist"

    df["segment"] = df.apply(segment, axis=1)
    df.to_csv(OUT / "customer_rfm_segments.csv", index=False)

    summary = df.groupby("segment").agg(
        customers=("customer_id", "count"),
        total_revenue_eur=("monetary", "sum"),
        avg_recency_days=("recency_days", "mean"),
    ).round(1).sort_values("total_revenue_eur", ascending=False)
    summary.to_csv(OUT / "rfm_segment_summary.csv")
    return summary


def marketing_efficiency_scan(con) -> pd.DataFrame:
    df = con.execute("""
        select country_code, month, channel, spend_eur, net_revenue_eur, blended_roas
        from main_analytics.marketing_roi
        where net_revenue_eur is not null
    """).df()

    # flag channel-months where ROAS is a statistical outlier on the low side (z-score within channel)
    df["z_roas"] = df.groupby("channel")["blended_roas"].transform(lambda s: stats.zscore(s, nan_policy="omit"))
    underperforming = df[df["z_roas"] < -1.5].sort_values("z_roas")
    underperforming.to_csv(OUT / "underperforming_marketing_spend.csv", index=False)
    return underperforming


def main():
    con = get_con()
    print("Detecting revenue anomalies...")
    anomalies = detect_revenue_anomalies(con)
    print(f"  {len(anomalies)} anomalous days flagged -> outputs/revenue_anomalies.csv, outputs/revenue_anomalies.png")

    print("Running RFM customer segmentation...")
    rfm_summary = rfm_segmentation(con)
    print(rfm_summary.to_string())
    print("  -> outputs/customer_rfm_segments.csv, outputs/rfm_segment_summary.csv")

    print("Scanning marketing spend efficiency...")
    underperforming = marketing_efficiency_scan(con)
    print(f"  {len(underperforming)} channel-months flagged as underperforming -> outputs/underperforming_marketing_spend.csv")

    con.close()


if __name__ == "__main__":
    main()
