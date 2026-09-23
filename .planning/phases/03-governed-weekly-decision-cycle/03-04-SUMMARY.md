---
phase: 03-governed-weekly-decision-cycle
plan: 04
subsystem: weekly-cycle-contracts
tags: [json-schema, powershell, test-json, decision-register, privacy]
requires:
  - phase: 03-governed-weekly-decision-cycle
    plan: 02
    provides: exact native analyst/reviewer artifacts and terminal packet producer
  - phase: 03-governed-weekly-decision-cycle
    plan: 03
    provides: governed decision anchors and cross-cut carried projection
provides:
  - exact closed JSON Schema for the emitted terminal packet
  - strict optional-together decision register and carried-decision current-cut contract
  - dependency-free named-fragment validation with bounded diagnostics
  - producer-derived drift, privacy and negative contract controls
affects: [04-offline-client-and-analyst-kit, 05-acceptance-and-v1-release]
tech-stack:
  added: []
  patterns: [producer-derived-schema-fixtures, closed-json-contracts, status-only-validation]
key-files:
  created:
    - scripts/validate_weekly_contract.ps1
    - tests/test_weekly_cycle_schema.py
  modified:
    - contracts/weekly-cycle-v1.schema.json
key-decisions:
  - "The production packet remains authoritative: the schema describes its exact 15 fields and does not synthesize the obsolete evidence_hashes field."
  - "Governed current-cut fields are optional together, recursively closed, and reuse the decision-register anchor semantics."
  - "The validator emits only an allowlisted definition token and VALID/INVALID status, including for malformed definition input."
patterns-established:
  - "Schema fixtures are built through production code in disposable synthetic roots."
  - "Fixed objects reject undeclared fields; dynamic hash maps constrain key names, values and cardinality."
requirements-completed: [FLOW-04, FLOW-05]
metrics:
  duration: 40 min
  completed: 2026-09-23
  tasks: 2
  files: 3
---

# Phase 3 Plan 4: Weekly Cycle Contract Closure Summary

**The published weekly-cycle schema now validates the exact terminal packet and governed cross-cut decision artifacts emitted by production, with portable PowerShell validation and fail-closed drift controls.**

## Performance

- **Duration:** 40 minutes
- **Started:** 2026-09-23T19:50:02Z
- **Completed:** 2026-09-23T20:29:48Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Replaced the obsolete packet contract with the exact 15-field producer shape, including recursively closed facts, recommendations, analyst summaries, reviewer content, provenance and prohibited external execution.
- Added strict decision anchor, binding and carried-decision definitions. First cuts remain valid; governed later cuts require `decision_register` and `carried_decisions` together.
- Added a package-free Draft 2020-12 fragment validator around PowerShell `Test-Json`. It keeps the complete `$defs` map in memory, accepts only named public definitions, writes no validation copy and returns bounded status-only diagnostics.
- Added producer-derived positives and missing, extra, hash, type, status, authority and malformed-definition negatives across the full weekly exchange.
- Locked the exact public native receipt allowlists and proved schema validation leaves the tracked receipt and private synthetic fixture tree unchanged except for the explicit disposable input file.

## Task Commits

Each TDD task was committed atomically:

1. **Task 1 RED: real packet/current-cut contract cases** - `96add3a`
2. **Task 1 GREEN: exact packet and governed current-cut schema** - `712bdf1`
3. **Task 2 RED: exchange drift and receipt privacy locks** - `3c677d7`
4. **Task 2 GREEN: bounded validator diagnostics** - `2033949`

## Files Created/Modified

- `contracts/weekly-cycle-v1.schema.json` - Exact closed packet, decision anchor, binding and carried-row definitions with current-cut co-dependency.
- `scripts/validate_weekly_contract.ps1` - Allowlisted named-fragment validation through built-in `Test-Json`, with no package or temporary validation copy.
- `tests/test_weekly_cycle_schema.py` - Fresh producer fixtures, exact key parity, full exchange drift matrix, privacy assertions and negative controls.

## Decisions Made

- Kept production artifacts authoritative and changed only the stale public schema; no field was added to or renamed in the packet producer.
- Retained every existing current-cut required field and made governed fields optional together so historical first cuts keep validating.
- Modeled analyst roles separately where reviewer presence is impossible, while retaining the complete role enum for reviewer-inclusive challenges.
- Constrained genuine maps by allowed key shape, value schema and producer cardinality instead of weakening fixed objects.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Information disclosure] Bounded malformed definition diagnostics**
- **Found during:** Task 2 (contract drift and receipt privacy)
- **Issue:** The first validator implementation echoed an untrusted, non-allowlisted definition string, which permitted multiline log injection even though artifact bodies remained private.
- **Fix:** Unknown definition input now maps to the fixed `UNRECOGNIZED` token; allowlisted definitions retain their exact public name.
- **Files modified:** `scripts/validate_weekly_contract.ps1`
- **Verification:** The malicious multiline negative returns exactly `definition=UNRECOGNIZED status=INVALID` and contains no injected content.
- **Committed in:** `2033949`

---

**Total deviations:** 1 auto-fixed bug. **Impact:** The fix tightened the planned privacy boundary without changing schemas, producers or accepted artifact semantics.

## Issues Encountered

- The initial RED harness had a PowerShell string-formatting error. It was corrected before the RED commit, after which the tests failed only on the intended obsolete packet and current-cut schema gaps.

## Verification

- Schema contract suite: 7/7 passed in 167.849 seconds.
- Phase 3 plus process/client focused suites: 73/73 passed in 399.199 seconds.
- Full discovery: 224/224 passed in 502.120 seconds.
- Release privacy audit: 522 tracked text files checked, zero findings, license present, PASS.
- Python compile and `git diff --check`: PASS.

## Known Stubs

None. Empty arrays in schema definitions are bounded domain collections produced by verified runtime artifacts, not placeholders.

## User Setup Required

None - no package, credential or external service configuration is required. PowerShell 7 provides the built-in `Test-Json` validator used locally and in the existing Ubuntu CI environment.

## Next Phase Readiness

- Phase 3 now has an executable public contract for owner-ready terminal packets and governed cross-cut decision continuity.
- Phase 4 can safely consume packet and current-cut artifacts in the offline client kit while using the same schema fragments for acceptance.
- External gates EXT-01 through EXT-03 remain outside this synthetic contract closure and still require observed client evidence.

## Self-Check: PASSED

- All three implementation/test files and this summary exist.
- All four RED/GREEN task commits exist in Git history.
- Focused, full-regression, privacy audit, compile and diff gates passed.

---
*Phase: 03-governed-weekly-decision-cycle*
*Completed: 2026-09-23*
