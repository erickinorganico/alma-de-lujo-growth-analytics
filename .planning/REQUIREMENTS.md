# Requirements: Alma OS Final

**Defined:** 2026-09-22  
**Core Value:** A weekly business cut must travel from source evidence to a reviewed, owner-ready decision and the next week's closure without losing unknowns, duplicating money or stock, or exposing private data.

## v1 Requirements

### Versioned data intake

- [x] **DATA-01**: Analyst can initialize blank or synthetic-example v1 source packs with exact CSV schemas, grains, keys, units and provenance fields.
- [x] **DATA-02**: Analyst can build a private immutable operating workspace from a source pack; malformed, duplicate or conflicting rows fail before metrics are published.
- [x] **DATA-03**: Every cut records source hashes, cutoff, timezone, coverage, quality, relationships and a stable cut identity without PII.
- [x] **DATA-04**: Costs, purchases, receipts, obligations, payments, cash, inventory, budgets, quality, sales readiness and loans share canonical SKU/event identities and never create competing ledgers.
- [x] **DATA-05**: A workspace can be exported, restored and verified with the same hashes and row relationships.

### Metrics and decisions

- [ ] **MET-01**: Cost marts distinguish known sum, complete cost, merchandise markup, gross margin and contribution, with version history, allocations and deterministic residual cents.
- [ ] **MET-02**: Purchase and inventory marts reconcile ordered, received, inspected, accepted, rejected, non-sellable, loaned, reserved and available units exactly once.
- [ ] **MET-03**: Finance marts reconcile canonical obligations and applied payments, and separate reconciled, committed, expected, undated and scenario cash for eight- and thirteen-week views.
- [ ] **MET-04**: Product-learning marts report launch sell-through, variant mix, mature return/quality rates, availability exposure and recorded unmet demand with denominators and coverage.
- [ ] **MET-05**: Budget/drop/channel marts keep approved, committed, incurred, paid, outstanding and unallocated amounts distinct and reconciled.
- [ ] **MET-06**: Sales-readiness, quality and loan-custody marts produce an owner/action/date/closure exception queue without exposing internal costs to sales-facing outputs.
- [ ] **MET-07**: Every metric definition declares formula, unit, grain, window, sources, unknown behavior, guardrail, owner and decision use.

### Governed weekly cycle

- [ ] **FLOW-01**: A private workbook or v1 source pack produces a current-cut report and task bundle bound to its evidence hash.
- [ ] **FLOW-02**: Native analyst responses are schema-validated, cite exact current-cut JSON references and cannot alter the workspace.
- [ ] **FLOW-03**: A different native agent independently reviews each analysis; stale hashes, changed evidence and identical reviewer identity fail closed.
- [ ] **FLOW-04**: A terminal packet separates facts, unknowns, hypotheses and recommendations, and every recommendation includes metric, guardrail, population, window and closure rule.
- [ ] **FLOW-05**: Reviewed decisions enter a validated register with source hash, owner, due date, status and closure evidence; open items carry into the next cut and stale actions are flagged.

### Client and analyst experience

- [ ] **CLIENT-01**: Client receives blank and synthetic-example operational workbooks covering all v1 source domains with readable instructions and validations.
- [ ] **CLIENT-02**: Final offline portal clearly separates demo evidence from a current private cut and exposes sources, metric definitions, processes, agent roles, decisions, exceptions and lineage.
- [ ] **CLIENT-03**: A documented one-command analyst workflow initializes, validates, builds, reviews, carries forward and packages a weekly cut without requiring a server.
- [ ] **CLIENT-04**: The client package includes the blank/example materials and offline operating guide; private filled cuts and native responses are excluded.

### Verification and delivery

- [ ] **REL-01**: Existing v0.2/v0.3 regression suite remains green and v1 adds positive, partial, tamper, duplicate, double-count and two-week E2E tests.
- [ ] **REL-02**: Generated workbooks pass independent arithmetic checks and a fresh Excel-engine recalculation/visual inspection whenever formulas change.
- [ ] **REL-03**: Clean Git archive and GitHub Actions reproduce tests, build, source hashes, privacy audit and package link checks on Windows/Linux boundaries.
- [ ] **REL-04**: A versioned v1.0.0 release contains the final offline package, checksum, acceptance evidence, runbook and no secrets/PII.

## External acceptance gates

- **EXT-01**: Real client-data correctness and adoption require an authorized first private cut and owner walkthrough; software ships with blank/synthetic contracts meanwhile.
- **EXT-02**: Fiscal/tax treatment, opening bank reconciliation and business approvals remain UNKNOWN until the owner or qualified reviewer supplies policy/evidence.
- **EXT-03**: The Pilates-socks winner hypothesis remains REVIEW until observed eligible data satisfies a declared validation window.

## Out of Scope

| Feature | Reason |
|---------|--------|
| React/Supabase transactional application | Conflicts with the repository's current analytical product contract. |
| Storefront, CRM, ERP or bank integration | Requires external systems, credentials and business execution beyond this scope. |
| Autonomous business actions | Human owner retains approval and execution authority. |
| Fiscal accounting or tax advice | Requires approved policy and qualified professional judgment. |
| Customer PII ingestion | Aggregate decision support does not require it. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01..05 | Phase 1 | Complete |
| MET-01..07 | Phase 2 | Pending |
| FLOW-01..05 | Phase 3 | Pending |
| CLIENT-01..04 | Phase 4 | Pending |
| REL-01..04 | Phase 5 | Pending |

**Coverage:** 25 v1 requirements, 25 mapped, 0 unmapped.

---
*Requirements defined: 2026-09-22 after GSD brownfield, domain and integration audits.*
