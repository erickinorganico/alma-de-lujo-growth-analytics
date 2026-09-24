---
phase: 04-offline-client-and-analyst-kit
plan: 01
subsystem: offline-workbook-intake
tags: [xlsxwriter, openpyxl, csv, operating-v1, privacy, parity]

# Dependency graph
requires:
  - phase: 01-versioned-operating-intake
    provides: Canonical 22-relation source registry and whole-pack validator
  - phase: 02-reconciled-decision-metrics
    provides: Metric registry and versioned management-policy contract
provides:
  - Registry-driven blank and synthetic operating workbooks and matching source packs
  - Fail-closed XLSX-to-canonical-pack adapter with atomic private publication
  - Independent 22-relation workbook-to-pack parity receipt
  - Separate REVIEW policy template and validated synthetic policy example
affects: [04-02, 04-03, 05-02, 05-03]

# Tech tracking
tech-stack:
  added: []
  patterns: [registry-driven spreadsheet projection, atomic private adapter, independent parity oracle]

key-files:
  created:
    - scripts/build_operating_workbooks.py
    - alma/operating_workbook.py
    - client/v1/policies/operating-metrics-review-template-v1.json
    - client/v1/policies/operating-metrics-synthetic-v1.json
    - tests/test_operating_workbooks.py
    - evidence/v1.0/workbooks/workbook-pack-parity.json
  modified: []

key-decisions:
  - "The workbook is an editing surface; the validated canonical CSV pack remains the intake authority."
  - "All supporting sheets remain visible, and policy artifacts stay separate from the 22 source relations."
  - "Workbook exports publish atomically beneath an explicit private root and never overwrite an accepted cut."

patterns-established:
  - "Registry projection: derive sheet order, headers, types, requiredness, units and provenance from the final Phase 1 registry."
  - "Independent oracle: compare workbook cells, emitted CSV bytes and manifest without reusing adapter normalization helpers."

requirements-completed: [CLIENT-01]

# Metrics
duration: 34min
completed: 2026-09-23
---

# Phase 4 Plan 1: Contract-Complete Operating Workbooks Summary

**Registry-driven blank and synthetic XLSX workbooks now export through a fail-closed adapter into Phase 1-valid canonical packs, with independent parity evidence for all 22 relations.**

## Performance

- **Duration:** 34 min
- **Started:** 2026-09-23T21:01:45Z
- **Completed:** 2026-09-23T21:35:17Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Generated accessible blank and visibly synthetic workbooks from the authoritative source registry, including all 22 relations exactly once, client guidance, a completeness matrix, input validation, print metadata and matching canonical source packs.
- Added separately versioned `REVIEW` and `SYNTHETIC_EXAMPLE` policy files that pass the Phase 2 policy validator without claiming owner approval or entering the source-relation count.
- Implemented a read-only, fail-closed XLSX adapter that rejects structural, privacy, archive and formula hazards before atomically publishing a Phase 1-valid private pack.
- Produced a safe receipt that independently proves workbook-to-pack-to-manifest row, null/zero, integer-cent, unit and hash parity across all 22 relations.

## Task Commits

Each TDD task was committed at its RED and GREEN gates:

1. **Task 1 RED: Define the operating-workbook generation contract** - `6d0cf88` (test)
2. **Task 1 GREEN: Generate registry-complete workbooks and policy materials** - `8e765ec` (feat)
3. **Task 2 RED: Define workbook import and adversarial boundaries** - `653be77` (test)
4. **Task 2 GREEN: Validate and export workbooks through the canonical intake** - `144565b` (feat)

## Files Created/Modified

- `scripts/build_operating_workbooks.py` - Builds deterministic blank/synthetic XLSX files, matching packs and a hash manifest from the source registry.
- `alma/operating_workbook.py` - Inspects workbook archives, validates all workbook surfaces, converts declared cell types and atomically exports canonical packs.
- `client/v1/policies/operating-metrics-review-template-v1.json` - Unapproved management-policy template with explicit `REVIEW` status.
- `client/v1/policies/operating-metrics-synthetic-v1.json` - Validated synthetic management-policy example with no real-cut authority.
- `tests/test_operating_workbooks.py` - Covers generation, all relation omissions, exact round trips, parity and adversarial workbook boundaries.
- `evidence/v1.0/workbooks/workbook-pack-parity.json` - Sanitized synthetic receipt binding workbook, pack and manifest hashes to 22 per-relation PASS dispositions.

## Decisions Made

- Kept canonical headers unchanged and generated workbook shape directly from Phase 1 contracts so spreadsheet maintenance cannot create a second schema authority.
- Kept workbook guidance and completeness surfaces visible; hidden rows, columns or sheets are rejected at import.
- Preserved blanks as null and explicit zero as measured zero, using `Decimal` at spreadsheet money boundaries and integer MXN cents in canonical CSV output.
- Used independent receipt logic that reads workbook cells, CSV bytes and manifest hashes directly, preventing shared adapter logic from masking parity defects.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Normalized numeric enum labels before workbook rendering**
- **Found during:** Task 1 (Generate every v1 input relation as an accessible blank and synthetic workbook)
- **Issue:** One registry enum contains integer values, and direct string joining raised a type error while building the workbook dictionary.
- **Fix:** Rendered registry enum values through explicit string conversion while preserving their canonical typed values in generated rows.
- **Files modified:** `scripts/build_operating_workbooks.py`
- **Verification:** `OperatingWorkbookGenerationTests` passed 4/4 and the generated example pack passed the upstream whole-pack validator.
- **Committed in:** `8e765ec`

---

**Total deviations:** 1 auto-fixed bug.
**Impact on plan:** The fix was required to project the authoritative registry correctly; it added no scope or dependency.

## Issues Encountered

- OpenPyXL normalizes repeated print-title rows to `$1:$6` and can omit `fitToWidth=1` because it is the OOXML default. Tests assert the effective print contract instead of requiring serializer-specific XML spelling.

## Verification

- `OperatingWorkbookGenerationTests`: 4/4 passed.
- `WorkbookImportTests`: 5/5 passed.
- Full suite: 233/233 passed in 452.551 seconds.
- Release audit: PASS across 529 text files with zero findings.
- Python compilation, privacy scan and `git diff --check`: PASS.
- Synthetic workbook hash is deterministic across independent builds: `c7e768925c9fc89d3ed3dfa5fbb1efed861a3cad01f404ba0a219d4eab8e81d4`.
- Receipt binds pack hash `c20567e3cfe9595fd44b1ee63ffddae841c529cd92474a1f8094b3aab7989595` and manifest hash `9b2e998d8106afdf8fb047fe3fd71abf6c2dca4cca27ab5507edbfe9538397d5` with 22/22 relation dispositions at PASS.

## Known Stubs

None.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 04-02 and 04-03 can consume the generated workbook, private pack and safe receipt contracts.
- Phase 5 remains responsible for fresh desktop Excel recalculation, formula-cache and page-render evidence for the final delivered bytes; canonical CSV packs provide the reader-neutral fallback.
- No blockers remain for CLIENT-01 or D-01.

## Self-Check: PASSED

- All six planned artifacts exist.
- RED and GREEN commits for both TDD tasks are present in repository history.
- Focused tests, the full suite, release audit, privacy scan, compilation and diff checks passed.

---
*Phase: 04-offline-client-and-analyst-kit*
*Completed: 2026-09-23*
