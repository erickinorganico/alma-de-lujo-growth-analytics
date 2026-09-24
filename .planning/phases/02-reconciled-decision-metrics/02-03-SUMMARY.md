---
phase: 02-reconciled-decision-metrics
plan: 03
subsystem: analytical-marts
tags: [sqlite, cohorts, exceptions, privacy, hashes, atomic-publication]
requires:
  - phase: 01-versioned-operating-intake
    provides: Immutable validated cuts, source coverage, and canonical Phase 1 relations
  - phase: 02-reconciled-decision-metrics
    provides: 02-01 cost/inventory and 02-02 finance mart builders
provides:
  - Coverage-aware product learning and recorded unmet-demand lower bounds
  - Governed exceptions and strictly allowlisted sales readiness projection
  - Complete metric registry and private, hashed, atomic operating mart bundles
affects: [Phase 3 decision packets, metric consumers]
tech-stack:
  added: []
  patterns: [read-only verified cut binding, explicit MetricDefinition registry, private staged publication]
key-files:
  created: [alma/operating_learning_exceptions.py, models/operating_learning_exceptions.sql, alma/operating_marts.py, tests/test_operating_marts_learning.py]
  modified: []
key-decisions:
  - "Reported returns are not physical received returns; immature or unlinked cohorts remain UNKNOWN."
  - "Unmet demand is a recorded lower bound, with no inferred channel-level zero."
  - "Private bundles are published only after cut, policy, metric registry, reconciliation, path and artifact checks pass."
patterns-established:
  - "Metrics carry grain, source coverage, reconciliation identity and separate policy lineage."
  - "Sales readiness uses fixed category, field and value allowlists."
requirements-completed: [MET-04, MET-06, MET-07]
duration: 17min
completed: 2026-09-22
---

# Phase 2 Plan 03: Learning, Exceptions, and Complete Mart Bundle Summary

**Coverage-aware cohort and exposure metrics, action exceptions, and all-family private bundles now preserve source and policy evidence through atomic publication.**

## Performance

- **Duration:** approximately 17 minutes
- **Started:** 2026-09-23T05:04:06Z (first TDD commit)
- **Completed:** 2026-09-23T05:21:05Z
- **Tasks:** 3
- **Files created:** 4, plus this summary

## Accomplishments

- Added exact numerator/denominator and coverage evidence for sell-through, variant mix, mature return and quality rates, stockout exposure, and recorded unmet demand. Unavailable exposure, reported-only return events, immature cohorts and missing opening counts cannot imply preference or a measured zero.
- Added stable exception IDs, source evidence hashes, policy-owned actions and due dates for incomplete cost, uninspected receipts, quality holds, readiness blocks, overdue loans and missing custody proof. The sales projection emits only allowlisted public fields and values.
- Built a single private bundle with cost/inventory, finance and learning facts, metric rows, registry, family controls, exception detail, public readiness, lineage and SHA-256 manifest. It verifies both the cut and policy before staging, and publishes atomically beneath the ignored `.local/operating-marts` root.

## Task Commits

1. **Task 1 learning:** RED `ec203a3`, GREEN `1eb1733`.
2. **Task 2 exceptions and sales privacy:** RED `768c146`, GREEN `4ad06c2`.
3. **Task 3 complete bundle:** RED `fbaada9`, GREEN `731cae7`.

The shared policy rule contract was updated by the orchestrator in `790ba9c`; this plan binds to its exact owner/action maps and due-day thresholds.

## Verification

- Focused Phase 2 mart suite: **22 tests passed**.
- Full `unittest` discovery: **172 tests passed**.
- `scripts/verify_v2.py --output build/verification-v2-phase2`: **passed**, including all six scenarios and 172 tests.
- `py_compile` for owned Python modules and `git diff --check`: passed.
- Two synthetic cuts retained independent source hashes and destinations; tampered input, missing/stale policy, unsafe output root, duplicate destination, missing definition, invalid status and failed reconciliation left no published bundle.

## Decisions and Limits

- The synthetic source still has PARTIAL coverage; the bundle retains UNKNOWN/PARTIAL states. `RETURN_REPORTED` is not counted as physically received, and the Phase 1 sources provide no non-void obligation-adjustment event, channel-level unmet-demand coverage, or separate asset/rights source.
- A real cut with policy status other than approved remains REVIEW; missing or stale policy blocks publication. The bundle remains private, and no real filled cut was used in tests.
- The symlink-negative test executes where filesystem privileges permit creating a symlink; Windows without that privilege skips only symlink creation. The production path validator checks symlinks and junctions.

## Deviations from Plan

- Used the project's verified `.venv\Scripts\python.exe` rather than the plan's unavailable Python 3.11 path, per the orchestrator's explicit instruction.
- Added `controls.json` to make family reconciliation identities and status counts directly inspectable.

## Known Stubs

None. The empty `io.StringIO(newline="")` value is an initialized CSV buffer, not a user-visible placeholder.

## TDD Gate Compliance

All three tasks have a failing `test(02-03)` commit before their passing `feat(02-03)` commit.

## Self-Check: PASSED

All four implementation/test files and the six task commits exist; the summary has been checked against the final verification results.
