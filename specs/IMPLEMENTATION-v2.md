# v0.2 implementation interface (normative)

The v0.1 `alma.validation.SCHEMA` 16 tables remain a strict, compatible projection. New `simulation.generate(seed=42, scenario="normal", days=365, order_count=1200)` returns metadata and tables. Metadata adds contract_version="2.0" and start_date. Coverage explicitly covers every table. `simulation.core_projection(data)` drops extras and extra coverage keys for v1 checks. Scenarios: normal, stock_pressure, promotion_illusion, cash_squeeze, missing_cost, broken_link.

Additional tables (columns in insertion order; id TEXT PRIMARY KEY; dates ISO strings; *_cents INTEGER; quantity/count/flags INTEGER; null only where noted):

| Table | Columns | Relations / rule |
|---|---|---|
| campaigns | id name channel objective start_date end_date | dates within snapshot |
| content_assets | id campaign_id format theme published_date variant_id | variant_id nullable; campaigns FK |
| sessions | id customer_id channel campaign_id date content_asset_id | customer_id/content_asset_id nullable; FKs |
| leads | id customer_id session_id channel campaign_id date intent status order_id variant_id | session_id/order_id/variant_id nullable; status open/converted/lost |
| purchase_receipts | id purchase_order_id date quantity | positive; sum by PO = received_qty |
| supplier_payments | id purchase_order_id date amount_cents | sum by PO = paid_cents; actual event dates |
| shipments | id order_id date status delivered_date | delivered_date nullable; status in_transit/delivered |
| invoices | id order_id date amount_cents status kind | status issued/void; kind management_statement (non-fiscal) |
| expense_payments | id expense_id date amount_cents | sum by expense = paid_cents; actual event dates |
| inventory_counts | id variant_id date counted_qty | as_of physical count; discrepancy is a business alert |
| lifecycle_events | id product_id date from_stage to_stage reason | product FK; final to_stage matches product.lifecycle; versioned transitions |
| experiments | id name hypothesis primary_metric guardrail start_date end_date status | status completed/running; synthetic randomized example |
| experiment_assignments | id experiment_id customer_id arm assigned_date | arm control/treatment; unique experiment/customer |
| experiment_outcomes | id assignment_id date converted net_revenue_cents contribution_cents returned | one outcome/assignment; converted/returned 0/1; contribution may be negative |

Total: 30 source tables. Canonical currency MXN cents. No customer PII, external business writes, servers or paid APIs. Never infer known zero from missing coverage. Synthetic conversion experiment outcomes are simulated, never evidence of real lift. Native analytical agents are separate from deterministic validation and report calculations.

## Warehouse interface

`alma.warehouse.build_warehouse(data, path) -> dict` creates a new typed SQLite database, validates schema/relations/reconciliations, imports atomically; `query_mart(path, name) -> list[dict]`; `export_marts(path, folder) -> dict`; `inspect_schema(path) -> dict`. Fixed SQL names, safe read-only query boundary. `ingest_batch(path, data) -> dict` is content-hash idempotent for exact same snapshot; rejects changed immutable rows instead of silently overwriting. Explicit quarantined input errors must preserve prior data. Tables include PK/FK/CHECK and STRICT types. Full core business validation applies after projection; missing_cost yields unknown margin; broken_link rejected. Errors raise ValueError. Supporting manifest can be separate from canonical tables.

Marts, minimum output names: sales_daily, inventory_position, inventory_aging, procurement, cash_daily, finance_monthly, channel_performance, customer_cohorts, experiment_results, funnel_conversion, reconciliation. All cash uses payment event dates. Reconcile SQL totals against independent source sums. Include SQL lineage and metric definitions. Avoid join fanout. Coverage-driven unknowns explicit.

## Fixture scale and semantics

At least 36 variants across Pilates sock colors/sizes and sportswear, 365-day calendar, 1200 orders, multiple item baskets, repeat and immature cohorts, returns both restocked and written off, split payments/receipts, stock ledger, unmet demand, 12 months expenses, synthetic randomized assignment. Product/sample concepts never sold. All supplied rows satisfy temporal FKs including customer acquisition and payment-before-shipment; campaigns/sessions/leads match the linked order. Quantity never negative in normal. stock_pressure is valid but low cover/discrepancies; promotion_illusion valid with discounts eroding contribution; cash_squeeze valid with supplier prepayments stressing cash; missing_cost intentionally null; broken_link intentionally invalid FK. Scenario metadata documents mechanism, never observed business fact.

## Process / native agent interface (parent ownership)

Parent owns `alma/process_engine.py`, `alma/native_agents.py`, `alma/workspace.py`, CLI additions, process JSON and agent JSON contracts. Runner emits immutable task requests bound to dataset and mart hashes and requires separately submitted native-agent responses. Runs record transitions and replays; gates fail closed; any external action is proposal only. A native Codex agent executes bounded analysis in the present task; its response and query trace are validated then ingested. CLI sign-in is unavailable in this environment; do not pretend unattended model execution is configured. CLI uses explicit request/response bridge, with runnable deterministic orchestration and actual native-agent receipts delivered here.
