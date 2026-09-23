---
phase: 03-governed-weekly-decision-cycle
verified: 2026-09-23T20:46:43Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 9/10
  gaps_closed:
    - "The published operating-cycle-v1 schema now validates the real terminal packet and both first-cut and carried-decision current-cut documents."
  gaps_remaining: []
  regressions: []
---

# Phase 3: Governed Weekly Decision Cycle Verification Report

**Phase Goal:** A current private cut can produce evidence-bound native analysis, independent review, an owner-ready packet, and decisions that carry into the next cut.
**Verified:** 2026-09-23T20:46:43Z
**Status:** passed
**Re-verification:** Yes - after Plan 03-04 contract-gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | A verified v1 source pack reaches a current-cut report and six immutable role requests bound to exact Phase 1/2 evidence. | VERIFIED | Quick regression: the focused Phase 3 gate passed; `start_cycle_from_source_pack` still calls the real workspace and mart builders/verifiers before publishing tasks. |
| 2 | Current-cut and request publication fail closed on changed evidence, traversal, links, malformed pointers and unsupported paths. | VERIFIED | Weekly-cycle tamper/path/reference tests passed in the 73-test focused gate. |
| 3 | Only role-correct native responses with exact typed references, registered-query traces and parent dispatch hashes enter the cycle. | VERIFIED | Native response, query-trace, dispatch and role-routing tests passed unchanged. |
| 4 | Analysts preserve frozen evidence and review begins only after every configured analyst validates. | VERIFIED | Multi-analyst state-machine tests passed; accepted hashes remain frozen into the reviewer request. |
| 5 | A distinct Astra task reviews all accepted analyses; same identity, stale hashes or changed evidence fail closed. | VERIFIED | Retained private run revalidated with six analysts and distinct reviewer `/root/native_evidence_review`; identity/tamper tests passed. |
| 6 | The terminal packet separates facts, unknowns, hypotheses, recommendations and challenges, with complete recommendation controls. | VERIFIED | Real packet SHA-256 `b4c9ba...e2c9c3` revalidated; exact 15-field packet schema requires its five sections and `external_execution: PROHIBITED`. |
| 7 | A real synthetic acceptance receipt proves the bounded native run without publishing prose, private paths or queries. | VERIFIED | `verify-acceptance` returned PASS with unchanged receipt SHA-256 `b7304c...fa1fc`; privacy audit passed over 523 files. |
| 8 | Reviewed owner decisions are append-only, hash chained and safe to project/import through proposal-only CSV. | VERIFIED | Decision-register and integration tests passed in the focused and full gates. |
| 9 | Open decisions retain identity across the next cut; stale, extension and closure behavior uses exact later-cut evidence or explicit local attestation. | VERIFIED | Fresh governed second-cut fixture passed schema and decision continuity tests; anchor/status/tamper mutations fail. |
| 10 | The published operating-cycle-v1 schema validates actual terminal packets and current cuts with or without carried decisions. | VERIFIED | Real private packet and first-cut current cut returned `VALID`; producer-derived first and governed cuts passed; missing/extra/hash/authority/anchor/status/type mutations returned `INVALID`. |

**Score:** 10/10 truths verified

### Re-verification of Previous Gap

The previous gap had two manifestations in `contracts/weekly-cycle-v1.schema.json`. Both are closed:

- `$defs.packet` at lines 152-202 now declares the exact 15 fields produced by `build_terminal_packet`, removes obsolete `evidence_hashes`, closes nested objects, and preserves recommendation and authority constraints.
- `$defs.current_cut` at lines 121-127 now permits strict `decision_register` and `carried_decisions` definitions and uses `dependentRequired` so neither can appear alone.
- `tests/test_weekly_cycle_schema.py` builds artifacts through production code and validates real packet, first-cut, governed second-cut, all exchange definitions, structural drift, public receipt privacy and bounded unknown-definition diagnostics.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `alma/weekly_cycle.py` | Current-cut, task, state-machine, receipt and carry implementation | VERIFIED | Unchanged producer remains substantive, wired and fully exercised. |
| `alma/native_agents_v1.py` | Strict native validation and terminal packet producer | VERIFIED | Exact producer output validates against the aligned schema. |
| `alma/decision_register.py` | Append-only two-cut decision engine | VERIFIED | Carry, stale, extension and closure regression tests pass. |
| `contracts/weekly-cycle-v1.schema.json` | Executable contract for all seven exchange definitions | VERIFIED | Real and producer-derived artifacts validate; fixed shapes are closed and dynamic maps bounded. |
| `scripts/validate_weekly_contract.ps1` | Dependency-free named-fragment validator | VERIFIED | Uses PowerShell `Test-Json`, emits only definition/status, rejects unrecognized definitions and returns nonzero on invalid data. |
| `tests/test_weekly_cycle_schema.py` | Producer-to-schema positives, negatives and privacy locks | VERIFIED | Seven tests passed in 149.576s; no hand-authored substitute for packet/current-cut producers. |
| `contracts/decision-register-v1.schema.json` | Event, anchor, closure and CSV shapes | VERIFIED | Anchor and carried-decision semantics agree with weekly-cycle references. |
| `evidence/v1/native-cycle-acceptance.json` | Sanitized actual synthetic-cycle receipt | VERIFIED | Exact private reconstruction still passes; tracked receipt bytes and allowlists are unchanged. |
| `agents/native-cycle-v1.roles.json` and runbook | Seven native roles and operating procedure | VERIFIED | Routing and authority regressions pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| Phase 1/2 artifacts | `current-cut.json` and analyst requests | verified hashes and deterministic report build | WIRED | Weekly-cycle regressions pass. |
| analyst responses/traces/dispatches | Astra reviewer request | immutable accepted-hash map | WIRED | Real receipt and state machine revalidate. |
| Astra review | `decision-packet.json` | deterministic terminal projection | WIRED | Actual packet validates against `$defs.packet`. |
| terminal packet | decision register | exact recommendation and packet/source hashes | WIRED | Decision registration and tamper tests pass. |
| prior register anchor | governed next cut/tasks | closed binding and carried projection | WIRED | Fresh producer-derived second cut validates against `$defs.current_cut`. |
| producer output | weekly-cycle schema | PowerShell named-fragment validation | WIRED | Exact key parity and executable schema tests now fail on either producer or schema drift. |
| private cycle | public acceptance receipt | exact metadata-only reconstruction | WIRED | PASS; no packet prose or carried decision content crosses the boundary. |

### Data-Flow Trace (Level 4)

| Artifact | Source | Produces Real Data | Status |
|---|---|---|---|
| first `current-cut.json` | verified Phase 1 workspace and Phase 2 marts | Yes; real retained synthetic acceptance cut | FLOWING |
| governed `current-cut.json` | production cycle plus verified register anchor | Yes; fresh two-cut fixture with carried decision | FLOWING |
| `decision-packet.json` | six validated analysts plus distinct Astra review | Yes; retained terminal packet | FLOWING |
| weekly-cycle schema | exact producer documents | Yes; all seven definitions validated | FLOWING |
| native acceptance receipt | retained private terminal state | Yes; exact metadata projection | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Actual terminal packet schema | `validate_weekly_contract.ps1 ... -Definition packet ...decision-packet.json` | `definition=packet status=VALID` | PASS |
| Actual first current-cut schema | `validate_weekly_contract.ps1 ... -Definition current_cut ...current-cut.json` | `definition=current_cut status=VALID` | PASS |
| First and governed second cuts | `test_first_and_governed_current_cuts_match_schema` | Both producer-derived documents valid | PASS |
| Packet negative controls | remove required field, add undeclared field, change authority | Three `INVALID`, exit 1 | PASS |
| Complete schema suite | `python -m unittest tests.test_weekly_cycle_schema... -v` | 7 tests in 149.576s | PASS |
| Phase 3 focused regression | weekly schema/cycle/native/decision/process/client review | 73 tests in 446.294s | PASS |
| Full repository regression | `python -m unittest discover -s tests -q` | 224 tests in 519.716s | PASS |
| Public receipt private recheck | `run_weekly_cycle.py verify-acceptance` | PASS; receipt and terminal hashes unchanged | PASS |
| Publishable-scope privacy | `scripts/audit_release.py` | 523 files; zero findings | PASS |

### Probe Execution

No phase-declared `probe-*.sh` files apply. The named-fragment validator, producer-derived contract suite and private receipt verification are the executable probes for this phase.

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
|---|---|---|---|
| FLOW-01 | 03-01, 03-04 regression | SATISFIED | Source pack produces current-cut and hash-bound tasks; first-cut contract validates. |
| FLOW-02 | 03-02, 03-04 regression | SATISFIED | Exact native evidence, query trace, dispatch and no-execution controls pass. |
| FLOW-03 | 03-02, 03-04 regression | SATISFIED | Distinct Astra and stale/change/identity negatives pass. |
| FLOW-04 | 03-02, 03-04 | SATISFIED | Runtime packet and executable schema agree on separated categories, recommendations and authority. |
| FLOW-05 | 03-03, 03-04 | SATISFIED | Append-only decisions carry through a schema-valid second cut and close only with verified evidence/attestation. |

No Phase 3 requirements are orphaned.

### Anti-Patterns Found

No blocker or warning patterns remain in the 03-04 artifacts. No `TBD`, `FIXME`, `XXX`, `TODO`, `HACK` or placeholder markers were found. The gap closure did not modify production producers, historical artifacts, package manifests or the tracked acceptance receipt.

### Human Verification Required

None for Phase 3. Native metadata remains explicitly scoped as parent-runtime attestation rather than a provider cryptographic signature. Real customer correctness and adoption remain external gate EXT-01.

### Gaps Summary

No gaps remain. The governed weekly decision cycle works end to end, its retained native acceptance evidence revalidates, decisions carry and close across cuts, and the public JSON contract now matches the exact documents produced by current code with positive, negative, privacy and full-regression coverage.

---

_Verified: 2026-09-23T20:46:43Z_
_Verifier: Codex (gsd-verifier)_
