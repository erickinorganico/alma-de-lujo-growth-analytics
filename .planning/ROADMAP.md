# Roadmap: Alma OS Final v1.0.0

## Overview

A private weekly cut moves through versioned intake, canonical analytical marts, native analyst and independent reviewer decisions, an offline client and analyst kit, and a verified v1.0.0 release. Each phase delivers a usable local capability while preserving v0.2/v0.3 behavior. The v1 workspace is aggregate specific and parallel to the historical synthetic warehouse; it must not invent orders or customers from workbook totals. Exact calculations stay in SQL/Python, private cuts stay under ignored `.local/`, and external business actions remain prohibited. Phase-local tests accompany implementation; Phase 5 proves the integrated milestone and release gates. Real client correctness, owner adoption, fiscal policy, and the Pilates-socks winner hypothesis remain external acceptance gates, not synthetic release claims.

## Phases

- [x] **Phase 1: Versioned Operating Intake** - A validated private cut becomes an immutable, restorable analytical workspace.
- [x] **Phase 2: Reconciled Decision Metrics** - Canonical marts expose exact, coverage-aware operating and product measures.
- [x] **Phase 3: Governed Weekly Decision Cycle** - Current-cut evidence reaches real native analysis, independent review, and next-cut closure.
- [ ] **Phase 4: Offline Client and Analyst Kit** - Users receive usable workbooks, a navigable offline portal, and a one-command weekly workflow.
- [ ] **Phase 5: Acceptance and v1.0.0 Release** - Regression, two-week closure, privacy, Excel, archive, and CI evidence support a reproducible release.

## Phase Details

### Phase 1: Versioned Operating Intake
**Goal**: Analysts can turn a versioned, non-PII weekly source pack into one trustworthy private operating workspace and restore the same cut later.
**Depends on**: Nothing in v1; builds on the released v0.2/v0.3 contracts without changing their evidence.
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):
  1. An analyst can initialize blank or clearly synthetic source packs and see each domain's exact fields, grain, keys, units, provenance, and version.
  2. An analyst can import a valid private pack into a new immutable workspace; malformed, duplicate, conflicting, or PII-bearing input is rejected before any metrics appear.
  3. A cut manifest exposes stable identity, cutoff, timezone, source hashes, coverage, quality, and relationships, with missing and zero values kept distinct.
  4. Costs, purchases, receipts, obligations, payments, cash, stock, budgets, quality, sales readiness, and loans resolve through canonical SKU/event identities rather than competing ledgers.
  5. An analyst can export, restore, and verify a workspace with identical hashes and row relationships; tampering fails verification.
**Plans**: 5 plans

Plans:
- [x] 01-01: Define versioned operating-source contracts, keys, units, provenance, and blank/synthetic pack initialization.
- [x] 01-02: Build strict import, canonical identity validation, immutable SQLite workspace, and coverage/quality manifest.
- [x] 01-03: Add export/restore verification and intake failure controls for duplicates, conflicts, tampering, and privacy.

### Phase 2: Reconciled Decision Metrics
**Goal**: Analysts and owners can inspect one exact, coverage-aware account of costs, units, cash, demand learning, and actionable exceptions for a cut.
**Depends on**: Phase 1
**Requirements**: MET-01, MET-02, MET-03, MET-04, MET-05, MET-06, MET-07
**Success Criteria** (what must be TRUE):
  1. An owner can compare known cost, complete cost, markup, gross margin, and contribution by effective cost version; allocations reconcile to the cent and incomplete costs remain unknown.
  2. An analyst can reconcile ordered, received, inspected, accepted, rejected, non-sellable, loaned, reserved, and available units once, with no duplicate receipt or return event inflating stock.
  3. An owner can view outstanding obligations and applied payments alongside separate reconciled, committed, expected, undated, and scenario cash in eight- and thirteen-week windows; budget and drop/channel financial states reconcile without double counting.
  4. An owner can inspect launch sell-through, variant mix, mature return/quality rates, stock exposure, and recorded unmet demand with explicit denominators, windows, and coverage; an exposed stockout does not become a weak-preference claim.
  5. Sales-facing readiness and quality/loan exceptions show an owner, action, date, and closure state without internal cost disclosure; every metric exposes its formula, unit, grain, sources, unknown rule, guardrail, owner, and decision use.
**Plans**: 3 plans

Plans:
- [x] 02-01: Materialize versioned cost and purchase/inventory/receipt marts with exact unit and cent reconciliation.
- [x] 02-02: Materialize obligation/payment, layered cash, and budget/drop/channel marts with non-additive financial states.
- [x] 02-03: Materialize product-learning and readiness/quality/loan exception marts, then register metric definitions and coverage rules.
- [x] 02-04: Close independent verification gaps in partitioned cost, cohort maturity, cash layers, empty domains and metric semantics.
- [x] 02-05: Close final cash gaps in future projections, missing movement coverage and forecast status.

### Phase 3: Governed Weekly Decision Cycle
**Goal**: A current private cut can produce evidence-bound native analysis, independent review, an owner-ready packet, and decisions that carry into the next cut.
**Depends on**: Phase 2
**Requirements**: FLOW-01, FLOW-02, FLOW-03, FLOW-04, FLOW-05
**Success Criteria** (what must be TRUE):
  1. An analyst can submit a private workbook or v1 source pack and receive a current-cut report and native task bundle tied to the cut's evidence hash.
  2. A real native analyst response is accepted only when its schema and exact current-cut JSON references validate; it cannot change the workspace or authorize business execution.
  3. A different native reviewer can inspect the same evidence and analysis; identical reviewer identity, stale hashes, or changed evidence block a terminal approval.
  4. The terminal packet visibly separates facts, unknowns, hypotheses, and recommendations; each recommendation names a metric, guardrail, population, window, and closure rule.
  5. An owner can register a reviewed decision with source hash, owner, due date, status, and closure evidence; unresolved and stale items reappear in the next cut.
**Plans**: 4 plans

Plans:
- [x] 03-01: Bridge workbook/source-pack intake to a current-cut report and hash-bound native task requests.
- [x] 03-02: Validate real native analyst dispatch/response and separate reviewer dispatch/response, then produce governed terminal packets.
- [x] 03-03: Implement validated decision register, next-cut carry-forward, stale-action detection, and closure evidence checks.
- [x] 03-04: Align the executable weekly-cycle schema with real terminal packets and governed later cuts, with strict drift and privacy regressions.

### Phase 4: Offline Client and Analyst Kit
**Goal**: A client can prepare a cut offline and an analyst can navigate, run, and package the full local weekly workflow.
**Depends on**: Phase 3
**Requirements**: CLIENT-01, CLIENT-02, CLIENT-03, CLIENT-04
**Success Criteria** (what must be TRUE):
  1. A client can use blank or clearly synthetic operational workbooks for every v1 source domain, with readable instructions and input validation.
  2. A client or analyst can open the offline portal and distinguish historical demo evidence from the current private cut while navigating sources, metric definitions, processes, native roles, decisions, exceptions, and lineage.
  3. An analyst can follow one documented command path to initialize, validate, build, review, carry forward, and package a weekly cut without a server.
  4. The client package opens offline with blank/example workbooks and the operating guide; private filled cuts and native responses are absent.
**Plans**: 6 plans

Plans:
- [ ] 04-01: Extend the contract-driven workbook generator and validation for all v1 domains using blank/synthetic materials.
- [ ] 04-02: Generate the offline portal from verified manifests and show demo/current provenance, metrics, decisions, exceptions, and lineage.
- [ ] 04-03: Wire and document the one-command analyst cycle and build the offline client kit with private-content exclusions.
- [ ] 04-04: Integrate the sanitized public-kit build into the weekly command with immutable package evidence and restart verification.
- [ ] 04-05: Redesign the offline executive portal, verify source/chart parity and responsive accessibility, then bind fresh visual evidence to the rebuilt public kit.
- [ ] 04-06: Close partial native-analysis PASS and capture actual 200% zoom/reduced-motion evidence, then rebind and audit the public kit.
**UI hint**: yes

### Phase 5: Acceptance and v1.0.0 Release
**Goal**: The final package is reproducible, private, backward compatible, and supported by current two-week operational evidence.
**Depends on**: Phase 4
**Requirements**: REL-01, REL-02, REL-03, REL-04
**Success Criteria** (what must be TRUE):
  1. Existing v0.2/v0.3 verification still passes, while v1 acceptance proves positive, partial, tamper, duplicate, double-count, and two-distinct-week scenarios, including one reviewed decision carried to closure or a flagged stale state.
  2. Workbook arithmetic agrees with an independent Decimal oracle, and any changed formulas have a fresh Microsoft Excel recalculation receipt and visual inspection tied to delivered bytes.
  3. A clean Git archive and GitHub Actions reproduce tests, build artifacts, source hashes, privacy checks, and offline package links across the supported Windows/Linux boundaries.
  4. The v1.0.0 release package extracts and works offline, carries a matching checksum, runbook, and acceptance evidence, and contains no private cuts, native responses, secrets, or PII.
**Plans**: 3 plans

Plans:
- [ ] 05-01: Add and run v1 invariant, adversarial, and two-week end-to-end acceptance alongside v0.2/v0.3 regression gates.
- [ ] 05-02: Verify workbook formulas with independent arithmetic and fresh Excel evidence when needed; prove clean-archive/CI reproducibility and privacy.
- [ ] 05-03: Build and audit the versioned offline ZIP, checksum, runbook, and release acceptance record.

## Progress

**Execution Order:** Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5. Plans within a phase may run in parallel only where their inputs and owned files are independent; integration and verification follow their prerequisites.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Versioned Operating Intake | 3/3 | Complete | 2026-09-22 |
| 2. Reconciled Decision Metrics | 5/5 | Complete | 2026-09-23 |
| 3. Governed Weekly Decision Cycle | 4/4 | Complete | 2026-09-23 |
| 4. Offline Client and Analyst Kit | 0/6 | Gap closure planned | - |
| 5. Acceptance and v1.0.0 Release | 0/3 | Not started | - |

**Coverage:** 25/25 v1 requirements mapped exactly once. External gates EXT-01..03 remain outside the software phase count and require separate owner or observed-data evidence.
