---
phase: 02-reconciled-decision-metrics
plan: 02
subsystem: analytics
tags: [sqlite, obligations, cash, budget, exact-cents, policy]
requires:
  - phase: 01-versioned-operating-intake
    provides: Immutable obligation, payment, cash, balance evidence, purchase, expense, budget and allocation facts
  - phase: 02-reconciled-decision-metrics
    provides: Plan 02-01 verified cut reader, metric definitions and independently hashed policy
provides:
  - Canonical obligation balance with recorded and authoritative coverage states
  - Supersession-safe settled, committed, expected, undated and scenario cash layers in 56/91-day windows
  - Source-grain budget/drop/channel states and exact target/unallocated cent bridge
affects: [02-03-learning-publication, phase-3-native-analysis]
tech-stack:
  added: []
  patterns: [source-grain integer aggregation, one active economic identity, independent balance reconciliation, stable largest-remainder cent allocation]
key-files:
  created: [alma/operating_finance_marts.py, models/operating_finance_marts.sql, tests/test_operating_marts_finance.py]
  modified: []
key-decisions:
  - "Recorded unpaid is visible with partial payment coverage; only complete coverage yields authoritative outstanding."
  - "An observed opening and independent matching closing are mandatory for a reconciled cash balance."
  - "Budget exposure is open commitment plus incurred; payments settle obligations and are never added to exposure."
patterns-established:
  - "Preaggregate payment IDs and source allocations before budget target joins."
  - "Keep scenario deltas and undated events outside dated baseline buckets."
requirements-completed: [MET-03, MET-05, MET-07]
duration: 15min
completed: 2026-09-22
---

# Phase 2 Plan 02: Reconciled Finance Marts Summary

**Canonical payments reduce one obligation, active cash events occupy one layer, and budget source cents reconcile across targets and explicit unallocated residuals.**

## Performance

- **Duration:** 15 minutes
- **Started:** 2026-09-23T04:46:00Z
- **Completed:** 2026-09-23T05:00:56Z
- **Tasks:** 3
- **Files created:** 3

## Accomplishments

- Reconciled a 180,000-cent obligation with one 100,000-cent application into 80,000 recorded unpaid; duplicate, over-applied and origin-conflicting identities fail. PARTIAL coverage retains the recorded exposure while withholding authoritative outstanding. VOID extinguishes the payable and rejects applied payment.
- Selected one active cash event per economic identity. The synthetic 900,000-cent settled outflow supersedes its commitment; an observed 2,000,000-cent opening and independent 1,100,000-cent closing reconcile only with complete source coverage. Missing or partial balance evidence keeps the close UNKNOWN.
- Computed half-open 56- and 91-day horizons from the same events. Day 56 enters only the 91-day horizon; undated and scenario amounts remain separate. Daily closes and minimum cash floor require a reconciled starting close and carry policy version/hash/status.
- Reconciled the synthetic 1,200,000-cent budget into 90,000 open commitment, 910,000 incurred and 900,000 paid, with 100,000 outstanding obligation. Under complete disposable coverage, headroom is 200,000 cents. A 101-cent source splits 50/50 across targets with 1 unallocated cent; two payment applications totaling 60 cents stay one settlement state.

## Task Commits

1. **Task 1:** `b6263e8` RED, `d4039e3` GREEN
2. **Task 2:** `387fd2d` RED, `17b6545` GREEN
3. **Task 3:** `a68d797` RED, `4acb10e` GREEN
4. **Integrity follow-up:** `83d562d` VOID obligation control

The shared policy bases required by Task 2/3 were added under the parent agent's `aba89f5` commit before use.

## Verification

- Finance focused module: 6 tests passed with `.venv/Scripts/python.exe`.
- Plan 02-01 cost/inventory module: 8 tests passed; Phase 1 intake module: 15 tests passed.
- Full repository unittest discovery after the final finance change: 164 tests passed in 48.297 seconds.
- Python compile check and `git diff --check` passed. No generated filled cut or finance bundle was committed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] VOID obligation retained a phantom payable**
- **Found during:** Final Task 3 review
- **Issue:** The original minus payment formula alone left a positive balance when the canonical obligation was VOID.
- **Fix:** Treat documented VOID as full cancellation and reject any applied payment on that origin.
- **Files modified:** `alma/operating_finance_marts.py`, `tests/test_operating_marts_finance.py`
- **Verification:** Finance focused and full unittest discovery passed.
- **Committed in:** `83d562d`

**Total deviations:** 1 auto-fixed (Rule 1). No new network or external disclosure surface was introduced.

## Known Limits

- Phase 1 has no separate adjustment-event source. The mart records the documented VOID cancellation and otherwise uses original obligation cents less unique applications. A future non-void adjustment must be added to the Phase 1 source contract before it can alter an authoritative balance.
- The checked-in synthetic pack marks finance coverage PARTIAL. Complete close and headroom oracles used disposable temporary packs with explicit COMPLETE coverage. Real policy approval and fiscal treatment remain external gates.
- Private derived-bundle publication and sales-facing filtering belong to Plan 02-03; this plan exposes read-only finance calculations.

## Next Phase Readiness

The integration plan can import `FINANCE_DEFINITIONS`, `project_obligations`, `project_cash` and `project_budgets`, then apply its private-path and atomic-publication controls.

## Self-Check: PASSED

All four files, including this summary, exist; every recorded task and shared policy commit resolves in Git. No tracked file was deleted by the plan commits.
