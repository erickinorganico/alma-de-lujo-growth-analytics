---
phase: 01-versioned-operating-intake
plan: 03
subsystem: operating-intake
tags: [python, sqlite, zip, archive-security, tamper-detection, atomic-publication]

# Dependency graph
requires:
  - phase: 01-versioned-operating-intake/01-02
    provides: immutable 22-table cuts with source, SQLite, and relationship evidence
provides:
  - Independent live-cut verification against authoritative source rows and SQLite relationships
  - Deterministic private ZIP export containing exactly one complete accepted cut
  - Bounded fail-closed ZIP restore with exact byte and identity preservation
  - Local verify, export, and restore CLI routes with safe receipts
affects: [reconciled-decision-metrics, governed-weekly-decision-cycle, acceptance-and-v1-0-0-release]

# Tech tracking
tech-stack:
  added: []
  patterns: [source-authoritative verification, deterministic flat ZIP, preflight-before-extract, verify-before-atomic-publish]

key-files:
  created:
    - alma/operating_archive.py
    - scripts/operating_archive.py
    - tests/test_operating_archive.py
  modified: []

key-decisions:
  - "Treat the original validated CSV rows as authoritative and require SQLite table content to match them exactly, even if an altered manifest and database agree with each other."
  - "Accept only a flat, exact 25-member archive and reject unsafe names, types, sizes, compression ratios, duplicates, and encryption before writing extraction bytes."
  - "Verify extracted content in private staging and publish only into an absent private destination by one directory rename."

patterns-established:
  - "Live verification: source, metadata, normalized rows, cut identity, SQLite bytes/schema/content/integrity/FKs, row/key counts, and relationship digest must all agree."
  - "Archive safety: central-directory validation precedes bounded streaming extraction; no ZipFile.extract path handling is trusted."
  - "Portable identity: restore preserves every accepted byte, including the original SQLite file, instead of rebuilding it."

requirements-completed: [DATA-02, DATA-03, DATA-04, DATA-05]

# Metrics
duration: 17min
completed: 2026-09-22
---

# Phase 1 Plan 03: Verified Operating Archive Summary

**Source-authoritative cut verification and deterministic private ZIP round-trips with bounded extraction, exact byte preservation, and economic relationship revalidation**

## Performance

- **Duration:** 17 min
- **Started:** 2026-09-23T03:50:04Z
- **Completed:** 2026-09-23T04:06:51Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Verifies a live accepted cut from its exact 22 CSVs, metadata, manifest, and SQLite database without exposing source rows or private digests in the verification receipt.
- Recomputes source and metadata hashes, normalized-row digest, D-07 cut identity, SQLite hash, strict schema, exact source-to-database rows, integrity, foreign keys, row/key counts, full cash supersession graph, active leaves, origin bindings, cohort links, and relationship digest.
- Exports only verified cuts as byte-deterministic private ZIPs with exactly 25 flat members, fixed member order, fixed timestamps, fixed permissions, and no accepted-workspace mutation.
- Restores original bytes through bounded streaming extraction after rejecting duplicate, case-colliding, missing, unexpected, traversal, absolute, symlink, non-file, encrypted, unsupported-compression, oversized, and excessive-ratio members.
- Revalidates D-10 observed cash balance, D-11 economic supersession and active-leaf semantics, forecast/actual double-count protection, and aggregate delivery-cohort gates before atomic publication to an absent private destination.
- Provides documented `verify`, `export`, and `restore` CLI routes with stable safe error codes.

## Task Commits

Each task was committed atomically with its TDD gates:

1. **Task 1 RED: Verify accepted cuts and export an exact private archive** - `a901062` (test)
2. **Task 1 GREEN: Verify accepted cuts and export an exact private archive** - `d327fe0` (feat)
3. **Task 2 RED: Restore to a new private cut and prove fail-closed boundaries** - `54b9a05` (test)
4. **Task 2 GREEN: Restore to a new private cut and prove fail-closed boundaries** - `9a6cfdc` (feat)

## Files Created/Modified

- `alma/operating_archive.py` - Live verifier, deterministic exporter, ZIP preflight, bounded extractor, restore verifier, and atomic publisher.
- `scripts/operating_archive.py` - Safe local CLI for verify, export, and restore operations.
- `tests/test_operating_archive.py` - Round-trip, tamper, privacy, immutability, archive attack, cash, supersession, cohort, CLI, and compatibility controls.

## Decisions Made

- Manifest agreement alone is insufficient: the verifier compares every SQLite source-table value with the normalized original pack so a coordinated database/manifest edit still fails.
- ZIP paths are intentionally flat and must exactly equal the accepted cut filenames; this removes extraction-path interpretation from the restore trust boundary.
- Archive contents are copied as streams with explicit per-member and aggregate bounds, while source and database hashes are also computed incrementally.
- A successful restore retains the archive's original database bytes; equality covers its byte hash as well as its logical relationships.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Accepted regular Windows ZIP members without weakening special-file rejection**
- **Found during:** Task 2 GREEN
- **Issue:** ZIPs written through the Windows standard library can carry permission bits without POSIX file-type bits. The initial preflight treated those ordinary members as non-files and rejected every test archive.
- **Fix:** Interpret a zero file-type mask as a regular portable ZIP member while continuing to reject explicit symlink, directory, and other special-file modes.
- **Files modified:** `alma/operating_archive.py`
- **Verification:** All unsafe-member controls and the positive round-trip pass on the project Windows runtime.
- **Committed in:** `9a6cfdc`

**2. [Rule 2 - Missing Critical] Streamed archive and hash operations under explicit byte bounds**
- **Found during:** Task 2 GREEN hardening
- **Issue:** Initial export and hashing read bounded but potentially large database files into one in-memory byte string, weakening the denial-of-service boundary required for untrusted live cuts.
- **Fix:** Added chunked SHA-256 and ZIP writes, retaining per-file maximums and deterministic archive bytes without large whole-file allocations.
- **Files modified:** `alma/operating_archive.py`
- **Verification:** Deterministic exports remain byte-identical and oversized/high-ratio archives fail before extraction.
- **Committed in:** `9a6cfdc`

---

**Total deviations:** 2 auto-fixed (1 portability bug, 1 missing resource-bound control)
**Impact on plan:** Both fixes strengthen the specified cross-platform and denial-of-service boundaries without changing architecture or dependencies.

## Issues Encountered

- Concurrent Phase 5 planning edits remained present throughout execution. They were preserved and excluded from every 01-03 commit.

## Authentication Gates

None.

## Known Stubs

None.

## Verification Evidence

- `.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_operating_archive.py' -v` — 12 tests passed in 8.034 seconds.
- `.venv\Scripts\python.exe -m unittest discover -s tests -v` — 150 tests passed in 35.562 seconds, including historical v0.2/v0.3 and all Phase 1 tests.
- `.venv\Scripts\python.exe -m compileall -q alma\operating_archive.py scripts\operating_archive.py` — passed.
- `git diff --check` — passed.
- `git check-ignore -v .local/operating-exports/example.zip .local/operating-cuts/example/workspace.json` — both private paths are covered by `.gitignore`'s `.local/` rule.
- `git status --short` showed no historical evidence modifications; only the preexisting concurrent Phase 5 planning edits remained after 01-03 commits.

## TDD Gate Compliance

- Task 1 RED `a901062` precedes GREEN `d327fe0`.
- Task 2 RED `54b9a05` precedes GREEN `9a6cfdc`.

## User Setup Required

None - the implementation uses only the Python standard library and private local paths.

## Next Phase Readiness

- Phase 1 now provides deterministic source packs, strict immutable operating cuts, and independently verifiable private archive round-trips for Phase 2 metrics.
- DATA-05 is proven with exact source, metadata, normalized-row, SQLite, row/key, relationship, economic identity, supersession-edge, and active-leaf preservation.
- Shared `STATE.md`, `ROADMAP.md`, and `REQUIREMENTS.md` remain for the orchestrator because this executor's ownership is limited to 01-03 files and this summary.

## Self-Check: PASSED

- The archive module, CLI, focused tests, and summary all exist.
- All four Task 1/Task 2 RED/GREEN commits are present in Git history.
- Focused and full unittest gates passed on the committed implementation, and private archive paths remain Git-ignored.

---
*Phase: 01-versioned-operating-intake*
*Completed: 2026-09-22*
