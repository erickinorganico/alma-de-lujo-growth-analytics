# Alma OS Final

## What This Is

Alma OS is the final local analytical operating system for Alma de Lujo, a small sportswear business whose multicolor Pilates socks are a product hypothesis to validate with observed data. It lets the owner and analyst turn a private weekly cut into validated relational sources, deterministic metrics, governed native-agent review, traceable decisions, and an offline client package without creating a storefront, CRM or ERP.

## Core Value

A weekly business cut must travel from source evidence to a reviewed, owner-ready decision and the next week's closure without losing unknowns, duplicating money or stock, or exposing private data.

## Requirements

### Validated

- ✓ Synthetic v0.2 warehouse: 30 typed sources, 11 SQL marts, six processes, seven native roles and independent review — v0.2.0.
- ✓ Client workbook kit with 91-day cash plan, stock/price scenarios, private Decimal validator and Excel-engine evidence — v0.3.0.
- ✓ Offline atlas, guarded packaging, hashes, privacy audit and cross-platform CI — v0.3.0.

### Active

- [ ] Accept a versioned private operating cut through explicit non-PII CSV and workbook contracts.
- [ ] Integrate costs, purchasing, receipts, obligations, cash, inventory, budgets, quality, sales readiness and loans into one canonical analytical workspace.
- [ ] Produce decision-ready marts and exception queues with exact formulas, coverage and reconciliation.
- [ ] Bind each weekly cut to real native Codex analyst and independent reviewer responses.
- [ ] Carry reviewed decisions, owners, due dates, guardrails and closure evidence into the next cut.
- [ ] Deliver a polished offline portal, operational workbooks, analyst tools and a reproducible v1.0.0 package.

### Out of Scope

- Storefront, checkout, CRM, ERP, Supabase application or authentication — the governing repository contract defines a local analytical product.
- Autonomous purchases, payments, refunds, price changes, publishing or customer messages — owner approval and execution remain external.
- Fiscal accounting, tax advice, FIFO or moving-average valuation — these require an approved accounting policy and qualified review.
- Claims of real hero-product performance, adoption or business impact without authorized observed data.
- Collection of customer PII, private conversations, bank credentials or personal creator documents.

## Context

The v0.3.0 release is technically sound but its workbook path and synthetic warehouse path are separate. A client workbook creates `informe.json` and an analyst brief, while the existing native process engine only consumes the historical v0.2 workspace. The cost/operations slice is static and separate from the canonical marts; the decision register is blank and has no governed carry-forward.

The final milestone closes those connections with a parallel aggregate-specific operating workspace. It never fabricates orders or customers from workbook aggregates. Public examples remain synthetic; private filled cuts live only under `.local/` and are never packaged or committed.

## Constraints

- **Architecture**: Python 3.11+, SQLite, CSV/JSON/XLSX and offline HTML; no required server or paid inference provider.
- **Money**: Integer MXN cents in relational data and Decimal at input boundaries; binary floats are prohibited for financial truth.
- **Unknowns**: Missing, partial, zero, not applicable, estimated and error remain distinct.
- **Privacy**: Public Git/release artifacts contain blank or synthetic data only; private cuts stay under ignored `.local/` paths.
- **Agents**: Native Codex tasks provide interpretation; SQL/Python own exact calculations. A different agent reviews each analysis.
- **Authority**: External business execution is always `PROHIBITED`.
- **Compatibility**: Existing v0.2 and v0.3 evidence and release behavior remain regression protected.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build a parallel v1 operating-cut workspace instead of mutating the v0.2 synthetic warehouse | Prevents fabricated row-level orders/customers and preserves released evidence | — Pending verification |
| Use versioned CSV contracts plus Excel intake/export | Supports client use and deterministic validation without a server | — Pending verification |
| Treat cost, stock, obligation and cash events as separate canonical facts | Prevents duplicated units and money | — Pending verification |
| Add handoff modules as analytical tables and decisions, not transactional screens | Honors the repository's analytical product boundary | — Pending verification |
| Ship `v1.0.0` only after unified two-week E2E, independent native review and package audit | “Final” requires observable closure, not file count | — Pending verification |

## Evolution

After each phase, move verified active requirements to validated, update decisions and keep the current product description accurate. External dependencies remain explicit gates rather than silent defaults.

---
*Last updated: 2026-09-22 after final-product GSD intake and three independent audits.*
