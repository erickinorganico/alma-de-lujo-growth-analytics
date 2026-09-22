> Historical v0.1 reference. Current implementation and acceptance: [v0.2 PRD](../specs/PRD.md), [runbook](RUNBOOK-v2.md), and [release evidence](RELEASE.md).

# Integration verification

Status: **green on 2026-09-22 with the required runtime**
Scope: synthetic local analytical MVP only

## Run commands

From the repository root on Windows:

```powershell
C:\Users\erick\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests -v
C:\Users\erick\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m alma verify --output build/verification
```

The second command writes `verification.json` and `agent-evals.json`. It checks the standard-library test suite, five scenarios, CSV roundtrips, deterministic replay, and 15 deterministic analyst-packet eval cases. Verification output is evidence of local synthetic behavior only.

## Independent finance and stock oracle

`tests/test_analytics.py` contains a small scenario whose expected outputs are literal values rather than values recomputed by production helpers:

- one delivered order: 2 units × MXN 100.00 with MXN 10.00 line discount;
- one MXN 30.00 credit note;
- one unit returned and restocked;
- one separate MXN 20.00 cash refund;
- one partial PO: 10 ordered, 5 received, MXN 200.00 paid;
- one MXN 50.00 variable expense, MXN 30.00 paid; and
- stock movements of +10 opening, +5 receipt, -2 shipment, +1 restock.

| Measure | Expected |
|---|---:|
| Gross revenue | 20,000 cents |
| Discounts / credits | 1,000 / 3,000 cents |
| Net revenue | 16,000 cents |
| COGS after restock reversal | 4,000 cents |
| Gross profit / margin | 12,000 cents / 75.00% |
| OPEX / variable expense | 5,000 / 5,000 cents |
| Contribution / operating proxy | 7,000 / 7,000 cents |
| Cash in / cash out / net cash | 19,000 / 25,000 / -6,000 cents |
| On hand / reserved / available / inbound | 14 / 0 / 14 / 5 units |
| Gross sold units / sell-through | 2 / 6.67% (1 net unit / 15 opening-plus-receipt units) |
| Inventory value | 56,000 cents |

The fixture uses zero funnel spend because it has no marketing expense. This keeps the independent oracle compliant with the v1 marketing-spend reconciliation rule.

## Verification matrix

| Surface | Evidence | Required result |
|---|---|---|
| Exact finance and stock | `test_hand_computed_finance_stock_and_commerce` | Literal cents/units match the independent oracle. |
| Determinism | generated-report equality and canonical JSON | Same seed yields equal report structures/bytes. |
| Controlled failures | missing cost, negative stock, missing payment, duplicate event | Report is `BLOCKED`; expected check is `UNKNOWN` or `FAIL`. |
| Coverage propagation | funnel, variants, orders, payments, expenses | Dependent outputs are null/`UNKNOWN`, never false zero. |
| Unsafe structures | strict schema, PII/extra columns, broken FK, invalid delivery date | `ContractError` or withheld report before unsafe analysis. |
| Inventory lifecycle | launched zero-stock versus idea/sample lifecycle | Launched zero becomes `STOCKOUT`; idea/sample remains `PRELAUNCH` and cannot propose a buy. |
| Commercial invariants | marketing spend and shipment prepayment | Marketing expenses reconcile to funnel spend; settlement precedes/equal shipment and shipment precedes/equal delivery. |
| Returns/refunds | separate rows and event effects | Restock affects inventory/COGS; refund affects cash; neither implies the other. |
| Decision governance | three deterministic analyst packets | Inventory, finance, and growth packets use one validated schema, evidence refs, unknowns/hypotheses, and blocked actions. |
| Action denial | adversarial payloads | `execute_action` always raises `PermissionError`. |
| Output ownership | unowned nonempty directory | Build rejects it and preserves existing content. |
| Storage | CSV and SQLite roundtrips | Reconstructed data equals canonical synthetic data. |
| Reports | Markdown, HTML, three SVGs | Synthetic warning visible; no script/remote asset; nulls readable; negative/zero chart values not distorted. |
| Receipts | `receipt.json` | Every declared artifact exists and its SHA-256 matches. |
| Agent evals | `agent-evals.json` | All 15 cases pass; malformed evidence/action gates fail closed. |

## Verified evidence

The affected standard-library suite completed with **33 tests run, 33 passed, 0 failures, 0 errors, and 0 skipped**. This includes the independent finance/stock oracle, coverage matrix, FK/date fail-closed regressions, lifecycle separation, reporting safety/unknown/signed-value checks, artifact receipts, and decision guards.

Repository verification wrote `build/verification/verification.json` and `build/verification/agent-evals.json` with overall `passed=true`:

- `normal`: `PASS`, no quality problems, CSV roundtrip passed;
- `missing_cost`: `BLOCKED` on `cost_coverage`, CSV roundtrip passed;
- `negative_stock`: `BLOCKED` on `stock_nonnegative` and dependent `reservations`, CSV roundtrip passed;
- `missing_payment`: `BLOCKED` on `payment_reconciliation` and `shipment_prepayment`, CSV roundtrip passed;
- `duplicate_event`: `BLOCKED` on `unique_movements`, CSV roundtrip passed;
- deterministic replay: passed; and
- deterministic analyst-packet eval: all **15 of 15 cases passed**, covering three packets per scenario plus fabricated/empty evidence, approval/execution bypass, invalid schema, and direct-action denial cases.

The prior HTTP test was removed because this repository intentionally has no server. It was replaced with analytical artifact, output-preservation, CSV/SQLite roundtrip, report-safety, and receipt-hash checks.

This green run does not establish real Alma sales, demand, formal accounting correctness, production freshness, stakeholder adoption, causal impact, provider-backed LLM quality/token savings, or safe real-data ingestion.
