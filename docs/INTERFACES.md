> Historical v0.1 reference. Current implementation and acceptance: [v0.2 PRD](../specs/PRD.md), [runbook](RUNBOOK-v2.md), and [release evidence](RELEASE.md).

# Implementation contracts v1

All amounts integer MXN cents; quantities integer; ISO dates; IDs synthetic strings. Seed 42, as_of 2026-09-21, 90 days. Provisional demo policy: recognize revenue on delivery, credit notes reduce revenue on their date; refunds only reduce cash; restock returns reverse standard COGS separately. Costs are locked on order items. The demo also requires settlement no later than the posted shipment/sale movement for prepaid shipped/delivered orders, and reconciles `expenses.category == 'marketing'` to funnel spend. These are synthetic analytical invariants, not approved real operating/accounting policy. All domains synthetic. No real-data loading enabled.

`alma/fixtures.py`: `generate(seed=42, scenario='normal') -> dict` with keys `metadata` and `tables`. Metadata includes synthetic=true, seed, as_of, scenario, currency='MXN', coverage (table->bool). Tables use these exact columns (nullable only where indicated):

- products: id,name,category,collection,lifecycle
- variants: id,product_id,size,color,price_cents,cost_cents(nullable)
- suppliers: id,name
- purchase_orders: id,supplier_id,variant_id,ordered_qty,received_qty,unit_cost_cents,status,date,paid_cents
- customers: id,acquired_date
- orders: id,customer_id,channel,campaign_id,date,delivered_date(nullable),status
- order_items: id,order_id,variant_id,quantity,unit_price_cents,discount_cents (whole line),unit_cost_cents(nullable)
- payments: id,order_id,date,amount_cents,status (settled/pending/failed)
- refunds: id,order_id,date,amount_cents,status (settled/pending)
- credit_notes: id,order_item_id,date,amount_cents,reason
- returns: id,order_item_id,date,quantity,restock (0/1)
- movements: id,variant_id,date,kind (opening/receipt/sale/return/adjustment/supplier_return),quantity (signed),reference_id (order item / PO / return / opening)
- reservations: id,order_item_id,quantity,status (active/released)
- expenses: id,date,category,amount_cents,paid_cents,variable (0/1)
- funnel: id,date,channel,campaign_id,visits(nullable),leads(nullable),spend_cents
- unmet_demand: id,date,variant_id,quantity,reason

Each table is a list of dictionaries. Fixtures should include delivered, shipped, paid, pending, cancelled orders; partial receipt/in-transit PO; customer returns with/without restock and refunds separate; discounts, OPEX, null traffic for DM channel, slow-stock/stockout variants. Sufficient opening stock to prevent negative balances normal. Receipt/sale/return movements reconcile 1:1 to source. PO paid cents <= total ordered value. Expense accrual vs cash distinct. Reproducible scenarios: normal; missing_cost (null cost); negative_stock (extra large negative adjustment); missing_payment (remove settled payment); duplicate_event (duplicate movement id). Returns <= sold quantity; credit <= delivered line net; refunds <= settled payment. No pseudo real PII.

`alma/analytics.py`: `analyze(data) -> report` contract:

```
{
 meta:{synthetic:true,as_of,seed,scenario,currency:'MXN',status:'PASS'|'BLOCKED',policy:'Provisional',coverage:{table:boolean}},
 kpis:{gross_revenue_cents,discounts_cents,credits_cents,net_revenue_cents,cogs_cents,gross_profit_cents,gross_margin_pct,opex_cents,variable_expenses_cents,contribution_cents,operating_proxy_cents,cash_in_cents,cash_out_cents,net_cash_cents,orders,delivered_orders,repeat_rate_pct,inventory_value_cents},
 trend:[{month,net_revenue_cents,cogs_cents,opex_cents,net_cash_cents}],
 inventory:[{sku,name,category,lifecycle,size,color,on_hand,reserved,available,in_transit,cost_cents,value_cents,sold_units,sell_through_pct,days_since_sale,status}],
 channels:[{channel,visits,leads,orders,delivered_orders,net_revenue_cents,spend_cents,conversion_pct}],
 cohorts:[{month,customers,repeat_customers,repeat_rate_pct,mature_30d}],
 products:[{id,name,category,collection,lifecycle}],
 orders:[{id,date,channel,status,customer_id,ordered_cents,recognized_cents,settled_cents,refunded_cents}],
 purchases:[{id,supplier,sku,ordered_qty,received_qty,in_transit,status,ordered_cents,paid_cents}],
 quality:[{id,status:'PASS'|'FAIL'|'UNKNOWN',message,evidence_refs:[string]}],
 market:[{id,title,publisher,url,observed_at,coverage,license,limitation,status}],
 experiments:[{id,title,hypothesis,primary_metric,guardrail,window,population,close_criterion,status,evidence_refs}],
 decisions:[{id,version,status,facts:[{text,evidence_refs}],unknowns:[string],hypotheses:[string],actions:[{description,approval_required:true,execution:'BLOCKED'}]}]
}
```

Null values mean unknown and must render as `Sin datos`, never zero. Inventory is all-time at as_of. `sold_units` is gross posted shipment units; sell-through uses net sold units after restocked customer returns divided by opening plus receipts. `idea` and `sample` product lifecycles are `PRELAUNCH` and must not produce reorder proposals. Trend finance uses event dates. Channels receive credit from the originating order channel. Conversion uses only known visit denominators and is descriptive, not causal. Each order campaign need not join a campaign table; use synthetic labels.

`alma/reporting.py`: `write_reports(report, output_dir) -> list[str]` writes deterministic UTF-8 artifacts and returns their output-relative filenames:

- `report.md`: narrative analysis with a persistent synthetic-data warning, calculated findings, limitations, source authority, experiments, and blocked actions;
- `report.html`: printable narrative HTML with no script or remote assets;
- `charts/monthly_finance.svg`: net revenue, COGS, and OPEX by event month;
- `charts/color_stock.svg`: available units by color with unknowns visible; and
- `charts/cash_bridge.svg`: observed cash in, cash out, and net cash.

The writer tolerates absent arrays and null measures, renders unknowns as `Sin datos`, escapes narrative content, and references only generated local SVGs. It does not create a navigable UI.

`python -m alma demo --output build/demo` writes the canonical JSON, SQLite staging artifact, CSV exports, quality results, decision packets, Markdown/HTML/SVG reports, receipt, and ownership marker. `python -m alma verify --output build/verification` runs standard-library tests, controlled scenarios, CSV roundtrips, and deterministic replay and writes `verification.json`. A build accepts a new/empty output directory or one carrying the exact Alma ownership marker; it rejects an unowned nonempty directory. Red scenarios use separate output directories from the normal demo.

Main owns analytics, validation, CLI, storage, publication checks, and integration. Luna owns fixtures and fixture tests. Terra owns deterministic reporting artifacts. Sol owns plan/domain/interfaces and integration/security tests. All code is Python 3.11+ standard library. There is no frontend, backend service, local web server, mobile app, SaaS, CRM, ERP, or BI application in v1.
