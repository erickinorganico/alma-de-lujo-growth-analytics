---
phase: 03-governed-weekly-decision-cycle
plan: 02
subsystem: native-analytical-cycle
tags: [native-codex, query-trace, dispatch-receipt, reviewer, terminal-packet, tdd]
requires:
  - phase: 03-governed-weekly-decision-cycle
    provides: 03-01 verified current-cut report and immutable analyst requests
provides:
  - strict v1 native response, registered-query-trace and parent dispatch validators
  - replayable six-analyst and independent-Astra-review state machine
  - advisory terminal packet and exact metadata-only synthetic acceptance receipt
affects: [03-03-decision-continuity, 04-final-workbooks, phase-3-verification]
tech-stack:
  added: []
  patterns: [typed-frozen-json-pointer, parent-attested-native-dispatch, accepted-artifact-replay, metadata-only-public-receipt]
key-files:
  created: [alma/native_agents_v1.py, agents/native-cycle-v1.roles.json, agents/RUN-NATIVE-CYCLE-v1.md, tests/test_native_agents_v1.py, evidence/v1/native-cycle-acceptance.json]
  modified: [alma/weekly_cycle.py, contracts/weekly-cycle-v1.schema.json, scripts/run_weekly_cycle.py, tests/test_weekly_cycle.py, tests/test_client_system.py]
key-decisions:
  - "Native responses are accepted only through exact frozen evidence, registered query results and parent-attested dispatch hashes."
  - "Astra reviews one request bound to all six accepted response, query-trace and dispatch digests."
  - "The public receipt exposes only synthetic metadata, task identities, hashes, terminal status and the attestation limit."
patterns-established:
  - "Status and every transition revalidate Phase 1/2 evidence, task bytes, accepted artifacts, journal checkpoints and terminal packet."
requirements-completed: [FLOW-02, FLOW-03, FLOW-04]
duration: 2h 5m
completed: 2026-09-23
---

# Phase 3 Plan 02: Native Review and Terminal Packet Summary

**Six actual parent-dispatched native analysts and one distinct Astra reviewer completed a verified synthetic cycle; the advisory packet reached `READY_FOR_OWNER` without authorizing business execution.**

## Accomplishments

- The v1 validator rejects stale request/report/manifest hashes, invalid RFC 6901 references, changed typed observations, extra or mutating fields, wrong role/model/provider, unregistered or altered metric queries, missing traces, and mismatched parent receipts. The registered read-only query selects exact frozen mart rows by reconciliation ID.
- Analyst responses can arrive in any order. Each accepted response, query trace and dispatch receipt is revalidated by exact canonical hash at status, resume and terminal reads. The hash-chained journal supports only an exact prior-checkpoint recovery after an interrupted state write.
- The separate Astra request binds all accepted analyst identities and response, trace and dispatch digests. The reviewer cannot reuse an analyst task ID. Its terminal packet keeps facts, unknowns, hypotheses, recommendations, challenges and provenance separate, and marks external execution `PROHIBITED`.
- The actual synthetic run has six parent-attested native task IDs with Terra/Luna/Sol routing and a distinct Astra task. Private responses, traces, receipts and the packet remain under ignored `.local/`; the public receipt is an exact metadata-only projection. Parent dispatch metadata is an attestation, not a provider signature.

## Task Commits

1. **Task 1 v1 validator and role contract:** RED `769dd1d`; GREEN `4aac339`.
2. **Task 2 native state machine:** RED `9fb27bb`; GREEN `86782cc`.
3. **Historical compatibility fix:** `4e174d4`.
4. **Task 3 real synthetic acceptance receipt:** `eb2c859`.

## Verification

- Focused weekly-cycle, v1 native-validator and historical process-engine gate: **29/29 passed**. The additional exact-checkpoint recovery test passed before Task 2 commit.
- Full unittest discovery after the historical test fix: **209/209 passed**. No code changed afterward.
- Actual private cycle and public receipt: `verify-acceptance` returned **PASS**, cut `eda52c0dcf84906cd66105088e0036bc71547df813033eb3022c6b63928598f2`, run `8e88f170a3057b71f3ea5185`, six accepted analysts, distinct reviewer and terminal `READY_FOR_OWNER`. Public receipt SHA-256 is `b7304c51509398bd133fa502d7f0bd13fdfd9b89d8a10a28ef362267ddafa1fc`; terminal packet SHA-256 is `b4c9ba41f7e8d261fba3611ddda81c8b2331f7fca11a718470b0de3c8de2c9c3`.
- Final contract/privacy gate: **6/6 focused tests passed**; exact public root and nested allowlists passed; `scripts/audit_release.py` checked **512** publishable text files with **zero findings**. Python compilation and `git diff --check` passed.

## Decisions Made

- Runtime task IDs, model IDs, effort and UTC timing are supplied by the parent after actual native execution. The local validator establishes consistency and integrity but does not claim a cryptographic provider signature.
- A reviewer sees the frozen cut, each analyst's original evidence and analysis, plus exact accepted hashes. Only a distinct Astra `READY_FOR_OWNER` verdict over all six accepted roles yields an owner-ready packet.
- `READY_FOR_OWNER` remains advisory. Owner selection, purchase, payment, refund, pricing, publishing and messaging are outside this cycle's authority.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical request field] Registered read-only query declaration**
- **Found during:** Task 1 native query-trace validation.
- **Issue:** Plan 03-01 requests did not yet declare a query ID that an analyst could execute and cite.
- **Fix:** Added a fixed registered metric-row query to every request and bound exact parameters, result pointers and row count in the v1 validator.
- **Committed in:** `4aac339`.

**2. [Rule 1 - Bug] Bounded reviewer request accepts six frozen evidences**
- **Found during:** Task 2 integration test.
- **Issue:** The 1 MiB response/trace bound also rejected the valid reviewer request containing six accepted analyses and their original evidence.
- **Fix:** Applied a separate 8 MiB reviewer/request cap while retaining the 1 MiB response and trace cap.
- **Committed in:** `86782cc`.

**3. [Rule 3 - Blocking historical test assumption] Scope legacy agent-card inventory**
- **Found during:** Full discovery after Task 2.
- **Issue:** The v0.2 client-system test treated the required new `native-cycle-v1.roles.json` catalog as an eighth legacy single-role agent card.
- **Fix:** Excluded versioned multi-role catalogs from that historical card glob; the new v1 seven-role catalog has its own focused contract test.
- **Committed in:** `4e174d4`.

## Known Limits

- The public receipt confirms exact local hashes and parent-recorded native metadata; it does not independently authenticate the model provider.
- The acceptance run is synthetic. Private-client correctness, owner adoption and external business outcomes remain unproven.
- Owner decisions and next-cut continuity are Plan 03-03 work. Shared planning-state updates remain with the phase orchestrator.

## Self-Check: PASSED

- All owned implementation, contract, runbook, test and acceptance files plus this summary exist.
- Both TDD RED/GREEN pairs, the historical compatibility fix and the actual acceptance commit resolve in Git.
- The public receipt revalidates against private terminal state; no private source path, response prose, customer information, new network endpoint, package dependency or blocking stub was introduced.
