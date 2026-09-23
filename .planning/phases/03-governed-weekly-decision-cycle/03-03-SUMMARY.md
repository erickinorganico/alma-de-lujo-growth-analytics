---
phase: 03-governed-weekly-decision-cycle
plan: 03
subsystem: governed owner decisions
tags: [decision-ledger, hash-chain, two-cut, closure-predicate, private-cli]
requires:
  - phase: 03-governed-weekly-decision-cycle
    plan: 02
    provides: reviewed native READY_FOR_OWNER packet
provides:
  - append-only private owner decision ledger with independent terminal anchors
  - stable cross-cut decision carry, stale status and due-date extension history
  - typed machine closure and explicit local human-attestation closure
  - private management CLI and deterministic injection-safe CSV projection
affects: [04-offline-client-and-analyst-kit, 05-acceptance-and-v1-release]
tech-stack:
  added: []
  patterns: [canonical-json-hash-chain, independent-anchor, historical-prefix-projection, proposal-only-csv]
key-files:
  created:
    - alma/decision_register.py
    - contracts/decision-register-v1.schema.json
    - scripts/manage_decisions.py
    - tests/test_decision_register.py
  modified:
    - alma/weekly_cycle.py
    - scripts/run_weekly_cycle.py
key-decisions:
  - "Decision identity is derived once from the exact terminal packet hash and recommendation ID; later events preserve source and packet hashes."
  - "A carried cycle stores a historical register anchor and verifies it as a prefix, so later append-only events do not invalidate the frozen cut."
  - "CSV is a deterministic projection and proposal intake only; it never mutates canonical history."
  - "Human closure is labeled local attestation rather than authenticated identity proof."
metrics:
  duration: 50 min
  completed: 2026-09-23
  tasks: 3
  files: 6
---

# Phase 3 Plan 3: Governed Owner Decision Register Summary

Owner-ready native recommendations now become private, tamper-evident decisions that reappear in later weekly cuts and close only against exact verified evidence or an explicit local owner attestation.

## Performance

- **Duration:** 50 minutes
- **Started:** 2026-09-23T18:30:42Z
- **Completed:** 2026-09-23T19:20:56Z
- **Tasks:** 3
- **Files changed:** 6

## Accomplishments

- Added a canonical JSON event ledger with stable decision IDs, unique content-derived event IDs, a `GENESIS` hash chain, independent terminal anchors, allowlisted functional owner roles, bounded inputs and atomic locked writes.
- Revalidated each originating `READY_FOR_OWNER` packet, exact recommendation, packet bytes, current-cut hash and source hash before registration. Later verification rechecks the cited private packet and closure-cut artifacts.
- Bound unresolved decisions into the next `current-cut.json` and every native analyst request. The bound historical anchor remains verifiable after new ledger events are appended.
- Added deterministic stale evaluation at the declared `America/Tijuana` cutoff, append-only extensions with old/new due dates, exact JSON Pointer resolution and typed existence/string/integer/Decimal/boolean predicates.
- Added `init`, `register`, `advance`, `extend`, `carry`, `close`, `verify`, `export-csv` and `import-proposals` commands. CLI output contains only identifiers, statuses, counts and hashes.
- Added negative controls for history edits, stale anchors, invalid transitions, duplicate identities, PII-looking owner values, path traversal, unsafe formulas, duplicate proposals and forged closure evidence.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: append-only owner contract tests** - `366caa2`
2. **Task 1 GREEN: tamper-evident owner decision ledger** - `5ecfe01`
3. **Task 2 RED: two-cut continuity tests** - `31322e5`
4. **Task 2 GREEN: carry, stale, extension and closure** - `d0c389b`
5. **Task 3: private management CLI and verification controls** - `7e4744f`

## Files Created/Modified

- `alma/decision_register.py` - ledger creation, registration, transition replay, carry, stale, extension, closure, anchor and CSV operations.
- `contracts/decision-register-v1.schema.json` - versioned event, anchor, closure predicate and CSV projection contract.
- `scripts/manage_decisions.py` - private register lifecycle CLI with stable error receipts.
- `alma/weekly_cycle.py` - optional prior-register binding and carried-decision evidence in current reports and native tasks.
- `scripts/run_weekly_cycle.py` - prior register and anchor inputs for both supported cycle-start routes.
- `tests/test_decision_register.py` - owner contract, two-cut continuity, closure and CLI negative controls.

## Decisions Made

- Stable decision identity uses `sha256(packet_hash + recommendation_id)` once. Event identity includes canonical event content and sequence.
- Register anchors include the terminal event hash, event count and origin-map hash. Historical anchor verification reconstructs an exact prefix while allowing legitimate later events.
- Machine closure compares typed values from exact canonical later-cut bytes. Decimal expected values cross the input boundary as text; binary floats are rejected.
- `REVIEW` without an explicit attestation is the terminal result of an attempted human-judgment closure. A successful attestation records `LOCAL_ATTESTATION_NOT_IDENTITY_PROOF`.
- The shipped project timezone is `America/Tijuana`; cutoff timestamps must carry its valid `-07:00` or `-08:00` offset before local-date stale evaluation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Validated the project IANA timezone without adding `tzdata`**
- **Found during:** Task 2
- **Issue:** The bundled Windows Python runtime has no system IANA database, and package installation is prohibited by the plan.
- **Fix:** Required the declared `America/Tijuana` IANA name plus an aware cutoff with a valid local `-07:00` or `-08:00` offset, then evaluated due dates against the preserved local calendar date.
- **Files modified:** `alma/decision_register.py`
- **Verification:** All four two-cut continuity tests passed.
- **Commit:** `d0c389b`

**2. [Rule 1 - Bug] Prevented recursive closure-origin verification**
- **Found during:** Task 3
- **Issue:** Verifying a closed register re-entered the same bound cycle while reconstructing its historical register prefix.
- **Fix:** Historical prefix reconstruction verifies the complete hash chain and anchor without re-entering external origins; top-level register verification still revalidates every registration and closure origin.
- **Files modified:** `alma/decision_register.py`
- **Verification:** Exact later-cut closure test and full 217-test discovery passed.
- **Commit:** `7e4744f`

**3. [Rule 3 - Blocking] Replaced a stale historical test-module name in the verification run**
- **Found during:** Task 3 verification
- **Issue:** The plan named `tests.test_decisions`, which has never existed in repository history. Historical `alma.decisions` coverage lives in `tests.test_security`.
- **Fix:** Ran the remaining requested suites plus `tests.test_security`; full discovery independently covered the complete test inventory.
- **Files modified:** None
- **Verification:** 45 available focused tests passed, 10/10 security and historical decision tests passed, and 217/217 full discovery tests passed.
- **Commit:** N/A

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking issues). **Impact:** No package or architectural change; verification remains stricter and the exact repository test inventory is green.

## Verification

- `tests.test_decision_register.DecisionRegisterContractTests`: 3/3 passed.
- `tests.test_decision_register.DecisionContinuityTests` plus `tests.test_weekly_cycle`: 19/19 passed.
- Phase 3 and historical focused suites: all available tests passed; the stale `tests.test_decisions` name was replaced by its actual `tests.test_security` coverage.
- Full discovery: 217/217 passed in 315.984 seconds.
- Release privacy audit: 517 text files checked, zero findings, license present, PASS.
- `python -m py_compile` and `git diff --check`: passed.

## Known Stubs

None. Empty collections in the implementation are bounded accumulators populated from verified artifacts; no UI or report receives placeholder data.

## Next Phase Readiness

- Phase 4 can project the verified private register into the client workbook and offline portal using `REGISTRO_DECISIONES.csv` as a deterministic view.
- External gates EXT-01 through EXT-03 remain outside this synthetic acceptance: real customer correctness, owner adoption and the Pilates-socks winner hypothesis still require observed evidence.

## Self-Check: PASSED

- All four created files and both modified integration files exist.
- All five Task 1-3 commits exist in Git history.
- Full discovery, privacy audit, compile and diff checks passed.
