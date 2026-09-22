# Warehouse v2 metric catalog

| Mart | Grain | Key measures and lineage |
|---|---|---|
| `sales_daily` | event date | Delivered-line gross/discount and COGS on the delivery date; credit-note reductions on their event date; restocked-return COGS reversals on the return event date. |
| `inventory_position` | variant at snapshot | Product/SKU attributes, ledger on-hand, active reservation, available, open PO transit, latest deterministic count, ledger-through-count discrepancy, valuation, trailing 30-day net sold, cover, and prelaunch/stockout rule. |
| `inventory_aging` | variant at snapshot | Position plus latest positive stock event and shipped quantity. |
| `procurement` | purchase order | Ordered/received/open quantity and event-reconciled supplier cash. |
| `cash_daily` | cash event date | Settled payments in; refunds, supplier payments, and expense payments out. This is movement, not bank balance. |
| `finance_monthly` | calendar month | Revenue, COGS, gross profit, variable expense, contribution after variable expense, all-expense operating result, and cash movement. A single missing COGS component makes monthly COGS/profit unknown. The month spine retains expense-only and cash-only months. |
| `channel_performance` | channel × campaign | Distinct delivered orders/customers, delivered revenue, credits, delivered COGS, restock COGS reversal, descriptive marketing spend, and an explicit unknown-attribution flag. It makes no causal ROI claim. |
| `customer_cohorts` | first delivered month | Cohort customers, mature 30-day denominator, immature customers, and repeat-within-30-day rate. Immature cohorts are unknown, never reported as zero repeat. |
| `experiment_results` | experiment × arm | Assignment, conversion, revenue, contribution and returns. Outcomes are synthetic randomized examples and are descriptive only; no causal lift or ROI is claimed. |
| `funnel_conversion` | channel × campaign | All leads plus linked/unlinked subgroups, distinct linked sessions/orders, descriptive spend, and conditional rates. Aggregate funnel traffic is not used as a substitution denominator. |
| `reconciliation` | named check | Independent source and mart totals with a `passed` evidence flag. |

The reconciliation result retains the generic columns `source_cents` and
`mart_cents` for compatibility. For `check_id = purchase_receipts`, their unit is
**physical units**, not currency; every other current reconciliation check uses
MXN cents. Interpret those two columns together with `check_id` and never sum
different checks. Business marts use quantity and money columns separately.

`models/marts.sql` is the short lineage index; `models/marts/*.sql` are the
executable fixed-query definitions loaded by `alma/warehouse.py`. Marts are materialized, and `query_mart` exposes names
only, so a consumer cannot execute arbitrary SQL through the public API.

## Column lineage and ownership

The executable sources are `models/schema.sql` and `models/marts/*.sql`; the
warehouse records their SHA-256 hashes in its manifest. `inspect_schema()`
returns each relation's source/mart type, grain, and operational owner
(`synthetic snapshot producer` for source facts; `deterministic warehouse` for
marts), rather than inventing an orchestration layer.

| Output column(s) | Direct source reference |
|---|---|
| `sales_daily.gross_revenue_cents`, `discount_cents`, `cogs_cents` | `orders.delivered_date`, `order_items.quantity/unit_price_cents/discount_cents/unit_cost_cents`; restock reversal from `returns.date/restock/quantity`. |
| `cash_daily.*_cents` | `payments`, `refunds`, `supplier_payments`, and `expense_payments` event `date` and `amount_cents`. |
| `inventory_position.*` | `variants`, `products`, `movements`, `reservations`, `purchase_orders`, `inventory_counts`, delivered `orders/order_items`, and restocked `returns`. |
| `funnel_conversion.sessions/leads/linked_orders` | Deduplicated `sessions.id`, `leads.id/session_id/order_id`; `funnel.spend_cents` is descriptive spend only. |
| `experiment_results.*` | `experiments`, `experiment_assignments`, and `experiment_outcomes`; results remain marked synthetic/descriptive. |
