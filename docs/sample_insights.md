# AI-Assisted Analytics Report

_Generated from validated dbt marts and statistical outputs. Every figure below traces back to a specific mart/column -- nothing is invented._

## Headline
- Across the full observation window, the business generated **EUR 6,241,305** in net revenue across **20,225 completed orders**.
- Revenue is led by: DE (EUR 1,591,654), FR (EUR 1,243,979), GB (EUR 1,225,858).

## Latest Month Snapshot (2025-12-01)
- **DE**: EUR 132,388 net revenue, 395 orders, AOV EUR 335.16 (+32.8% MoM).
- **ES**: EUR 51,874 net revenue, 171 orders, AOV EUR 303.35 (+17.6% MoM).
- **FR**: EUR 105,067 net revenue, 319 orders, AOV EUR 329.36 (+33.9% MoM).
- **GB**: EUR 105,519 net revenue, 371 orders, AOV EUR 284.42 (+24.3% MoM).
- **IT**: EUR 37,116 net revenue, 125 orders, AOV EUR 296.93 (+22.4% MoM).
- **NL**: EUR 57,073 net revenue, 174 orders, AOV EUR 328.01 (+27.3% MoM).
- **SE**: EUR 17,713 net revenue, 63 orders, AOV EUR 281.15 (-38.0% MoM).

## Statistically Significant Revenue Anomalies
Flagged via day-of-week-adjusted z-score (|z| > 2.5) on daily net revenue:
- 2025-03-03: EUR 27,139 net revenue, a spike (z = 10.57 vs. the same weekday's trailing baseline).
- 2025-03-04: EUR 27,879 net revenue, a spike (z = 9.55 vs. the same weekday's trailing baseline).
- 2025-09-05: EUR 14,752 net revenue, a spike (z = 8.30 vs. the same weekday's trailing baseline).
- 2025-05-13: EUR 11,400 net revenue, a spike (z = 7.71 vs. the same weekday's trailing baseline).
- 2024-11-27: EUR 16,568 net revenue, a spike (z = 5.83 vs. the same weekday's trailing baseline).

## Customer Segments (RFM)
- **Champions**: 679 customers, EUR 1,949,238 total revenue, avg recency 21 days since last order.
- **Potential Loyalist**: 1,130 customers, EUR 1,419,181 total revenue, avg recency 41 days since last order.
- **At Risk**: 701 customers, EUR 1,321,348 total revenue, avg recency 173 days since last order.
- **Hibernating**: 891 customers, EUR 784,085 total revenue, avg recency 260 days since last order.
- **Loyal**: 580 customers, EUR 767,454 total revenue, avg recency 19 days since last order.

## Top Products by Revenue
- **Electronics Item 129** (Electronics): EUR 209,241 gross revenue, 51.5% margin, 4.9% return rate.
- **Electronics Item 144** (Electronics): EUR 187,525 gross revenue, 47.7% margin, 10.3% return rate.
- **Electronics Item 112** (Electronics): EUR 187,269 gross revenue, 40.7% margin, 8.8% return rate.
- **Electronics Item 75** (Electronics): EUR 186,252 gross revenue, 41.6% margin, 5.8% return rate.
- **Electronics Item 55** (Electronics): EUR 184,941 gross revenue, 47.7% margin, 5.1% return rate.

## Leading Return Reasons
- **wrong_size**: 245 returns, EUR 55,841 refunded.
- **late_delivery**: 239 returns, EUR 47,419 refunded.
- **not_as_described**: 238 returns, EUR 54,748 refunded.

## Marketing Spend Efficiency
- 35 country/channel/month combinations were flagged as statistical ROAS underperformers (z-score < -1.5 within their channel).
  - SE / paid_search / 2025-08-01: EUR 1,175 spend, blended ROAS 5.61x.
  - SE / affiliate / 2025-08-01: EUR 468 spend, blended ROAS 14.08x.
  - NL / social_media / 2024-02-01: EUR 1,836 spend, blended ROAS 7.22x.

---
_Report generation: `python python/ai_insights.py`. Pass `--llm` with `ANTHROPIC_API_KEY` set to have Claude re-phrase this same evidence in fluent prose (numbers are never sourced from the model)._