---
phase: 04-offline-client-and-analyst-kit
plan: 04
subsystem: client-operations
tags: [weekly-cycle, deterministic-zip, immutable-receipt, restart-verification, tdd]

# Dependency graph
requires:
  - phase: 04-03
    provides: Supported weekly command, reproducible public kit builder and analyst runbook
provides:
  - Integrated public-package stage in the supported weekly command
  - Canonical package receipt and run-index binding
  - Fresh package revalidation before every continuation action
affects: [05-acceptance-and-release, weekly-operations, client-package-delivery]

# Tech tracking
tech-stack:
  added: []
  patterns: [build-then-audit, exact-safe-projection, immutable-receipt-binding, restart-revalidation]

key-files:
  created: []
  modified:
    - alma/weekly.py
    - tests/test_weekly_kit.py
    - docs/ANALYST-WEEKLY-v1.md

key-decisions:
  - "The existing weekly command invokes the audited public builder using only a new run-relative output path."
  - "Package identity is an exact safe projection shared by command result, canonical receipt and run index; the receipt hash remains in the existing receipts map."
  - "Every weekly-resume action rehashes and freshly audits the package before touching Phase 3 state."

patterns-established:
  - "Atomic package stage: builder, auditor or receipt failure removes the entire newly prepared cut."
  - "Committed restart proof: git archive must contain the package verifier before a restored private run can continue."

requirements-completed: [CLIENT-03]

# Metrics
duration: 26min
completed: 2026-09-23
---

# Phase 04 Plan 04: Integrated Public Package Stage Summary

**The supported weekly command now builds, audits, receipts and restart-verifies the deterministic public client ZIP while preserving honest WAITING and PROHIBITED authority states**

## Performance

- **Duration:** 26 min
- **Started:** 2026-09-23T16:55:35-07:00
- **Completed:** 2026-09-23T17:21:20-07:00
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Wired `build_client_kit()` followed by `audit_client_zip()` into `create_weekly_run()` without passing the private pack, workbook, marts, cycle, native evidence or register to the public builder.
- Added `receipts/public-package.json` with an exact safe key set: version, PASS status, run-relative path, ZIP and manifest hashes, member count, and allowlist/privacy/link dispositions.
- Bound the same package identity into `run-index.json` and the command result while keeping `WAITING_ANALYSTS`, `native_execution_claimed=false` and `external_execution=PROHIBITED` unchanged.
- Added fresh path, byte, receipt, index and audit verification before every `weekly-resume` action.
- Proved deterministic hashes across independent run roots, immutable replay, whole-cut cleanup after builder/auditor failures, tamper rejection and continuation from a clean committed archive.
- Replaced the detached packager instruction with one supported weekly command path and literal receipt/readback guidance.

## Task Commits

Each task was committed atomically:

1. **Task 1: Failing integrated package-stage contracts** — `e12a829` (RED)
2. **Task 2: Integrated immutable package stage and runbook** — `9a64c7f` (GREEN)

## Files Created/Modified

- `alma/weekly.py` — Builds and audits the public ZIP, projects its safe identity, writes the immutable receipt/index binding and revalidates it on continuation.
- `tests/test_weekly_kit.py` — Covers exact keys, hashes, inventory boundary, deterministic roots, replay, atomic cleanup, tamper and clean-archive restart.
- `docs/ANALYST-WEEKLY-v1.md` — Documents automatic package creation, paths, receipt fields, audit meaning and authority boundaries.

## Decisions Made

- Used `public-kit/Alma_OS_Client_v1.zip` as the single run-relative package path.
- Reused the existing package version and auditor output rather than introducing another package schema or duplicating ZIP logic.
- Represented the auditor allowlist disposition with its bounded PASS status and retained privacy and links as separate PASS fields.
- Kept the deep self-consistent content/secret mutation scanner outside this plan; it remains assigned to Phase 5 Plan 05-03.

## TDD Gate Compliance

- RED `e12a829` failed only because the integrated package call, receipt/index/result binding, atomic failure behavior, restart verification and updated guide were absent.
- GREEN `9a64c7f` passed the non-archive contracts before commit; the full focused class then passed from the new HEAD, proving `git archive` contained and executed `audit_client_zip`.

## Verification

- Exact post-commit `WeeklyPackageStageTests` + `GuideContractTests`: 7/7 PASS in 13.559 s.
- Full weekly/package/guide focused set: 14/14 PASS in 70.728 s.
- Client/workbook/security regressions: 44/44 PASS.
- Full repository suite: 255/255 PASS in 1120.808 s.
- `scripts/audit_release.py`: PASS, 544 publishable text files checked, zero findings.
- Python compilation, bounded owned-file privacy scan, stub scan and `git diff --check 4a529cf..HEAD`: PASS.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The clean-archive test correctly could not prove the new verifier before its bytes existed in `HEAD`. The implementation was committed after the other GREEN contracts, then the exact focused command was rerun from the new commit and passed without weakening the archive assertion.

## Known Stubs

None.

## Authentication Gates

None.

## User Setup Required

None - no dependency, server or external service was added.

## Next Phase Readiness

- CLIENT-03 is closed: the existing weekly command now reaches a receipted sanitized package through one restart-safe path.
- Phase 5 may exercise the full live native acceptance and the explicitly deferred 05-03 deep content mutation scanner.
- This plan makes no claim that the deferred deep content/secret audit has passed.
- No blockers remain.

## Self-Check: PASSED

- All three plan-owned implementation files and this summary exist.
- RED `e12a829` and GREEN `9a64c7f` resolve in repository history.

---
*Phase: 04-offline-client-and-analyst-kit*
*Completed: 2026-09-23*
