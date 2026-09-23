---
phase: 02-reconciled-decision-metrics
plan: 01
subsystem: analytics
tags: [sqlite, exact-cents, inventory, policy, coverage]
requires:
  - phase: 01-versioned-operating-intake
    provides: Immutable operating-v1 cut, 22-source registry, STRICT SQLite workspace, source hashes and relationship digest
provides:
  - Verified read-only Phase 1 cut binding and semantic metric contract
  - Separately hashed, versioned management policy with synthetic example
  - Exact cost allocation and realized SKU/channel economics
  - Purchase receipt and stock custody reconciliation
affects: [02-02-finance, 02-03-learning-publication, phase-3-native-analysis]
tech-stack:
  added: []
  patterns: [read-only verified cut binding, integer-cent conservation, half-open local-date windows, coverage-aware metric status]
key-files:
  created: [alma/operating_mart_contracts.py, contracts/operating-metrics-policy-v1.schema.json, policies/operating-metrics-synthetic-v1.json, alma/operating_cost_inventory.py, models/operating_cost_inventory.sql, tests/test_operating_marts_cost_inventory.py]
  modified: []
key-decisions:
  - "A cost component belongs to one SKU/cost version; residual cents go to stable unit ordinals and unallocated source cents remain explicit."
  - "A physical receipt contributes to on-hand stock through its single accepted movement; count rows observe variance rather than adding stock."
  - "A real cut cannot show complete cost or contribution using an unapproved or synthetic policy."
patterns-established:
  - "Bind immutable source bytes, cut identity, STRICT schema, keys, foreign keys, and relationship digest before read-only mart queries."
  - "Carry coverage, policy identity, source references, and reconciliation ID separately from metric value."
requirements-completed: [MET-01, MET-02, MET-07]
duration: 15min
completed: 2026-09-22
---

# Phase 2 Plan 01: Reconciled Cost and Inventory Summary

**Verified operating-v1 cuts feed exact cent allocation, same-grain economics, and purchase/stock custody controls without treating partial coverage as zero.**

## Performance

- **Duration:** 15 minutes
- **Started:** 2026-09-23T04:30:00Z
- **Completed:** 2026-09-23T04:44:58Z
- **Tasks:** 3
- **Files created:** 6

## Accomplishments

- Bound all 22 Phase 1 sources and literal semantic fields to the actual STRICT SQLite tables, validating manifest/source/SQLite hashes, cut ID, keys, foreign keys, row counts, relationship digest, timezone and coverage before any read-only query.
- Added a distinct canonical SHA-256 management policy. Synthetic, REVIEW, stale, missing and approved states remain separate from metric measurement; the synthetic policy never authorizes a real cut.
- Reconciled 101 component cents as 34+34+33, retained unallocated cents and missing/estimated quality, selected historical effective cost versions, and calculated Decimal markup, gross margin and contribution at the eligible SKU/channel window.
- Reconciled 20 ordered / 18 received / 2 still due and a 24-unit stock count with 2 reserved, 1 non-sellable, 1 loaned and 21 available. A reported-only return adds no stock; a unique physical restock movement does.

## Task Commits

1. **Task 1:** `0be3b7b` RED, `bcdfa8d` GREEN
2. **Task 2:** `38fd4d7` RED, `38963d2` GREEN
3. **Task 3:** `1fa7b10` RED, `131ca8c` GREEN
4. **Integrity follow-up:** `6eb240f` source hash and policy rule negative controls

## Verification

- Focused cost/inventory module: 8 tests passed using `.venv/Scripts/python.exe` (Python 3.12.14, SQLite 3.53.1).
- Phase 1 intake module: 15 tests passed.
- Full repository unittest discovery after the final code change: 158 tests passed in 52.624 seconds.
- Python compile check and `git diff --check` passed. No generated filled cut or derived bundle was committed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Bound literal semantic field floor and declared foreign keys**
- **Found during:** Task 3 binding review
- **Issue:** A registry-derived map alone would silently follow a future incompatible Phase 1 field change.
- **Fix:** Added a literal 22-source semantic field floor, checked SQLite column types and declared foreign keys, and extended hash/policy negative controls.
- **Files modified:** `alma/operating_mart_contracts.py`, `tests/test_operating_marts_cost_inventory.py`
- **Verification:** Focused module and full unittest discovery passed.
- **Committed in:** `131ca8c`, `6eb240f`

**Total deviations:** 1 auto-fixed (Rule 2). No new external or network surface was introduced.

## Known Limits

- The checked-in synthetic pack has PARTIAL source coverage. Complete economics was verified on a disposable temporary copy with explicit COMPLETE sales and cost coverage. Real owner approval and fiscal treatment remain external gates.
- The final private derived-bundle publisher belongs to Plan 02-03. This plan exposes read-only calculations and writes no output artifact.

## Next Phase Readiness

Finance and learning marts can import `MetricDefinition`, `MetricRow`, `bind_cut`, and `load_policy`; the final Plan 02-03 integration can publish only after its own private-path and atomic-output checks.

## Self-Check: PASSED

All seven created files, including this summary, exist; all seven recorded task commits resolve in Git. No tracked file was deleted by these commits.
