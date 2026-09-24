---
phase: 03-governed-weekly-decision-cycle
status: ready
nyquist_validation: true
validated_requirements: [FLOW-01, FLOW-02, FLOW-03, FLOW-04, FLOW-05]
test_framework: unittest
---

# Phase 3 Validation: Governed Weekly Decision Cycle

## Purpose

Provide fast, deterministic evidence after every implementation task and reserve live native execution for the bounded synthetic acceptance task. Tests use only blank or clearly synthetic cuts in disposable private roots. No fixture response is evidence of live inference.

## Validation architecture

| Layer | Evidence | Rule |
|---|---|---|
| Contract | Focused `unittest` plus named `$defs` validation through PowerShell `Test-Json` | Runs after each TDD task, validates real producer artifacts and must distinguish pass from fail without printing private JSON. |
| Integration | Weekly-cycle, historical process and decision suites | Revalidates upstream bytes, event chains, state projections and compatibility. |
| Live native acceptance | Actual native task IDs plus response, registered-query-trace and dispatch hashes | Runs once in Plan 03-02 Task 3; deterministic fixtures cannot satisfy this gate. |
| Privacy | Exact public-receipt allowlist plus `scripts/audit_release.py` | Public evidence may contain synthetic metadata, hashes and statuses only. |
| Full regression | `unittest discover` | Runs at the terminal task of Plans 03-01, 03-03 and gap closure 03-04. |

Project interpreter: `.venv\Scripts\python.exe`. Commands must not use watch mode. Focused checks are the feedback path; full discovery and the release audit are terminal gates rather than per-edit checks.

## Requirement coverage

| Requirement | Planned evidence | Negative controls | Status |
|---|---|---|---|
| FLOW-01 | Source-pack route invokes actual Phase 1 build/verify and Phase 2 mart build/verify; prebuilt canonical boundary yields the same cut/report/task scope. | Changed source/report/manifest/mart bytes, path escape, symlink, unresolved required reconciliation, direct workbook argument in Phase 3. | COVERED |
| FLOW-02 | Strict v1 response, RFC 6901 pointer, typed-value, registered-query-trace and parent receipt validation. | Bad `~` escape, missing pointer, changed value, `null` to zero, wrong role/model/provider, response or trace hash mismatch, mutation/execution field. | COVERED |
| FLOW-03 | Reviewer request binds every response, trace and dispatch digest; Astra identity differs from all analyst identities. | Same task ID with another model, changed accepted analysis/trace, changed evidence, altered receipt, reviewer `BLOCKED`. | COVERED |
| FLOW-04 | Terminal packet preserves facts, unknowns, hypotheses, recommendations, reviewer challenges and provenance; every recommendation has the complete action contract. | Missing category/action field, invented fact, tampered packet/event journal, external execution request. | COVERED |
| FLOW-05 | Two distinct cuts prove register, carry-forward, stale, extension and typed closure or explicit human attestation. | Bad prior anchor, duplicate IDs, invalid transition, formula injection, forged/same-cut closure, failed predicate, missing attestation. | COVERED |

The 03-04 gap closure additionally requires the produced terminal packet and both current-cut variants to validate against their named Draft 2020-12 definitions. Contract negatives remove required fields, add undeclared fields, corrupt hashes/types/anchors and change execution authority. This closes schema drift without changing producer semantics.

## Per-task automated verification

| Wave | Plan / Task | Automated command | Expected outcome |
|---|---|---|---|
| 1 | 03-01 / 1 | `.venv\Scripts\python.exe -m unittest tests.test_weekly_cycle.WeeklyCycleEvidenceTests -v` | Source-pack and prebuilt-boundary identities match; upstream tamper blocks publication. |
| 1 | 03-01 / 2 | `.venv\Scripts\python.exe -m unittest tests.test_weekly_cycle.WeeklyCycleTaskBundleTests -v` | Six immutable role requests contain resolvable exact references and matching hashes. |
| 1 | 03-01 / 3 | `.venv\Scripts\python.exe -m unittest tests.test_weekly_cycle tests.test_process_engine -v && .venv\Scripts\python.exe -m unittest discover -s tests -q` | CLI remains private and historical plus full regressions pass. |
| 2 | 03-02 / 1 | `.venv\Scripts\python.exe -m unittest tests.test_native_agents_v1 -v` | Response, trace, receipt, role/model and v1 role-contract controls pass. |
| 2 | 03-02 / 2 | `.venv\Scripts\python.exe -m unittest tests.test_weekly_cycle tests.test_native_agents_v1 tests.test_process_engine -v` | Replayable analyst/reviewer state machine fails closed on changed evidence or identity. |
| 2 | 03-02 / 3 | `.venv\Scripts\python.exe scripts/run_weekly_cycle.py verify-acceptance --receipt evidence/v1/native-cycle-acceptance.json && .venv\Scripts\python.exe -m unittest tests.test_native_agents_v1 tests.test_weekly_cycle.NativeAcceptancePrivacyTests -q && .venv\Scripts\python.exe scripts/audit_release.py` | Actual synthetic task/trace/receipt hashes verify and the public receipt passes allowlist and repository privacy audit. |
| 3 | 03-03 / 1 | `.venv\Scripts\python.exe -m unittest tests.test_decision_register.DecisionRegisterContractTests -v` | Only intact owner-ready recommendations create append-only owner decisions. |
| 3 | 03-03 / 2 | `.venv\Scripts\python.exe -m unittest tests.test_decision_register.DecisionContinuityTests tests.test_weekly_cycle -v` | Later cut carries open work, flags stale work and closes only with valid evidence/attestation. |
| 3 | 03-03 / 3 | `.venv\Scripts\python.exe -m unittest tests.test_decision_register tests.test_weekly_cycle tests.test_native_agents_v1 tests.test_lifecycle tests.test_decisions tests.test_process_engine -v && .venv\Scripts\python.exe -m unittest discover -s tests -q && .venv\Scripts\python.exe scripts/audit_release.py` | All Phase 3, historical, full-regression and privacy gates pass. |
| 4 | 03-04 / 1 | `.venv\Scripts\python.exe -m unittest tests.test_weekly_cycle_schema.WeeklyCycleJsonSchemaTests -v` | Real terminal packet, first cut and governed later cut pass named schema fragments; missing/extra/hash/authority mutations fail. |
| 4 | 03-04 / 2 | `.venv\Scripts\python.exe -m unittest tests.test_weekly_cycle_schema tests.test_weekly_cycle tests.test_native_agents_v1 tests.test_decision_register tests.test_process_engine tests.test_client_review -v && .venv\Scripts\python.exe -m unittest discover -s tests -q && .venv\Scripts\python.exe scripts/audit_release.py` | Phase 3 exchange, historical behavior, public receipt privacy and full regression remain green. |

## Nyquist assessment

Every implementation task has an automated command, and none is marked missing, so no separate Wave 0 dependency is required. The TDD tasks create their named test files and failing cases before implementation in the same task.

| Wave | Implementation tasks | Tasks with automated verification | Sampling |
|---|---:|---:|---|
| 1 | 3 | 3 | PASS — 3/3 |
| 2 | 3 | 3 | PASS — 3/3 |
| 3 | 3 | 3 | PASS — 3/3 |
| 4 | 2 | 2 | PASS — 2/2 |

No three-task window lacks automated feedback. Focused module/class commands are the quick feedback loop. Full discovery, actual native acceptance and privacy audit may take longer and therefore appear only at plan terminal tasks.

## Live native acceptance gate

The Plan 03-02 Task 3 run is valid only when all of the following are true:

1. Six analyst tasks have actual native task IDs, correct Terra/Luna/Sol routing and parent-recorded UTC metadata.
2. Each analyst response and registered-query trace validates; the receipt binds both hashes.
3. The reviewer is a distinct Astra task and its request binds every analyst response, trace and dispatch digest.
4. Workspace, mart bundle, current-cut and request bytes remain unchanged through terminal validation.
5. `READY_FOR_OWNER` is advisory, contains the complete four-part packet and authorizes no external execution.
6. `evidence/v1/native-cycle-acceptance.json` contains only the exact public metadata/hash/status allowlist and passes the repository privacy audit.

A schema-valid fixture, hand-authored response, missing trace, historical v0.2 process receipt, or deterministic replay cannot satisfy this gate.

## Failure handling

- A focused failure blocks completion of its task.
- Changed upstream or accepted bytes block the cycle and require a new run; they are never overwritten.
- Reviewer `BLOCKED`, missing expected roles, same-agent review, failed reconciliation or privacy failure cannot yield terminal approval.
- A full-regression failure must be traced to the Phase 3 change and fixed before the plan completes.
- Live native acceptance failures and corrective evidence are retained privately; only a passing sanitized receipt is public.

## Overall

Nyquist compliance: PASS. All eleven implementation tasks have executable automated feedback, all four waves maintain continuous sampling, and the schema, live/native and public/privacy claims have dedicated terminal gates.
