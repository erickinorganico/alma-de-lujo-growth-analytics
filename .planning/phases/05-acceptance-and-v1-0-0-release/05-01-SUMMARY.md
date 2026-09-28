---
phase: 05-acceptance-and-v1-0-0-release
plan: 01
subsystem: testing
tags: [release-acceptance, synthetic-data, native-review, decision-register]

# Dependency graph
requires:
  - phase: 04-offline-client-and-analyst-kit
    provides: Offline weekly adapter and client kit consumed by v1 acceptance.
provides:
  - Deterministic v1 acceptance runner and adversarial release matrix, with a post-fix 9/9 gate result.
  - Sanitized native acceptance receipt for two distinct synthetic cuts and 14 native tasks.
  - Evidence-backed week-one decision continuity and closure against the later cut.
affects: [05-02, 05-03, v1.0-release]

# Tech tracking
tech-stack:
  added: []
  patterns: [fail-closed release gates, hash-linked native receipts, synthetic decision continuity]

key-files:
  created:
    - evidence/v1.0/two-week-native.json
    - .planning/phases/05-acceptance-and-v1-0-0-release/05-01-SUMMARY.md
  modified:
    - scripts/verify_v1.py
    - tests/test_v1_release_acceptance.py

key-decisions:
  - "Treat the two-cut business scenario and decision as synthetic acceptance evidence; they do not establish a product winner, owner adoption, or authority to execute business actions."
  - "Preserve EXT-01 as UNKNOWN, EXT-02 as UNKNOWN, and EXT-03 as REVIEW."
  - "Normalize the documented relative prepare-live destination before comparing generated cycle paths, so the documented invocation works on Windows."

patterns-established:
  - "A live acceptance receipt is supported by distinct native task identities, validated artifact hashes, independent review, and terminal cut state."
  - "A later-cut closure must retain the week-one decision anchor and reference the verified week-two cut."

requirements-completed: [REL-01]

# Metrics
duration: not recorded
completed: 2026-09-28
---

# Phase 5 Plan 01: Two-cut v1 acceptance summary

**The v1 acceptance chain reached two distinct synthetic `READY_FOR_OWNER` cuts with 14 verified native tasks and one week-one decision closed against week-two evidence.**

## Performance

- **Duration:** Not recorded
- **Started:** Not recorded
- **Completed:** 2026-09-28
- **Tasks:** 3 plan tasks evidenced
- **Files modified in the current diff:** 3, including this summary

## Accomplishments

- The post-fix deterministic acceptance completed against candidate `f9af688c950610014cd99e0e358fe090a57f1fa4` with 9/9 gates PASS, 0 FAIL and 0 BLOCKED. The committed machine-readable receipt is `evidence/v1.0/regression-acceptance.json`.
- The final sanitized native receipt reports 14 distinct native tasks: 12 analysts and 2 separate Astra reviews across two different synthetic cutoffs. Both cuts reached `READY_FOR_OWNER`.
- The verified decision register records one synthetic week-one decision closed with evidence anchored to the distinct week-two cut. The receipt preserves the evidence hashes and excludes private response prose and query contents.
- Corrected `prepare_live` to resolve the documented relative `.local/...` output before checking generated absolute cycle paths, with the acceptance test exercising that relative invocation.

## Files Created/Modified

- `scripts/verify_v1.py` - Resolve relative `prepare-live` destinations before validating the output path.
- `tests/test_v1_release_acceptance.py` - Exercise `prepare_live` with the documented repository-relative destination.
- `evidence/v1.0/two-week-native.json` - Sanitized final receipt for both native cuts, identities, hashes, reviewer decisions, and later-cut closure.
- `.planning/phases/05-acceptance-and-v1-0-0-release/05-01-SUMMARY.md` - This plan summary.

## Decisions Made

- Kept the scenario explicitly synthetic; its Pilates-socks observations do not establish a winner.
- Kept external evidence gates at `EXT-01 UNKNOWN`, `EXT-02 UNKNOWN`, and `EXT-03 REVIEW`.
- The first `week_one` attempt ended in `REVIEW` and was archived outside the final receipt. The final receipt describes the subsequent accepted run only.

## Deviations from Plan

The documented relative `prepare-live` command exposed a path-normalization issue because prepared cycle paths are absolute on Windows. The implementation now resolves the output path before validating it, and the contract test covers the relative CLI form.

The deterministic rerun after the path correction is recorded as 9/9 PASS. Publication of the v1.0 release has not occurred, and this summary makes no claim that it happened.

---

**Total deviations:** 1 implementation correction
**Impact on plan:** The change aligns `prepare-live` behavior with its documented relative-path invocation; the post-correction deterministic rerun is now green.

## Issues Encountered

The first `week_one` attempt was `REVIEW`; it was archived outside the final receipt. The final receipt independently validates 14 distinct native task identities, two `READY_FOR_OWNER` cuts, and one verified later-cut closure.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The final native acceptance receipt is complete for the synthetic two-cut scenario, and deterministic acceptance is 9/9 PASS after the path correction. Release publication remains a separate gate. External gates remain `EXT-01 UNKNOWN`, `EXT-02 UNKNOWN`, and `EXT-03 REVIEW`.

---
*Phase: 05-acceptance-and-v1-0-0-release*
*Completed: 2026-09-28*
