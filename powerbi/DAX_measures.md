# DAX Measures

Paste these into a dedicated `_Measures` table in Power BI (Model view -> New Table -> `_Measures = {BLANK()}`, then add each measure to it) once the model in [data_model.md](data_model.md) is built.

## Revenue & Orders

```dax
Net Revenue (EUR) =
SUM ( fct_orders[net_amount_eur] )

Orders =
DISTINCTCOUNT ( fct_orders[order_id] )

Average Order Value (EUR) =
DIVIDE ( [Net Revenue (EUR)], [Orders] )

Net Revenue LY =
CALCULATE ( [Net Revenue (EUR)], SAMEPERIODLASTYEAR ( dim_date[date_day] ) )

Revenue YoY % =
DIVIDE ( [Net Revenue (EUR)] - [Net Revenue LY], [Net Revenue LY] )

Revenue MoM % =
VAR PrevMonth =
    CALCULATE ( [Net Revenue (EUR)], DATEADD ( dim_date[date_day], -1, MONTH ) )
RETURN
    DIVIDE ( [Net Revenue (EUR)] - PrevMonth, PrevMonth )

Cancelled Order Rate % =
VAR TotalOrders = CALCULATE ( DISTINCTCOUNT ( fct_orders[order_id] ), ALL ( fct_orders[status] ) )
VAR Cancelled = CALCULATE ( DISTINCTCOUNT ( fct_orders[order_id] ), fct_orders[status] = "cancelled" )
RETURN
    DIVIDE ( Cancelled, TotalOrders )
```

## Customers

```dax
Active Customers =
DISTINCTCOUNT ( fct_orders[customer_id] )

New Customers =
CALCULATE (
    DISTINCTCOUNT ( dim_customer[customer_id] ),
    FILTER ( dim_customer, dim_customer[signup_date] IN VALUES ( dim_date[date_day] ) )
)

Customer Lifetime Value (EUR) =
AVERAGE ( customer_ltv[total_net_revenue_eur] )

Repeat Purchase Rate % =
VAR Repeaters = CALCULATE ( COUNTROWS ( customer_ltv ), customer_ltv[total_orders] > 1 )
VAR Purchasers = CALCULATE ( COUNTROWS ( customer_ltv ), customer_ltv[total_orders] > 0 )
RETURN
    DIVIDE ( Repeaters, Purchasers )

Churn Rate % =
VAR Churned = CALCULATE ( COUNTROWS ( customer_ltv ), customer_ltv[lifecycle_stage] = "churned" )
VAR EverPurchased = CALCULATE ( COUNTROWS ( customer_ltv ), customer_ltv[total_orders] > 0 )
RETURN
    DIVIDE ( Churned, EverPurchased )
```

## Products & Returns

```dax
Gross Margin (EUR) =
SUM ( fct_order_items[line_margin_eur] )

Gross Margin % =
DIVIDE ( [Gross Margin (EUR)], SUM ( fct_order_items[line_total_eur] ) )

Return Rate % =
VAR OrdersWithReturns = DISTINCTCOUNT ( fct_returns[order_id] )
VAR TotalOrders = DISTINCTCOUNT ( fct_orders[order_id] )
RETURN
    DIVIDE ( OrdersWithReturns, TotalOrders )

Total Refunded (EUR) =
SUM ( fct_returns[refund_amount_eur] )
```

## Marketing

```dax
Marketing Spend (EUR) =
SUM ( fct_marketing_spend[spend_eur] )

Blended ROAS =
DIVIDE ( [Net Revenue (EUR)], [Marketing Spend (EUR)] )

Cost per Conversion (EUR) =
DIVIDE ( [Marketing Spend (EUR)], SUM ( fct_marketing_spend[conversions] ) )

Click-Through Rate % =
DIVIDE ( SUM ( fct_marketing_spend[clicks] ), SUM ( fct_marketing_spend[impressions] ) )
```

## Anomaly overlay (import `outputs/revenue_anomalies.csv` as its own table)

```dax
Anomaly Flag Revenue (EUR) =
IF (
    NOT ISBLANK ( SELECTEDVALUE ( revenue_anomalies[net_revenue_eur] ) ),
    SELECTEDVALUE ( revenue_anomalies[net_revenue_eur] )
)
```
Plot this as a scatter series layered on top of the `Net Revenue (EUR)` line chart to highlight the statistically flagged days.
