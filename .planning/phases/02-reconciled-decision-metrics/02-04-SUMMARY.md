---
phase: 02-reconciled-decision-metrics
plan: 04
subsystem: operating-marts
tags: [reconciliation, cash, cohorts, semantic-catalog, coverage, tdd]
requires:
  - phase: 01-verified-operating-workspace
    provides: immutable verified cuts and source coverage
  - phase: 02-reconciled-decision-metrics
    provides: 02-01 through 02-03 projections and private publication
provides:
  - canonical partition-invariant COGS with estimated quality propagation
  - cohort-specific mature return and defect rates with excluded evidence
  - complete coverage-aware cash and semantic metric publication
affects: [phase-2-verification, downstream-metric-consumers]
tech-stack:
  added: []
  patterns: [integer-prefix-cost-allocation, cohort-eligibility-pooling, family-path-semantic-audit]
key-files:
  created: [tests/test_operating_marts_publication.py]
  modified: [alma/operating_cost_inventory.py, alma/operating_learning_exceptions.py, models/operating_learning_exceptions.sql, alma/operating_finance_marts.py, alma/operating_marts.py, tests/test_operating_marts_cost_inventory.py, tests/test_operating_marts_finance.py, tests/test_operating_marts_learning.py]
key-decisions:
  - "Allocate cost cents across canonical SKU/version sales before report partition filters."
  - "Pool only mature, linked, covered delivery cohorts; retain excluded evidence explicitly."
  - "Classify family paths as defined metrics or documented facts and reject unknown measures."
patterns-established:
  - "Every published semantic family measure has a catalog entry and normalized row verified against the family projection."
requirements-completed: [MET-01, MET-02, MET-03, MET-04, MET-05, MET-06, MET-07]
duration: 90min
completed: 2026-09-22
---

# Phase 2 Plan 04: Reconciled Decision Metrics Gap Closure Summary

**Canonical cost allocation, cohort-specific learning, and coverage-aware private bundles close all five verified Phase 2 blockers.**

## Accomplishments

- A 101-cent component across three dated sales now allocates 34, 34, and 33 cents regardless of report partition; estimated complete costs remain ESTIMATED through economic ratios.
- Return and defect rates pool eligible mature delivery cohorts only. Recent, foreign, and unlinked observations remain explicit exclusions or UNKNOWN evidence.
- Valid independently observed cash, all five cash layers in both horizons, ZERO/MISSING domains, a semantic metric/fact catalog, and normalized decision measures publish in one immutable private bundle.
- No physical source, broken FK, missing definition, unclassified family measure, or mismatched semantic row can pass publication.

## Task Commits

1. **Task 1 RED:** `4802bb0`; **GREEN:** `56a3f08`.
2. **Task 2 RED:** `4f1cc9f`; **GREEN:** `6c00e1a`.
3. **Task 3 RED:** `22e0f8d`; **GREEN:** `61cabb5`.

The orchestrator also repaired the shared BoundCut null-window contract in `5a7f7a3` and aligned its fixture in `91e7142`; those files were outside this executor's ownership.

## Verification

- Phase 2 mart suite: **33/33 passed**.
- Full unit suite: **183/183 passed**.
- `scripts/verify_v2.py --output build/verification-v2-phase2-gap-closure`: **passed**; six scenario checks passed, including expected REVIEW for missing cost and BLOCKED for broken links.
- `compileall` and `git diff --check`: passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing application coverage in budget reconciliation**
- **Found during:** Task 3 empty-domain matrix.
- **Issue:** The budget projector assumed complete payment applications and rejected a previously settled obligation when payment coverage was MISSING.
- **Fix:** Bind obligation reconciliation to actual payment coverage; retain recorded exposure while withholding authoritative headroom.
- **Files modified:** `alma/operating_finance_marts.py`.
- **Committed in:** `61cabb5`.

**2. [Rule 2 - Completeness] Explicit source-domain evidence**
- **Found during:** Task 3 coverage review.
- **Issue:** ZERO/MISSING status was only in the bundle manifest, without row counts and empty reasons per source.
- **Fix:** Publish `domain_coverage.json` atomically with status, row count, and MISSING/declared-ZERO/no-row reason.
- **Files modified:** `alma/operating_marts.py`.
- **Committed in:** `61cabb5`.

## Known Limits

- Non-VOID obligation adjustments remain unsupported because no Phase 1 source exists for them; no adjustment was inferred.
- Synthetic policy/cuts prove calculation and publication behavior, not authorization for real business execution.

## Self-Check: PASSED

- All listed source, test, SQL, and summary files exist.
- Every RED/GREEN task commit resolves in Git.
- Bundle publication remains private and atomic; no new endpoint or public surface was introduced.
