---
phase: 01-versioned-operating-intake
verified: 2026-09-22
status: passed
score: 5/5
requirements: [DATA-01, DATA-02, DATA-03, DATA-04, DATA-05]
---

# Phase 1 Verification

## Goal verdict

**PASSED.** The implemented operating-v1 path turns an exact 22-source pack into an immutable, content-addressed SQLite cut and can verify, export, restore, and reverify the same source, database, identity, and relationship evidence. All checks use blank or explicitly synthetic fixtures; observed client correctness remains an external gate.

## Requirement evidence

| Requirement | Evidence | Verdict |
| --- | --- | --- |
| DATA-01 | `alma/operating_contracts.py`, `scripts/operating_pack.py`, both checked-in v1 source packs, and 13 contract tests prove exact ordered schemas, keys, units, provenance, metadata, and byte-stable generation. | PASS |
| DATA-02 | `alma/operating_interchange.py`, `alma/operating_workspace.py`, `models/operating_v1.sql`, and intake tests prove fail-before-publish parsing and exactly 22 SQLite `STRICT` source tables. | PASS |
| DATA-03 | `workspace.json` generation binds cutoff, timezone, coverage, quality, source/typed/database/relationship digests, and stable cut identity without exposing row values. | PASS |
| DATA-04 | Whole-pack checks and archive reverification cover canonical SKU/event relationships, receipt and stock reconciliation, payment and budget links, cash supersession/active leaves, delivery cohorts, and double-count controls. | PASS |
| DATA-05 | `alma/operating_archive.py`, its CLI, and 12 archive tests prove deterministic export, exact restore, byte and relationship equality, tamper refusal, bounded ZIP handling, and immutable publication. | PASS |

## Plan and must-have evidence

| Plan | Must-have result | Evidence |
| --- | --- | --- |
| 01-01 | One executable contract and reproducible public packs | 22 registered sources; each blank/synthetic directory contains metadata plus 22 CSV files; all 46 generated files compare byte for byte. |
| 01-02 | Strict private intake and immutable workspace | 15 focused tests; exactly 22 source tables report `STRICT`; `PRAGMA foreign_key_check` is empty; invalid packs publish no cut. |
| 01-03 | Independent verification and exact archive round-trip | 12 focused tests cover positive, tamper, unsafe ZIP, cash, cohort, identity, and existing-destination controls. |

## Verification receipts

- Independent phase rerun: `.venv\Scripts\python.exe -m unittest tests.test_operating_contracts tests.test_operating_intake tests.test_operating_archive -v` — **40/40 passed** in 11.024 seconds.
- Final plan regression: `.venv\Scripts\python.exe -m unittest discover -s tests -v` — **150/150 passed** in 35.562 seconds, including v0.2/v0.3 behavior.
- Compilation and `git diff --check` passed; `.local/` cut and export paths remain ignored.

## Release boundary

No synthetic test establishes real client correctness, owner adoption, fiscal policy, opening-bank reconciliation, or the Pilates-socks winner hypothesis. Those remain EXT-01..03 and do not weaken the verified software goal for this phase.

## Gaps

None within Phase 1. Phase 2 may rely on the operating-v1 registry, immutable cut, and archive verification contract.
