---
phase: 01-versioned-operating-intake
plan: 02
subsystem: operating-intake
tags: [python, sqlite, strict-tables, csv, hashing, atomic-publication]

# Dependency graph
requires:
  - phase: 01-versioned-operating-intake/01-01
    provides: operating-v1 registry and deterministic source packs
provides:
  - Strict typed parser and whole-pack business validation for 22 sources
  - Separate 22-table SQLite STRICT operating schema
  - Immutable private cut builder with raw, typed, database, and relationship hashes
  - Safe validate/build CLI with atomic staging and publication
affects: [01-03, reconciled-decision-metrics, governed-weekly-decision-cycle]

# Tech tracking
tech-stack:
  added: []
  patterns: [parse-before-persist, strict SQLite defense in depth, content-addressed cuts, atomic directory publication]

key-files:
  created:
    - alma/operating_interchange.py
    - alma/operating_workspace.py
    - models/operating_v1.sql
    - scripts/operating_build.py
    - tests/test_operating_intake.py
  modified: []

key-decisions:
  - "Validate every relationship and business invariant before creating a staging directory."
  - "Bind cut identity to metadata and exact source bytes while recording typed rows, SQLite, and relationship digests separately."
  - "Publish original source bytes, metadata, database, and manifest together through one atomic directory rename."

patterns-established:
  - "Safe diagnostics: validation failures expose only stable code and location, never private cell values."
  - "Relationship evidence: manifests bind row/key counts, FK results, economic identities, supersession edges, active leaves, origin bindings, and cohort links."
  - "Private immutability: accepted cut IDs are never overwritten and separate cuts coexist under one private root."

requirements-completed: [DATA-02, DATA-03, DATA-04]

# Metrics
duration: 24min
completed: 2026-09-22
---

# Phase 1 Plan 02: Strict Operating Intake Summary

**Fail-closed 22-source parser and immutable SQLite cut builder with active-cash, cohort, stock, coverage, and provenance controls**

## Performance

- **Duration:** 24 min
- **Started:** 2026-09-23T03:20:51Z
- **Completed:** 2026-09-23T03:44:42Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Parses the exact operating-v1 pack with UTF-8-SIG support, bounded files/rows, typed integers/dates/timestamps, explicit nulls, exact keys, and safe validation diagnostics.
- Rejects malformed headers/rows, PII-like values, duplicates, broken foreign identities, invalid receipt/stock/reservation/cost/budget/cohort relationships, and orphaned, cyclic, forked, downgraded, or cross-origin cash supersession.
- Builds exactly 22 source-only SQLite `STRICT` tables with PK, UNIQUE, FK, enum, range, and reconciliation checks; no v0.2 order/customer tables or analytical marts are created.
- Publishes content-addressed private cuts with original source bytes, `operating.sqlite3`, and a manifest binding source hashes, metadata hash, normalized-row digest, database hash, row/key counts, coverage, cash evidence, cohort status, and relationship digest.
- Provides `validate` and `build` CLI commands and proves failed validation/publication leaves no trusted cut or staging residue.

## Task Commits

Each task was committed atomically with its TDD gates:

1. **Task 1 RED: Parse and reject invalid whole packs before persistence** - `28fc176` (test)
2. **Task 1 GREEN: Parse and reject invalid whole packs before persistence** - `ecc3156` (feat)
3. **Task 2 RED: Build strict private SQLite cut and provenance manifest** - `267788b` (test)
4. **Task 2 GREEN: Build strict private SQLite cut and provenance manifest** - `1dae544` (feat)

## Files Created/Modified

- `alma/operating_interchange.py` - Strict parser, safe coercion, coverage rules, keys, and whole-pack relationship/business checks.
- `models/operating_v1.sql` - Separate 22-table aggregate source schema using SQLite `STRICT` tables.
- `alma/operating_workspace.py` - Stable cut identity, deterministic relationship summary, SQLite builder, manifest, staging, and atomic publication.
- `scripts/operating_build.py` - Safe JSON receipt CLI for validation and private builds.
- `tests/test_operating_intake.py` - Positive, partial/unknown, malformed, PII, duplicate, FK, cash, cohort, double-count, immutability, and cleanup controls.

## Decisions Made

- Dates and offset timestamps become Python `date`/`datetime` values during validation, then canonical ISO text at the SQLite and typed-digest boundaries.
- Raw CSV hashes remain distinct from the canonical typed-row digest, so line-ending or byte changes affect cut identity without falsely changing normalized business content.
- The relationship digest includes the full cash supersession graph and active leaves, not only row counts and amounts.
- `UNIQUE` nullable predecessor/cohort columns rely on SQLite's standard multiple-NULL behavior while enforcing non-null uniqueness.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Required every accepted receipt and sale source fact to have exactly one stock posting**
- **Found during:** Task 2 GREEN
- **Issue:** The initial validator prevented duplicate stock postings but could accept an accepted receipt or delivered aggregate with no canonical movement.
- **Fix:** Added source-to-ledger completeness checks alongside duplicate-post rejection.
- **Files modified:** `alma/operating_interchange.py`, `tests/test_operating_intake.py`
- **Verification:** Removing the synthetic receipt movement fails with `stock.missing_post`; the linked fixture passes.
- **Committed in:** `1dae544`

**2. [Rule 1 - Bug] Allowed multiple immutable cut IDs under one private root**
- **Found during:** Task 2 GREEN
- **Issue:** The first publication implementation created `operating-cuts/` as if only one cut could ever exist, so a second distinct cut raised `FileExistsError`.
- **Fix:** Reuse the verified cuts directory, continue refusing an existing cut ID, reject a symlinked cuts root, and remove only directories created by a failed attempt.
- **Files modified:** `alma/operating_workspace.py`, `tests/test_operating_intake.py`
- **Verification:** Two distinct cuts coexist; rebuilding an identical cut still fails without changing bytes.
- **Committed in:** `1dae544`

---

**Total deviations:** 2 auto-fixed (1 missing critical control, 1 bug)
**Impact on plan:** The fixes complete the canonical stock and immutable multi-cut behavior without expanding architecture or dependencies.

## Issues Encountered

- Concurrent planning edits in Phases 4 and 5 appeared during execution. They were preserved and excluded from every 01-02 commit.

## Authentication Gates

None.

## Known Stubs

None.

## Verification Evidence

- `.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_operating_intake.py' -v` — 15 tests passed in 5.431 seconds.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_operating_contracts.py' -v` — 13 upstream contract tests passed in 1.504 seconds.
- `.venv\Scripts\python.exe -m compileall -q alma\operating_interchange.py alma\operating_workspace.py scripts\operating_build.py` — passed.
- Focused tests inspect `PRAGMA table_list`, require all 22 source tables to be `STRICT`, and require `PRAGMA foreign_key_check` to return no rows.
- The phase-wide v0.2/v0.3 regression suite remains assigned to plan 01-03 by `01-VALIDATION.md`.

## User Setup Required

None - no external service configuration or dependency installation is required.

## Next Phase Readiness

- Plan 01-03 can verify, export, and restore cuts using exact source, typed, SQLite, row/key, relationship, active-leaf, and cut identity evidence from `workspace.json`.
- Shared `STATE.md`, `ROADMAP.md`, and `REQUIREMENTS.md` remain for the orchestrator because this executor's ownership is limited to 01-02 files and this summary.

## Self-Check: PASSED

- All parser, workspace, SQL, CLI, test, and summary paths exist.
- All four RED/GREEN task commits are present in Git history.
- The schema declares exactly 22 tables; focused tests prove they are `STRICT` and that foreign-key checks return no violations.

---
*Phase: 01-versioned-operating-intake*
*Completed: 2026-09-22*
