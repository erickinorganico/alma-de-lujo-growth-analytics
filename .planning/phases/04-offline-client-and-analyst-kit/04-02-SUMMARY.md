---
phase: 04-offline-client-and-analyst-kit
plan: 02
subsystem: ui
tags: [offline-html, provenance, accessibility, print, sha256, edge]

requires:
  - phase: 04-offline-client-and-analyst-kit
    provides: Workbook-to-pack parity receipt and safe operating workbook intake
  - phase: 03-governed-weekly-decision-cycle
    provides: Verified cycle, native-role, packet and decision-register contracts
provides:
  - Static eight-section Spanish portal for the historical public demo and a selected verified private cut
  - Exact mart-to-portal-to-CSV-to-JSON parity oracle with explicit unknown and blocked states
  - Hash-bound Edge evidence for desktop, 390px and every printed page of both safe surfaces
affects: [04-offline-client-and-analyst-kit, client-delivery, release-verification]

tech-stack:
  added: []
  patterns: [verified-input view model, physically separated public/private output, bounded visual receipt]

key-files:
  created:
    - scripts/build_offline_portal_v1.py
    - client/portal-v1.css
    - tests/test_offline_portal_v1.py
    - evidence/v1.0/portal/portal-visual-inspection.json
  modified: []

key-decisions:
  - "Portal calculations stay deterministic: verified artifacts feed a stable view model, while HTML only renders and exports exact values."
  - "Public historical and selected private outputs use separate destinations, labels and verified hashes; private evidence never crosses into the public portal."
  - "A visual PASS requires exact final HTML/CSS hashes plus inspected desktop, 390px, PDF and every rasterized PDF page."

patterns-established:
  - "Verified view model: revalidate upstream source, report, packet and register anchors before exposing a current cut."
  - "Bounded browser evidence: receipt inventory rejects unexpected files and rehashes every screenshot, PDF and print page."

requirements-completed: [CLIENT-02]

duration: 49min
completed: 2026-09-23
---

# Phase 04 Plan 02: Offline Client Portal Summary

**A serverless Spanish evidence portal now preserves verified provenance and exact analytical states across HTML, CSV, JSON, desktop, 390px and fully inspected print output.**

## Performance

- **Duration:** 49 min
- **Started:** 2026-09-23T14:44:08-07:00
- **Completed:** 2026-09-23T15:33:00-07:00
- **Tasks:** 2
- **Files modified:** 70

## Accomplishments

- Built the eight required semantic sections from verified historical or selected-current evidence, including sources, metrics, native roles, decisions, exceptions and portable lineage.
- Preserved exact metric IDs, integer MXN cents, units, source hashes and `MEASURED`/`UNKNOWN`/`PARTIAL`/`REVIEW`/`BLOCKED` states across mart, portal model, CSV and JSON.
- Kept public historical and ignored private-current generation physically separate; hash mismatch, path escape and missing evidence fail closed.
- Captured final bytes in Microsoft Edge 153.0.4234.48 through `file://` at 1440px and 390px and as PDF, then inspected 11 public and 48 synthetic-current print pages.
- Bound 65 browser artifacts and the exact HTML, CSS, manifest, model, export and workbook-oracle hashes into `portal-visual-inspection.json`.

## Task Commits

Each TDD gate and completed task was committed atomically:

1. **Task 1 RED: verified portal evidence contracts** - `7661df8` (test)
2. **Task 1 GREEN: verified portal evidence collector** - `e5b0a65` (feat)
3. **Task 2 RED: accessibility and parity contracts** - `dcb7f5f` (test)
4. **Task 2 GREEN: accessible static portal and exports** - `92f7d78` (feat)
5. **Task 2 visual correction: narrow provenance wrapping** - `abdfbb1` (fix)
6. **Task 2 browser evidence: hash-bound inspected surfaces** - `f14dd07` (test)

## Files Created/Modified

- `scripts/build_offline_portal_v1.py` - Revalidates public/private evidence, creates the stable portal model and writes safe static HTML plus exact CSV/JSON exports.
- `client/portal-v1.css` - Local cream/forest/teal responsive, focus and print styles, including long provenance/hash wrapping at 390px.
- `tests/test_offline_portal_v1.py` - Provenance, tamper, two-cut continuity, hostile-text, link, workbook-oracle, export parity and visual-inventory gates.
- `evidence/v1.0/portal/portal-visual-inspection.json` - Canonical PASS receipt binding exact generated portal and 65 reviewed browser artifacts.
- `evidence/v1.0/portal/*.png` - Desktop, narrow and every rasterized print page reviewed for clipping and hidden critical content.
- `evidence/v1.0/portal/*.pdf` - Final public and safe synthetic-current print output produced from the same final HTML/CSS bytes.

## Decisions Made

- A missing selected private cut renders a labelled unselected view; it never falls back to demo values.
- Prepared native requests remain `ESPERANDO_RESPUESTA`, and advisory packets remain distinct from owner registration.
- Core content works without JavaScript. The optional source filter cannot define or hide evidence in the no-script document.
- Browser evidence records logical relative paths and hashes only; it does not expose temporary or private absolute paths.

## TDD Gate Compliance

- Task 1 RED `7661df8` preceded GREEN `e5b0a65`.
- Task 2 RED `dcb7f5f` preceded GREEN `92f7d78`.
- The responsive correction and final evidence gate were added after visual inspection without rewriting either TDD history.

## Verification

- `PortalEvidenceTests`: 4/4 PASS.
- `PortalAccessibilityTests`: 4/4 PASS, including the bounded 65-member receipt rehash.
- Full suite: 241/241 PASS in 503.395 s.
- `scripts/audit_release.py`: PASS, 534 text files checked, zero findings.
- Python compile, privacy scan and `git diff --check 5ee55bc..HEAD`: PASS.
- Visual review: public 1440px, public 390px, synthetic-current 1440px and synthetic-current 390px PASS; 11/11 public and 48/48 synthetic-current PDF pages inspected by the executor and independently by root.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Long current-cut provenance clipped at 390px**
- **Found during:** Task 2 browser inspection
- **Issue:** The initial narrow rendering allowed the long current-cut label, warning, hashes and navigation to extend beyond the viewport.
- **Fix:** Added bounded body width, navigation wrapping and overflow wrapping for headings, provenance, hashes and tabular values; recaptured every desktop, narrow and print artifact from the final CSS bytes.
- **Files modified:** `client/portal-v1.css`, `tests/test_offline_portal_v1.py`
- **Verification:** Both final 390px captures were inspected; accessibility tests and the full suite passed.
- **Committed in:** `abdfbb1`

---

**Total deviations:** 1 auto-fixed bug.
**Impact on plan:** The correction was required for the explicit narrow-layout success criterion and introduced no product scope beyond the plan.

## Issues Encountered

- Edge could not open the first generated portal from the system temporary location. The same generated bytes were staged under the ignored project-local `.local/` boundary and opened successfully through `file://`; no private or temporary path entered the receipt.
- The receipt helper initially lacked the repository root on `sys.path`. The ignored helper was corrected before the receipt existed; product files and captured bytes were unchanged.

## Known Stubs

None. The source-search `placeholder` attribute is instructional UI copy; it is not placeholder data or an unwired component.

## User Setup Required

None - the portal is local, uses existing Python and Edge runtimes, and requires no service or package installation.

## Next Phase Readiness

- CLIENT-02 and D-02 are covered by deterministic tests and reviewed browser evidence.
- The portal generator is ready for the final client-kit packaging step; actual private customer data remains confined to ignored `.local/` paths.
- No blockers remain.

## Self-Check: PASSED

- All four primary implementation/evidence paths and this summary exist.
- All six task/TDD commit objects resolve in Git.
- The final receipt rehash gate passed again after summary creation.

---
*Phase: 04-offline-client-and-analyst-kit*
*Completed: 2026-09-23*
