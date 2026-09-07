"""
AI-assisted analytics layer.

Reads the validated business metrics already computed by dbt (models/marts/analytics)
and python/stats_anomaly_detection.py, then produces an evidence-based narrative
report: every claim in the output is generated FROM a specific computed number,
never invented. This is the "grounding" pattern that makes an LLM safe to use
for business reporting -- the model is only asked to phrase evidence, never to
originate it.

Two modes:
  - Rule-based (default, no dependencies, fully deterministic): turns the
    computed evidence dict directly into templated bullet points.
  - LLM-enhanced (optional): if ANTHROPIC_API_KEY is set, sends the SAME
    evidence dict to Claude with a strict "only use these numbers" system
    prompt, and asks it to write the narrative in fluent prose. Falls back
    to the rule-based writer on any error (missing key, network, etc).

Run:
    python python/ai_insights.py
    python python/ai_insights.py --llm     # use Claude if ANTHROPIC_API_KEY is set
"""
import argparse
import json
import os
from pathlib import Path

import duckdb
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "warehouse.duckdb"
OUT = BASE / "outputs"
DOCS = BASE / "docs"
DOCS.mkdir(exist_ok=True)


def gather_evidence() -> dict:
    """Pulls a compact set of validated numbers from the marts + stats outputs.
    Everything downstream (rule-based or LLM) is only allowed to talk about
    numbers that appear in this dict."""
    con = duckdb.connect(str(DB_PATH), read_only=True)

    kpis = con.execute("""
        select country_code, month, net_revenue_eur, orders_count, avg_order_value_eur, mom_revenue_growth_pct
        from main_analytics.monthly_revenue_kpis
        order by month
    """).df()
    latest_month = kpis["month"].max()
    latest = kpis[kpis["month"] == latest_month]

    totals = con.execute("""
        select sum(net_revenue_eur) as total_revenue_eur, sum(orders_count) as total_orders
        from main_analytics.monthly_revenue_kpis
    """).df().iloc[0]

    top_country = (
        kpis.groupby("country_code")["net_revenue_eur"].sum().sort_values(ascending=False)
    )

    returns = con.execute("""
        select return_reason, sum(returns_count) as returns_count, sum(total_refund_eur) as total_refund_eur
        from main_analytics.returns_analysis
        group by 1 order by 2 desc limit 3
    """).df()

    product_perf = con.execute("""
        select product_name, category, gross_revenue_eur, margin_pct, return_rate_pct
        from main_analytics.product_performance
        order by gross_revenue_eur desc limit 5
    """).df()

    con.close()

    evidence = {
        "latest_month": str(latest_month.date()) if hasattr(latest_month, "date") else str(latest_month),
        "total_revenue_eur": round(float(totals["total_revenue_eur"]), 2),
        "total_orders": int(totals["total_orders"]),
        "top_countries_by_revenue": top_country.head(3).round(2).to_dict(),
        "latest_month_by_country": latest[["country_code", "net_revenue_eur", "orders_count", "avg_order_value_eur", "mom_revenue_growth_pct"]]
            .round(2).to_dict(orient="records"),
        "top_return_reasons": returns.round(2).to_dict(orient="records"),
        "top_products_by_revenue": product_perf.round(2).to_dict(orient="records"),
    }

    anomalies_path = OUT / "revenue_anomalies.csv"
    if anomalies_path.exists():
        anomalies = pd.read_csv(anomalies_path)
        biggest = anomalies.reindex(anomalies["seasonal_zscore"].abs().sort_values(ascending=False).index).head(5)
        evidence["biggest_revenue_anomalies"] = biggest[["date", "net_revenue_eur", "seasonal_zscore", "direction"]].round(2).to_dict(orient="records")

    rfm_path = OUT / "rfm_segment_summary.csv"
    if rfm_path.exists():
        evidence["rfm_segments"] = pd.read_csv(rfm_path).round(1).to_dict(orient="records")

    underperf_path = OUT / "underperforming_marketing_spend.csv"
    if underperf_path.exists():
        underperf = pd.read_csv(underperf_path)
        evidence["underperforming_marketing_spend_count"] = int(len(underperf))
        evidence["worst_marketing_examples"] = underperf.head(3)[["country_code", "month", "channel", "spend_eur", "blended_roas"]].round(2).to_dict(orient="records")

    return evidence


def write_rule_based_report(evidence: dict) -> str:
    lines = ["# AI-Assisted Analytics Report", "", "_Generated from validated dbt marts and statistical outputs. Every figure below traces back to a specific mart/column -- nothing is invented._", ""]

    lines.append("## Headline")
    lines.append(
        f"- Across the full observation window, the business generated **EUR {evidence['total_revenue_eur']:,.0f}** "
        f"in net revenue across **{evidence['total_orders']:,} completed orders**."
    )
    top_countries = evidence["top_countries_by_revenue"]
    top_list = ", ".join(f"{c} (EUR {v:,.0f})" for c, v in top_countries.items())
    lines.append(f"- Revenue is led by: {top_list}.")
    lines.append("")

    lines.append(f"## Latest Month Snapshot ({evidence['latest_month']})")
    for row in evidence["latest_month_by_country"]:
        growth = row["mom_revenue_growth_pct"]
        growth_str = f"{growth:+.1f}% MoM" if pd.notna(growth) else "MoM n/a (first observed month)"
        lines.append(
            f"- **{row['country_code']}**: EUR {row['net_revenue_eur']:,.0f} net revenue, "
            f"{row['orders_count']:,} orders, AOV EUR {row['avg_order_value_eur']:.2f} ({growth_str})."
        )
    lines.append("")

    if "biggest_revenue_anomalies" in evidence:
        lines.append("## Statistically Significant Revenue Anomalies")
        lines.append("Flagged via day-of-week-adjusted z-score (|z| > 2.5) on daily net revenue:")
        for a in evidence["biggest_revenue_anomalies"]:
            lines.append(
                f"- {a['date']}: EUR {a['net_revenue_eur']:,.0f} net revenue, a {a['direction']} "
                f"(z = {a['seasonal_zscore']:.2f} vs. the same weekday's trailing baseline)."
            )
        lines.append("")

    if "rfm_segments" in evidence:
        lines.append("## Customer Segments (RFM)")
        for s in evidence["rfm_segments"]:
            lines.append(
                f"- **{s['segment']}**: {int(s['customers']):,} customers, "
                f"EUR {s['total_revenue_eur']:,.0f} total revenue, "
                f"avg recency {s['avg_recency_days']:.0f} days since last order."
            )
        lines.append("")

    if "top_products_by_revenue" in evidence and evidence["top_products_by_revenue"]:
        lines.append("## Top Products by Revenue")
        for p in evidence["top_products_by_revenue"]:
            lines.append(
                f"- **{p['product_name']}** ({p['category']}): EUR {p['gross_revenue_eur']:,.0f} gross revenue, "
                f"{p['margin_pct']:.1f}% margin, {p['return_rate_pct']:.1f}% return rate."
            )
        lines.append("")

    if evidence.get("top_return_reasons"):
        lines.append("## Leading Return Reasons")
        for r in evidence["top_return_reasons"]:
            lines.append(f"- **{r['return_reason']}**: {int(r['returns_count']):,} returns, EUR {r['total_refund_eur']:,.0f} refunded.")
        lines.append("")

    if "underperforming_marketing_spend_count" in evidence:
        lines.append("## Marketing Spend Efficiency")
        lines.append(
            f"- {evidence['underperforming_marketing_spend_count']} country/channel/month combinations were flagged as "
            "statistical ROAS underperformers (z-score < -1.5 within their channel)."
        )
        for m in evidence.get("worst_marketing_examples", []):
            lines.append(
                f"  - {m['country_code']} / {m['channel']} / {m['month']}: EUR {m['spend_eur']:,.0f} spend, "
                f"blended ROAS {m['blended_roas']:.2f}x."
            )
        lines.append("")

    lines.append("---")
    lines.append("_Report generation: `python python/ai_insights.py`. Pass `--llm` with `ANTHROPIC_API_KEY` set to have Claude re-phrase this same evidence in fluent prose (numbers are never sourced from the model)._")
    return "\n".join(lines)


def write_llm_report(evidence: dict) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set -- skipping LLM enhancement, using rule-based report.")
        return None
    try:
        import anthropic
    except ImportError:
        print("anthropic package not installed (pip install anthropic) -- using rule-based report.")
        return None

    system_prompt = (
        "You are a business analyst writing an executive summary for a European e-commerce company. "
        "You will be given a JSON object of pre-computed, validated metrics. "
        "You MUST only reference numbers that appear in that JSON -- never invent, estimate, or extrapolate "
        "a figure that is not explicitly present. Write clear, direct prose organized under markdown headings "
        "(Headline, Latest Month, Anomalies, Customers, Products, Marketing). Cite the exact numbers you were given."
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Validated metrics:\n{json.dumps(evidence, indent=2, default=str)}"}],
        )
        return response.content[0].text
    except Exception as exc:
        print(f"LLM call failed ({exc}) -- falling back to rule-based report.")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="Use Claude to phrase the narrative if ANTHROPIC_API_KEY is set")
    args = parser.parse_args()

    evidence = gather_evidence()
    (OUT / "insights_evidence.json").write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")

    report = None
    if args.llm:
        report = write_llm_report(evidence)
    if report is None:
        report = write_rule_based_report(evidence)

    out_path = DOCS / "sample_insights.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote insights report -> {out_path}")
    print(f"Wrote raw evidence JSON -> {OUT / 'insights_evidence.json'}")


if __name__ == "__main__":
    main()
