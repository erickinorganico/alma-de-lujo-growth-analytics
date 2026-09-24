# Phase 2: Reconciled Decision Metrics — Context

## Decisions

These decisions come from `AGENTS.md`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, and `.planning/ROADMAP.md`. No separate Phase 2 owner interview has approved the proposed business policies in `02-RESEARCH.md`.

- **D-01 — Canonical cut.** Phase 2 reads the immutable, aggregate-specific Phase 1 v1 workspace and its verified cut manifest. It does not alter the v0.2 warehouse, invent customer/order rows, or mutate accepted source facts.
- **D-02 — Exact money and conservation.** Relational money is integer MXN cents. Python `Decimal` handles ratios and explicit rounding. A source cent or unit enters each economic/physical projection once; allocations retain deterministic residual cents and unallocated balances. A Phase 1 cost component belongs to one SKU/cost version; indivisible batch cents can be assigned across stable unit ordinals within that SKU, never invented multi-SKU targets.
- **D-03 — Coverage and time.** Missing, partial, measured zero, not applicable, estimated, and error remain distinct. All marts retain cut identity, source hashes, as-of timezone, event date, window, lineage, and reconciliation result. Unverified coverage cannot become a complete metric.
- **D-04 — Distinct economic facts.** Cost, purchase, receipt, obligation, payment, settled cash, budget, quality, loan, and aggregate sales are separate canonical facts. A PO/invoice/expense/payment chain does not create competing liabilities, spend, or cash.
- **D-05 — Product learning limits.** Product learning uses declared cohorts, denominators, maturity and availability exposure. Stockout-limited sales, unlinked returns, or absent demand logging do not establish weak preference or zero demand. Phase 1 unmet-demand coverage is source-wide, so only recorded observations are published and an absent channel row is never measured zero. The Pilates-socks winner hypothesis remains `REVIEW` without eligible observed data.
- **D-06 — Private analytical output.** Filled cuts and derived reports stay under ignored `.local/` with canonical private-root checks. Sales-facing projections allow only public-safe row categories, fields and values. No internal cost, supplier terms, budget, bank amount, recipient token or PII leaks. No external business execution occurs.
- **D-07 — Compatibility and authority.** Existing v0.2/v0.3 outputs and tests remain intact. Phase 2 supplies deterministic evidence for Phase 3 native interpretation and independent review; owner policy and fiscal treatment are not inferred from synthetic fixtures.

## Agent's Discretion

- Use separate SQL and Python modules for cost/inventory, finance, and learning/exception families. SQL preaggregates by canonical IDs; Python enforces controls, performs Decimal ratios/cent allocation, and serializes read-only outputs.
- The Phase 1 schema is pending. The first Phase 2 task must bind actual table and column names, keys, coverage fields, date semantics, and source hashes. It must compare available relations to the semantic input contract and block publication of any dependent metric when a required fact or linkage is absent. Do not silently fabricate missing relations or infer aggregate transactions.
- Proposed management formulas, maturity lengths, exposure cadence, drop/channel allocation bases, owner roles, and thresholds live in a separate versioned policy artifact with schema, effective interval, canonical hash and status. The builder takes an explicit policy path; missing/stale policy blocks dependent calculations, unapproved real-cut policy is `REVIEW`, and synthetic policy never asserts owner approval.
- Materialize derived marts into a new private output bundle keyed by cut hash and metric-contract version; keep the Phase 1 workspace immutable. Use one registry contract for every metric and a sales-facing allowlist.

## Deferred Ideas

- Owner approval of fiscal/tax definitions, bank opening evidence, real-cut correctness/adoption, and hero-product validation remain external acceptance gates `EXT-01..03`.
- Storefront, CRM, ERP, web backend, autonomous purchases/payments/refunds, and real customer PII remain out of scope.

## Phase Boundary

Phase 2 covers `MET-01..07`: materialized measurements, coverage, reconciliation, metric definitions, and action-ready exception evidence. Phase 3 owns native interpretation, independent review, recommendations, decision register, and next-cut closure. Phase 4 owns offline client workbooks and portal.

## Multi-Source Coverage Audit

| Source | Item | Plan | Status |
|--------|------|------|--------|
| GOAL | Exact, coverage-aware costs, units, cash, demand learning and exceptions for one cut | 02-01, 02-02, 02-03 | COVERED |
| REQ | MET-01 cost versions, allocations, margin and contribution | 02-01 | COVERED |
| REQ | MET-02 purchase/receipt/stock custody conservation | 02-01 | COVERED |
| REQ | MET-03 obligation/payment and 8/13-week layered cash | 02-02 | COVERED |
| REQ | MET-04 sell-through, mix, mature return/quality, exposure, recorded unmet demand | 02-03 | COVERED |
| REQ | MET-05 budget/drop/channel source states and allocation | 02-02 | COVERED |
| REQ | MET-06 sales readiness and quality/loan action exceptions | 02-03 | COVERED |
| REQ | MET-07 formula, unit, grain, window, sources, unknown, guardrail, owner, decision use | 02-01, 02-02, 02-03 | COVERED |
| RESEARCH | Final Phase 1 relation binding, cut verification, read-only derived bundle | 02-01, 02-03 | COVERED |
| RESEARCH | SQL integer preaggregation; Python Decimal ratios and residual cents | 02-01, 02-02, 02-03 | COVERED |
| RESEARCH | Zero/partial/estimated/unknown status, policy review and temporal windows | 02-01, 02-02, 02-03 | COVERED |
| RESEARCH | Join, duplicate, stock, cash, cost, exposure and privacy negative controls | 02-01, 02-02, 02-03 | COVERED |
| CONTEXT | D-01, D-02, D-03, D-04 | 02-01, 02-02, 02-03 | COVERED |
| CONTEXT | D-05, D-06, D-07 | 02-03 | COVERED |

Dependency condition: Phase 1's `01-CONTEXT.md` now specifies variant/day availability, qualified unmet-demand logging, budget allocation, stock movement/custody, `cash_balance_evidence.csv`, and aggregate `delivery_cohort_id` links on sales and quality events. The 02-01 schema-binding task must verify that the finished Phase 1 implementation actually delivers those sources, fields, relationships and coverage in the immutable cut. Independent balance evidence is required before a cash balance is called `RECONCILED`; cohort linkage and maturity are required before a mature return rate is measured. If a private cut lacks either observation, publish `UNKNOWN`/`PARTIAL` for the dependent measure and identify the gap. `UNKNOWN` is not permission to ship an intake contract incapable of collecting a required Phase 2 measure.
