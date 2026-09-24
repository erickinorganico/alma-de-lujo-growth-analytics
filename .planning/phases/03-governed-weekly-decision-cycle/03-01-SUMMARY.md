---
phase: 03-governed-weekly-decision-cycle
plan: 01
subsystem: weekly-analytical-cycle
tags: [operating-cut, reconciled-marts, native-task-bridge, immutable-evidence, tdd]
requires:
  - phase: 01-versioned-operating-intake
    provides: validated source packs, canonical private workspaces, and cut verification
  - phase: 02-reconciled-decision-metrics
    provides: complete private mart bundles, metric registry, and source lineage
provides:
  - verified current-cut report bound to exact Phase 1 and Phase 2 artifact bytes
  - six role-specific native analyst requests with bounded evidence and strict local references
  - private start/status/verify CLI with resumable WAITING_ANALYSTS state
affects: [03-02-native-review, 03-03-decision-continuity, 04-final-workbooks]
tech-stack:
  added: []
  patterns: [read-only-upstream-verification-adapter, canonical-hash-bound-requests, atomic-private-cycle-publication]
key-files:
  created: [alma/weekly_cycle.py, contracts/weekly-cycle-v1.schema.json, scripts/run_weekly_cycle.py, tests/test_weekly_cycle.py]
  modified: []
key-decisions:
  - "Verify every Phase 2 manifest artifact through a read-only adapter because Phase 2 exports a builder but no standalone verifier."
  - "Persist source-pack provenance in private cycle state while keeping the canonical current-cut bytes route-independent."
  - "Keep native execution outside deterministic preparation; all new cycles remain WAITING_ANALYSTS."
patterns-established:
  - "Revalidate upstream bytes, canonical current-cut bytes, exact requests, bundle inventory, and event checkpoint on every status or verify call."
requirements-completed: [FLOW-01]
duration: 9h
completed: 2026-09-23
---

# Phase 3 Plan 01: Verified Current-Cut and Native Task Bundle Summary

**A validated source pack or verified upstream boundary now produces the same current-cut evidence and six immutable, role-specific native task requests without claiming analyst execution.**

## Accomplishments

- The source-pack route invokes the real Phase 1 builder/verifier and Phase 2 builder, then checks every derived bundle artifact, registry, contract hash, lineage, source hash, coverage, and cut identity before publication. An unchanged rerun reuses the verified upstream artifacts and private cycle bytes.
- `current-cut.json` preserves exact metric rows, definitions, source hashes, coverage, quality, reconciliation, lineage, cutoff, timezone, and the verified synthetic marker. Missing cash coverage blocks only dependent finance analysis in the focused negative control.
- Six Terra/Luna/Sol analyst requests carry exact report, manifest, mart, contract, and role evidence hashes; strict RFC 6901 pointers resolve locally. Requests declare response/query-trace-only write scopes and remain in `WAITING_ANALYSTS`.
- The CLI supports source-pack or prebuilt-boundary `start`, plus revalidating `status` and `verify`. It rejects direct workbook intake with explicit Phase 4 ownership and prints only paths, statuses, and hashes.

## Task Commits

1. **Task 1 current-cut boundary:** RED `6903222`; GREEN `f06f014`.
2. **Task 2 immutable requests:** RED `1a9fce2`; GREEN `49e80da`.
3. **Task 3 private CLI:** `ce5e6d7`.

## Verification

- Focused weekly-cycle and historical process-engine modules: **19/19 passed**.
- Full unittest discovery: **198/198 passed**.
- `scripts/audit_release.py`: **passed**, 506 publishable text files checked, zero findings.
- `py_compile` for all changed Python files and `git diff --check`: **passed**.
- CLI tests exercised both input routes, unchanged source-pack rerun, status/verify, invalid route/workbook rejection, and exact request tamper failure.

## Decisions Made

- A read-only Phase 2 manifest/hash/lineage adapter verifies the builder's published output. It does not duplicate metric calculations or change Phase 2 contracts.
- The current-cut report is independent of input route; route provenance belongs in private state and event checkpoint.
- No deterministic script writes an analyst response, query trace, dispatch receipt, review, or terminal packet.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing verification interface] Added a read-only Phase 2 bundle adapter**
- **Found during:** Task 1 interface binding.
- **Issue:** Phase 2 has a complete builder but no standalone public bundle verifier.
- **Fix:** Validate exact manifest/artifact hashes, canonical JSON, registry, metric contract, source/coverage/lineage, and cut identity in `alma/weekly_cycle.py` before requests exist.
- **Committed in:** `f06f014`.

**2. [Rule 1 - Bug] Reuse intact source-pack artifacts on an unchanged rerun**
- **Found during:** Task 2 idempotence test.
- **Issue:** The Phase 1 builder correctly rejects an existing cut, so a second source-pack start failed before reaching the idempotent cycle.
- **Fix:** Parse the pack identity, reuse only a verified existing cut and mart bundle, and persist `source_pack` provenance in state.
- **Committed in:** `49e80da`.

## Known Limits

- Direct workbook-to-v1 preparation remains Phase 4 scope. A workbook-derived cut can already enter through the same verified workspace/mart boundary.
- Native analyst and reviewer dispatch, response validation, and terminal packet creation belong to Plan 03-02. This plan truthfully ends at `WAITING_ANALYSTS`.
- The Phase 2 adapter verifies published artifacts and their contracts read-only; it does not recompute the mart metrics from source data.

## Self-Check: PASSED

- All four owned implementation, contract, and test files plus this summary exist.
- The Task 1 and Task 2 RED/GREEN commits and Task 3 implementation commit resolve in Git.
- No package, network endpoint, external business action, or known blocking stub was introduced.
