---
phase: 01
slug: versioned-operating-intake
status: passed
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-22
---

# Phase 1 — Validation Strategy

Phase 1 is complete only when the 22-source operating contract, private immutable cut, economic-event replacement, and exact export/restore round-trip have automated evidence. Tests use blank or synthetic source packs and disposable private roots. No real customer data, filled private packs, or production service is involved.

## Test Infrastructure

| Property | Value |
| --- | --- |
| Framework | Python 3.11+ standard-library `unittest` with temporary directories and real SQLite |
| Config | Existing `tests/test_*.py` convention; no new dependency or config file |
| Contract command | `python -m unittest discover -s tests -p 'test_operating_contracts.py' -v` |
| Intake command | `python -m unittest discover -s tests -p 'test_operating_intake.py' -v` |
| Archive command | `python -m unittest discover -s tests -p 'test_operating_archive.py' -v` |
| Full regression command | `python -m unittest discover -s tests -v` |
| Runtime evidence | Record actual focused/full durations during execution; do not assert an unmeasured runtime |

The three new test modules are created in the red stage of their assigned tasks, before the related production code. Existing `unittest` infrastructure is sufficient; no package installation or preliminary scaffold wave is needed. A failing red test is expected during implementation, but each task exits only on a green automated command.

## Nyquist Sampling and Feedback Cadence

1. **Each task's red stage:** Add a behavior test and run its focused command; confirm it fails for the missing behavior.
2. **After each production edit and task completion:** Run that task's focused command. Do not continue to the next task on red or flaky results; fix the defect or document a concrete blocker.
3. **After Wave 1:** Run the contract command and compare both generated pack directories against a fresh deterministic generation byte for byte.
4. **After Wave 2:** Run contract and intake commands; inspect `PRAGMA foreign_key_check` and SQLite `STRICT` schema for every source relation.
5. **After Wave 3:** Run archive command, then the full regression command from 01-03 Task 2. This is the phase gate for existing v0.2/v0.3 behavior.
6. **Before phase verification:** Re-run only a check affected by subsequent changes; preserve valid unchanged receipts. The full regression result must remain green at the final Phase 1 code state.

Focused feedback should finish promptly; if a command exceeds a minute, keep it running and report progress rather than weakening the gate. Archive tests and the final full suite are mandatory regardless of duration. No watch mode, external data, or manual-only substitute is used.

## Per-Task Verification Map

| Task | Wave | Requirements | Test file and behavior | Automated gate | Status |
| --- | --- | --- | --- | --- | --- |
| 01-01 Task 1 | 1 | DATA-01, DATA-04 | `tests/test_operating_contracts.py`: literal 22 headers, grain/key/type/unit/FK/provenance, `cash_events.economic_event_id` required and `supersedes_event_id` nullable, metadata versions/coverage | `python -m unittest discover -s tests -p 'test_operating_contracts.py' -v` | Green — 13/13 focused |
| 01-01 Task 2 | 1 | DATA-01, DATA-04 | Same file: blank/synthetic generation, byte-stable 22 CSVs plus metadata, explicit synthetic mark, linked cash forecast→actual event, private-public path rejection | `python -m unittest discover -s tests -p 'test_operating_contracts.py' -v` | Green — 46 generated files byte-stable |
| 01-02 Task 1 | 2 | DATA-02, DATA-04 | `tests/test_operating_intake.py`: exact headers/typed rows; malformed, duplicate, conflict, PII, FK, stock/reservation, budget and cash self/cycle/fork/cross-origin negatives | `python -m unittest discover -s tests -p 'test_operating_intake.py' -v` | Green — 15/15 focused |
| 01-02 Task 2 | 2 | DATA-02, DATA-03, DATA-04 | Same file: immutable private SQLite, source/typed/DB/relationship digests, stable cut ID, 22 `STRICT` tables, active-leaf-only cash and balance reconciliation | `python -m unittest discover -s tests -p 'test_operating_intake.py' -v` | Green — 22/22 STRICT, no FK violations |
| 01-03 Task 1 | 3 | DATA-03, DATA-05 | `tests/test_operating_archive.py`: live verification, exact private archive, one-byte tamper, changed supersession edge or active leaf, no source-value disclosure | `python -m unittest discover -s tests -p 'test_operating_archive.py' -v` | Green — 12/12 focused |
| 01-03 Task 2 | 3 | DATA-02, DATA-03, DATA-04, DATA-05 | Same file plus existing suite: exact restore equality, unsafe ZIP/path/tamper/preexisting destination, unknown/reconciled evidence and old-version regressions | `python -m unittest discover -s tests -v` | Green — 150/150 full regression |

## Requirement and Negative-Control Coverage

| Requirement | Positive oracle | Failure/unknown oracle | Final gate |
| --- | --- | --- | --- |
| DATA-01 | Blank and synthetic packs regenerate exact 22 ordered schemas from one registry | Wrong version/header/order, duplicate header, undeclared null, private pack under `client/` fail | 01-01 focused + full suite |
| DATA-02 | Valid private or synthetic pack publishes one new cut only after all checks | Malformed, duplicate, conflicting, PII-like, path escape, broken FK, business inconsistency and existing cut leave no new published metrics/workspace | 01-02 focused + full suite |
| DATA-03 | Same inputs reproduce cut ID and raw/typed/DB/relationship digests with cutoff, timezone, coverage and quality | Changed source bytes, cutoff, timezone, coverage or supersession link change expected digest; MISSING/PARTIAL/ZERO/ESTIMATED/ERROR stay distinct | 01-02 + 01-03 focused + full suite |
| DATA-04 | 22 sources resolve canonical SKU/receipt/payment/obligation/budget/cohort IDs and one active cash economic event; 20 ordered/18 received/2 inspected/16 accepted reconciles | Duplicate stock/payment, invalid reservation, cash forecast plus actual counted twice, orphan/self/cyclic/forked/cross-origin supersession and unsupported RECONCILED label fail or remain unknown | 01-02 + 01-03 focused + full suite |
| DATA-05 | Export and restore preserve original CSV, SQLite, row/key/FK, supersession/active-leaf and identity hashes | Missing/extra/duplicate/traversal/symlink/oversized member, one-byte tamper and existing destination fail before publish | 01-03 focused + full suite |

## Trust and Compatibility Gates

- **Privacy:** Generated public packs are blank or explicitly synthetic. Tests scan bounded tokens/headers and assert safe issue codes without private cell values. `.local/` inputs, cuts and exports stay ignored; tests use disposable synthetic roots.
- **Immutability:** Build/export/restore reject overwrite. Failed validation or extraction leaves no accepted partial cut; verified source bytes never change.
- **Cash integrity:** `supersedes_event_id` is a same-identity self-FK with no self link, fork or cycle. Only the active leaf is eligible for layer sums; observed balance evidence must reconcile active `RECONCILED` events in integer cents. Relationship digest and archive verification cover edges, identities, active leaves and origin bindings.
- **Compatibility:** The full suite tests existing v0.2/v0.3 behavior. Do not rewrite prior evidence or generated release hashes to make Phase 1 pass.

## Wave 0 Requirements

Existing `unittest` and temporary-fixture patterns cover the phase; no separate Wave 0 setup is required. The new test files are owned by their respective plan tasks and created before implementing each behavior.

## Manual-Only Verifications

None for Phase 1. Observed private client correctness and owner adoption are external acceptance gates, outside synthetic Phase 1 verification.

## Validation Sign-Off

- [x] Every task has an automated verification command.
- [x] Each task has immediate focused feedback; no three-task gap exists.
- [x] No new test framework or Wave 0 dependency is needed.
- [x] No watch mode or manual-only acceptance substitute.
- [x] Focused tests green on implemented code.
- [x] Final full suite green with v0.2/v0.3 compatibility.

**Approval:** Passed on 2026-09-22. Evidence is recorded in `01-VERIFICATION.md` and the three plan summaries.
