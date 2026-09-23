---
phase: 03-governed-weekly-decision-cycle
verified: 2026-09-23T19:40:44Z
status: gaps_found
score: 9/10 must-haves verified
overrides_applied: 0
gaps:
  - truth: "The published operating-cycle-v1 schema validates the terminal packet and carried-decision current-cut documents produced by Phase 3."
    status: failed
    reason: "The runtime behavior is substantive and green, but the versioned JSON contract is out of sync with both persisted document shapes. A contract-driven consumer will reject valid Phase 3 output."
    artifacts:
      - path: "contracts/weekly-cycle-v1.schema.json"
        issue: "The packet definition requires evidence_hashes, which the actual packet does not emit, and additionalProperties:false rejects eight fields the packet does emit. The current_cut definition also rejects decision_register and carried_decisions added for FLOW-05."
      - path: "tests/test_native_agents_v1.py"
        issue: "The schema-contract test checks only that named definitions exist; it never validates an emitted packet or a carried-decision current cut against those definitions."
    missing:
      - "Align $defs.packet with the exact terminal packet produced by build_terminal_packet, including its separated categories, provenance and authority fields."
      - "Extend $defs.current_cut for decision_register and carried_decisions with strict nested shapes."
      - "Add contract-conformance tests for a real emitted terminal packet and a second-cut current-cut document with carried decisions."
---

# Phase 3: Governed Weekly Decision Cycle Verification Report

**Phase Goal:** A current private cut can produce evidence-bound native analysis, independent review, an owner-ready packet, and decisions that carry into the next cut.
**Verified:** 2026-09-23T19:40:44Z
**Status:** gaps_found
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | A verified v1 source pack reaches a current-cut report and six immutable role requests bound to exact Phase 1/2 evidence. | VERIFIED | `start_cycle_from_source_pack` calls the real workspace and mart builders/verifiers in `alma/weekly_cycle.py:371-399`; `tests.test_weekly_cycle` passed inside the 55-test focused gate. |
| 2 | Current-cut and request publication fail closed on changed evidence, traversal, links, malformed pointers and unsupported/private output paths. | VERIFIED | Exact byte/hash revalidation is performed in `alma/weekly_cycle.py:459-609`; the tamper, path and RFC 6901 tests in `tests/test_weekly_cycle.py:61-232` passed. |
| 3 | Only role-correct native responses with exact typed references, registered-query traces and parent-recorded dispatch hashes enter the cycle. | VERIFIED | `validate_response`, `validate_query_trace` and `validate_dispatch` are wired through `_accepted_artifact`, `record_dispatch` and `submit_response`; all five native-v1 contract tests passed. |
| 4 | Analysts preserve frozen evidence and a reviewer request is created only after all configured analyst responses validate. | VERIFIED | `alma/weekly_cycle.py:753-808` advances the hash-chained state machine; `test_any_order_analysts_reviewer_and_advisory_packet` and change/tamper controls passed. |
| 5 | A distinct Astra task independently reviews all accepted response, trace and dispatch hashes; same identity or stale/changed evidence fails closed. | VERIFIED | Private verified run has six distinct analyst identities and reviewer `/root/native_evidence_review`; the reviewer request hash is `8e2e75...d51b32`; identity/tamper tests passed. |
| 6 | The terminal packet separates facts, unknowns, hypotheses, recommendations and challenges, and every recommendation carries metric, guardrail, population, window and closure rule with execution prohibited. | VERIFIED | Private packet SHA-256 `b4c9ba...e2c9c3` contains all five sections and eight recommendations; an independent structural probe found every nested recommendation complete with `approval_required: true` and `execution: PROHIBITED`. |
| 7 | A real synthetic acceptance receipt proves the bounded native run without publishing prose, private paths or query contents. | VERIFIED | `scripts/run_weekly_cycle.py verify-acceptance` returned PASS for cut `eda52c...98f2`, run `8e88f170a3057b71f3ea5185`; receipt SHA-256 `b7304c...fa1fc`; release privacy audit passed over 518 files. |
| 8 | Reviewed owner decisions are append-only, hash chained and safe to project/import through proposal-only CSV. | VERIFIED | `alma/decision_register.py` revalidates owner-ready origins and immutable evidence; contract/CSV/tamper tests passed. |
| 9 | Open decisions retain identity across the next cut, stale and extension states are deterministic, and closure requires exact later-cut evidence or explicit local attestation. | VERIFIED | Four two-cut tests passed for carry, stale, extension, machine closure, forgery rejection and human attestation; carried rows are bound into reports and requests at `alma/weekly_cycle.py:308-315`. |
| 10 | The published operating-cycle-v1 schema validates the terminal packet and carried-decision current-cut documents produced by Phase 3. | FAILED | `$defs.packet` at `contracts/weekly-cycle-v1.schema.json:54-58` requires absent `evidence_hashes` and rejects eight emitted fields. `$defs.current_cut` uses `additionalProperties:false` at line 28 but has no `decision_register` or `carried_decisions`, which runtime adds at `alma/weekly_cycle.py:312-314`. |

**Score:** 9/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `alma/weekly_cycle.py` | Current-cut adapter, immutable tasks, native state machine, public receipt and carry binding | VERIFIED | Substantive, imported by CLI/tests, and exercised against real Phase 1/2 artifacts plus the retained private acceptance run. |
| `alma/native_agents_v1.py` | Strict request/response/trace/dispatch/packet validation | VERIFIED | Substantive and wired into every acceptance transition. |
| `alma/decision_register.py` | Append-only decision, carry, stale, extension and closure engine | VERIFIED | Substantive and wired into `start_cycle`, the management CLI and two-cut tests. |
| `scripts/run_weekly_cycle.py` | Start/query/record/submit/resume/status/packet/acceptance CLI | VERIFIED | CLI paths are exercised by integration tests and the retained acceptance receipt. |
| `scripts/manage_decisions.py` | Private owner-decision lifecycle CLI | VERIFIED | CLI negative and positive controls passed. |
| `agents/native-cycle-v1.roles.json` | Seven-role routing and authority contract | VERIFIED | Six analysts plus Astra; Terra/Luna/Sol/Astra routing matches emitted requests. |
| `agents/RUN-NATIVE-CYCLE-v1.md` | Exact native operating procedure | VERIFIED | References v1 CLI and contract; no historical process CLI substitution. |
| `contracts/decision-register-v1.schema.json` | Event, anchor, closure and CSV shapes | VERIFIED | Substantive definitions align with event fields enforced in code. |
| `contracts/weekly-cycle-v1.schema.json` | Current cut, task, native exchange and terminal packet shapes | FAILED | Request/response/trace/receipt portions are substantive; packet and carried-current-cut definitions are inconsistent with actual persisted bytes. |
| `evidence/v1/native-cycle-acceptance.json` | Sanitized actual synthetic-cycle receipt | VERIFIED | Exact metadata allowlist reconstructs from ignored private state and passes privacy checks. |
| `tests/test_weekly_cycle.py` | Current-cut, state-machine, tamper and privacy integration controls | VERIFIED | Included in 55 focused and 217 full green tests. |
| `tests/test_native_agents_v1.py` | Native contract negative controls | WARNING | Runtime controls are strong, but the named schema-contract test checks definition presence rather than output conformance. |
| `tests/test_decision_register.py` | Two-cut decision continuity and adversarial controls | VERIFIED | Eight tests passed, including CLI and two-cut scenarios. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `scripts/run_weekly_cycle.py` | Phase 1 workspace and Phase 2 mart APIs | source-pack start route | WIRED | Calls `start_cycle_from_source_pack`; that function uses completed upstream builders and verifiers before task publication. |
| `alma/weekly_cycle.py` | frozen manifest/marts/current-cut | exact bytes and SHA-256 | WIRED | Every status and transition rebuilds and compares upstream/current-cut artifacts. |
| analyst request | response + query trace + dispatch receipt | strict validation and canonical digests | WIRED | Actual private run has all six triads and matching public digests. |
| six accepted analyses | Astra reviewer request | immutable accepted hash map | WIRED | Reviewer request contains all response, trace and dispatch hashes and is emitted only after analyst completion. |
| Astra review | terminal packet | deterministic projection and review verdict | WIRED | Terminal packet revalidates from private accepted artifacts and reaches `READY_FOR_OWNER`. |
| private cycle | public acceptance receipt | metadata-only projection plus private reconstruction | WIRED | Exact allowlist comparison passes; prose/path injection negative test passes. |
| terminal packet | decision register | revalidated recommendation and packet/source hashes | WIRED | `register_decision` accepts only intact `READY_FOR_OWNER` origin. |
| prior register anchor | next current-cut/tasks | historical prefix projection | WIRED | Two-cut test proves stable identity and `STALE` carry into analyst evidence. |
| later-cut pointer | closure transition | current-cut hash plus typed predicate | WIRED | Exact closure passes; forged hash/value and same-cut evidence fail. |
| runtime documents | `weekly-cycle-v1.schema.json` | published JSON contract | NOT_WIRED | Runtime validators rebuild Python structures but never establish conformance to the published packet/current-cut schema; those definitions contradict actual output. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `current-cut.json` | report, coverage, reconciliations, metric rows | verified Phase 1 workspace + Phase 2 mart bundle | Yes, deterministic synthetic acceptance data | FLOWING |
| role requests | role evidence subset + registered query contract | frozen current-cut | Yes, six hash-bound requests | FLOWING |
| reviewer request | accepted responses/traces/dispatches | six validated analyst transitions | Yes, all accepted digests bound | FLOWING |
| `decision-packet.json` | separated analysis and review sections | validated analysts + distinct reviewer | Yes, eight recommendations and explicit limits | FLOWING |
| carried decisions | register projection at supplied anchor | verified prior ledger + next cutoff | Yes, tested with distinct cuts | FLOWING |
| `native-cycle-acceptance.json` | hashes, model/task IDs and terminal state | retained private cycle | Yes, exact private recheck | FLOWING |
| published JSON schema | packet/current-cut definitions | static contract file | No for Phase 3 terminal/carry extensions | HOLLOW |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Public receipt matches private run | `.venv\\Scripts\\python.exe scripts\\run_weekly_cycle.py verify-acceptance --receipt evidence\\v1\\native-cycle-acceptance.json` | PASS; exact cut/run/packet/receipt hashes returned | PASS |
| Native/privacy/decision critical controls | unittest native-v1 + privacy + decision-register | 14 tests in 204.098s | PASS |
| Phase 3 plus historical controls | unittest weekly/native/decision/lifecycle/security/process | 55 tests in 303.700s | PASS |
| Full repository regression | `.venv\\Scripts\\python.exe -m unittest discover -s tests -q` | 217 tests in 376.673s | PASS |
| Publishable-scope privacy | `.venv\\Scripts\\python.exe scripts\\audit_release.py` | 518 files; zero findings | PASS |
| Python syntax | `python -m py_compile` over five Phase 3 modules/scripts | exit 0 | PASS |
| Actual terminal packet against published packet definition | read-only key/required/additional-property conformance probe | missing `evidence_hashes`; eight disallowed emitted fields | FAIL |
| Carried-decision fields against published current-cut definition | read-only schema property probe | both fields absent while `additionalProperties:false` | FAIL |

### Probe Execution

No phase-declared or conventional `probe-*.sh` files apply. The executable acceptance receipt, focused tests and schema-conformance probes above provide the runnable evidence.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| FLOW-01 | 03-01 | Private source pack produces current-cut and hash-bound task bundle | SATISFIED | Real upstream builders/verifiers, six requests, tamper/path tests. Direct workbook preparation remains explicitly assigned to Phase 4. |
| FLOW-02 | 03-02 | Native analysts cite exact current-cut evidence and cannot mutate/execute | SATISFIED | Strict typed pointers, registered queries, write scope and `PROHIBITED` authority pass. |
| FLOW-03 | 03-02 | Distinct native reviewer; stale/change/same identity fail closed | SATISFIED | Actual distinct Astra receipt plus adversarial state-machine tests. |
| FLOW-04 | 03-02 | Terminal packet separates categories and complete recommendations | PARTIAL | Runtime packet fully satisfies the behavior, but the published `$defs.packet` rejects it. |
| FLOW-05 | 03-03 | Validated decision register with carry/stale/closure | PARTIAL | Runtime and two-cut tests satisfy behavior, but `$defs.current_cut` rejects the decision fields used for carry. |

No Phase 3 requirements are orphaned from plans. Later Phase 4/5 goals do not specifically schedule correction of this Phase 3 contract mismatch, so the gap is not deferred.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `contracts/weekly-cycle-v1.schema.json` | 54-58 | Stale packet definition | BLOCKER | Contract-driven consumers reject the actual owner-ready packet. |
| `contracts/weekly-cycle-v1.schema.json` | 24-28 | Closed current-cut definition lacks carry fields | BLOCKER | Contract-driven consumers reject the exact next-cut document required by FLOW-05. |
| `tests/test_native_agents_v1.py` | 180-184 | Existence-only schema assertion | WARNING | Test passes while the emitted packet contradicts the schema. |

No unreferenced `TBD`, `FIXME` or `XXX` markers were found in Phase 3 implementation artifacts. Empty collections observed in code are bounded accumulators or valid initial state, not user-visible stubs.

### Human Verification Required

None for this phase. The native receipt accurately limits its claim to parent-runtime attestation rather than provider cryptographic proof, and all phase behaviors are locally inspectable. Real customer correctness and adoption remain the explicit external gate EXT-01, outside Phase 3.

### Gaps Summary

The governed workflow itself is implemented and independently green: evidence is current-cut-bound; six native analyst receipts and a distinct Astra review revalidate; terminal recommendations are complete; decisions are append-only and survive a second cut with stale, extension and closure semantics; privacy and historical regression gates pass.

The phase cannot pass because its published versioned contract does not describe the documents it produces. This is one root gap with two manifestations: the terminal packet shape is stale, and the current-cut shape was not extended for carried decisions. The existing schema test only proves that definition names exist, which allowed both contradictions through. No later roadmap phase explicitly owns this correction.

---

_Verified: 2026-09-23T19:40:44Z_
_Verifier: Codex (gsd-verifier)_
