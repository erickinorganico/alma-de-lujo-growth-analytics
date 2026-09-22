# Synthetic simulation v2

`alma.simulation.generate()` creates a deterministic synthetic source snapshot for the Alma de Lujo v2 contract. It is a fixture for local validation and warehouse development. It contains no real customers, customer contact information, external writes, servers, paid APIs, or observed business results.

```python
from alma.simulation import core_projection, generate
from alma.validation import validate

snapshot = generate(seed=42, scenario="normal", days=365, order_count=1200)
quality = validate(core_projection(snapshot))
```

The generator accepts an integer `seed`, one of `normal`, `stock_pressure`, `promotion_illusion`, `cash_squeeze`, `missing_cost`, or `broken_link`, an inclusive window length, and an exact order count. The snapshot ends on the fixed synthetic date `2026-09-21`; `metadata.start_date` is the first date in the requested window. Repeating the same arguments returns byte-for-byte equivalent Python values. The metadata includes `contract_version="2.0"`, full 30-table boolean coverage, the scenario mechanism, synthetic hypotheses, and an explicit limitation statement.

## Source tables and event flow

The 16 v1 tables retain their existing column order and semantics. The v2 source adds these 14 tables, for 30 total:

- `campaigns`, `content_assets`, `sessions`, and `leads` describe synthetic acquisition events. Every order has a campaign-matched session and lead; converted leads point to their order and first item. The fixture also contains a much larger anonymous public-session pool and open/lost leads so funnel conversion is a measurable synthetic drop rather than one lead per order.
- `purchase_receipts`, `supplier_payments`, and `expense_payments` record actual event dates. Receipt quantities reconcile to `purchase_orders.received_qty`; supplier and expense payments reconcile to their respective `paid_cents` values.
- `shipments` and `invoices` are operational and management records. Invoice `kind` is always `management_statement`; it is not a fiscal document.
- `inventory_counts` is a physical-count snapshot. A discrepancy is intentionally an alertable business condition, not a source-contract failure.
- `experiments`, `experiment_assignments`, and `experiment_outcomes` provide a randomized synthetic example. Enrollment closes seven days before the fixed experiment end (or at the available end for shorter snapshots), preserving a 1–7 day synthetic follow-up inside the declared window. Outcomes are simulated and do not prove conversion lift.
- `lifecycle_events` records product stage changes. Its final `to_stage` agrees with the product lifecycle; sample and concept products never appear in sold order items.

All IDs are synthetic. Money is integer MXN cents. Dates are ISO strings and remain within the snapshot. Payments precede any sale movement, sale movements precede delivery, returns follow delivery, and customers are acquired no later than their linked order. The ledger opens with enough stock to keep each valid scenario non-negative, then applies receipts, sales, restocked returns, and scenario-specific adjustments.

`core_projection(snapshot)` copies only the v1 tables and replaces coverage with the exact 16-table v1 coverage map. This is the compatibility boundary used with `alma.validation.validate`; v2 warehouse ingestion should validate the complete 30-table snapshot and its additional relations.

## Scenario mechanisms

| Scenario | Mechanism | Expected validation / analytical signal |
| --- | --- | --- |
| `normal` | Seasonal date mix, repeat customers, split payments and receipts, returns, stock ledger, and monthly expenses. | Core projection PASS; baseline synthetic metrics. |
| `stock_pressure` | Smaller safety stock, additional unmet-demand rows, and physical counts with controlled discrepancies. | Core projection PASS; lower final stock and more stock-pressure signals. |
| `promotion_illusion` | Discounts are generated at roughly 22–40% of line gross instead of the baseline 2–9%. | Core projection PASS; discount pressure reduces contribution. |
| `cash_squeeze` | Supplier payments cover open ordered quantities and are dated at the purchase order, before receipts. | Core projection PASS; higher and earlier supplier cash outflow. |
| `missing_cost` | Selected variants and their order items have `cost_cents` / `unit_cost_cents = null`. Purchase-order costs remain known source costs. | Core projection has `cost_coverage=UNKNOWN`; downstream margin and inventory valuation must remain unknown. |
| `broken_link` | One core order item and one linked lead reference a `variant-missing` ID after valid derivation. | Core projection reports a foreign-key failure; full warehouse ingestion must reject it. |

These are controls for analytical behavior, not business narratives. The metadata mechanism and hypotheses state what was generated; they must not be reported as observed demand, customer preference, cash health, or experiment evidence.

## Verification

Run the assigned simulation tests with the repository interpreter:

```powershell
& .venv/Scripts/python.exe -m unittest tests.test_simulation -v
```

The tests cover determinism, exact 30-table shape and insertion-order columns, 1,200-order scale, repeat customers, 36-plus variants, monthly expenses, event reconciliations, temporal bounds, v1 projection compatibility, all four valid business scenarios, the intentional unknown-cost scenario, the intentional broken-link scenario, and scenario-level signals. The existing validator performs quadratic-style reconciliation on the large generated fixture, so validation of one 1,200-order snapshot is expected to take a few seconds on a local machine.
