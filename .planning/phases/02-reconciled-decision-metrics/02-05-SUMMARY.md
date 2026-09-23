---
phase: 02-reconciled-decision-metrics
plan: 05
subsystem: operating-cash-marts
tags: [cash, forecasts, coverage, temporal-intake, reconciliation, tdd]
requires:
  - phase: 01-verified-operating-workspace
    provides: typed source-pack intake and immutable verified cuts
  - phase: 02-reconciled-decision-metrics
    provides: 02-04 cash layers, private bundle and semantic registry
provides:
  - future-dated forecast intake with unchanged observed cutoff
  - null UNKNOWN dependent cash measures when movements are MISSING but balances remain
  - ESTIMATED projected daily/weekly cash beside MEASURED independent close
affects: [phase-2-independent-verification, downstream-metric-consumers]
tech-stack:
  added: []
  patterns: [typed-row-temporal-gate, null-versus-zero-coverage, metric-specific-cash-status]
key-files:
  created: []
  modified: [alma/operating_interchange.py, alma/operating_finance_marts.py, alma/operating_marts.py, tests/test_operating_intake.py, tests/test_operating_marts_finance.py, tests/test_operating_marts_publication.py]
key-decisions:
  - "Defer only cash event_date cutoff validation until its typed level is known."
  - "Retained balance evidence identifies a scenario but never proves missing movements are zero."
  - "Determine cash metric status from observed, projected, and coverage dependencies, not generic complete coverage."
patterns-established:
  - "Semantic cash lineage resolves by exact scenario, horizon, layer, week and eligible event dates."
requirements-completed: [MET-03, MET-07]
duration: 20min
completed: 2026-09-23
---

# Phase 2 Plan 05: Cash Gap Closure Summary

**Future cash forecasts pass real intake, retained balances no longer invent missing movements, and forecast-derived cash remains ESTIMATED beside the measured close.**

## Accomplishments

- EXPECTED, COMMITTED and SCENARIO events after the September 21 cutoff preserve exact dates, IDs, source hashes and unchanged observation coverage. Future RECONCILED and other observed facts still fail intake.
- A MISSING cash-events source with retained observed 2,000,000-cent balances publishes its scenario and evidence while actual movement, close, layers and minimum remain null UNKNOWN. Explicit ZERO remains distinct and can reconcile to the observed 2,000,000-cent close.
- A 13-cent EXPECTED outflow yields a 1,099,987-cent ESTIMATED daily close and minimum in both horizons; the independently reconciled 1,100,000-cent close remains MEASURED. Future days 55/56/90/91 reconcile to exact -11/-41 horizon layers and exclude day 91.
- Semantic cash rows now retain exact horizon/layer/week status and source references; scenario amounts stay outside the baseline projected close.

## TDD Task Commits

1. **Task 1 intake:** RED `f600e55`; GREEN `43e2095`.
2. **Task 2 retained balance:** RED `cbcef3b`; GREEN `792ea5a`.
3. **Task 3 forecast and future horizon:** RED `9787fcb`; GREEN `ec59cc2`.
4. **Additional validation negatives:** `9caf192`.

## Verification

- `.venv/Scripts/python.exe --version`: Python 3.12.14.
- Intake: **17/17 passed**; Phase 2 mart suite: **37/37 passed**.
- Full suite after the last test change: **189/189 passed**.
- `scripts/verify_v2.py --output build/verification-v2-phase2-cash-gap-closure`: **passed**, 189 tests and all six expected scenario outcomes; receipt in `build/verification-v2-phase2-cash-gap-closure/verification.json`.
- `compileall` and `git diff --check`: passed; working tree clean before this summary.

## Deviations from Plan

None. The additional Task 1 negative-control test commit completes the plan's explicit invalid-level, malformed-date, origin, identity and supersession cases without changing implementation scope.

## Known Limits

- `forecast_status=REVIEW` remains a policy authority fact rather than a MetricRow measurement status. Unapproved projected daily balances remain unavailable.
- Independent Phase 2 re-verification and shared planning-state updates are owned by the orchestrator.

## Self-Check: PASSED

- All six owned source/test files and this summary exist.
- Each task's RED and GREEN commit resolves in Git.
- No new network or public surface, package dependency, or known stub was introduced.
