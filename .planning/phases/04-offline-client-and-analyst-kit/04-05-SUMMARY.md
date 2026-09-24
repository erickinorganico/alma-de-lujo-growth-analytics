---
phase: 04-offline-client-and-analyst-kit
plan: 05
subsystem: offline-client-portal
tags: [static-html, css, edge-cdp, visual-evidence, public-kit]
requires:
  - phase: 04-04
    provides: verified workbook-to-pack receipt and public packaging boundary
provides:
  - truthful executive offline portal with canonical 22-source domain coverage
  - inspected browser and print receipt tied to final HTML/CSS and image hashes
  - audited public client ZIP bound to the new receipt
affects: [client-kit, phase-04-verification, phase-05-release]
tech-stack:
  added: []
  patterns: [local-only static projection, SVG-and-table count parity, CSS page margin provenance, exact visual artifact inventory]
key-files:
  created: [evidence/v1.0/portal/public-small.png, evidence/v1.0/portal/synthetic-current-small.png]
  modified: [scripts/build_offline_portal_v1.py, client/portal-v1.css, tests/test_offline_portal_v1.py, tests/test_weekly_kit.py, evidence/v1.0/portal/portal-visual-inspection.json]
key-decisions:
  - "Unknown or unverified exception and decision counts remain nonnumeric; verified empty current sets may show zero."
  - "The historical synthetic inventory retains its own 30-source denominator; current v1 coverage partitions exactly 22 sources into five domains."
  - "Print provenance uses an Edge-supported page margin box so it repeats without obscuring rows."
patterns-established:
  - "A PASS receipt lists and hashes every screenshot, PDF and printed page from the exact rendered HTML/CSS."
requirements-completed: [CLIENT-02, CLIENT-04]
duration: 54min
completed: 2026-09-23
---

# Phase 4 Plan 05: Executive Offline Portal Summary

**The offline portal now puts the cut state, source coverage, exceptions and next action on the first screen while preserving verified evidence and strict public/private boundaries.**

## Performance

- **Duration:** approximately 54 minutes
- **Started:** 2026-09-24T00:32:56Z
- **Completed:** 2026-09-24T01:26:05Z
- **Tasks:** 3/3
- **Files changed:** portal builder, CSS, two test modules, and the bounded visual evidence set

## Accomplishments

- Replaced the editorial hero with a compact `Alma de Lujo / Corte semanal` header, 232px rail, truthful cards and five-domain SVG/table coverage. Each of the 22 current source IDs appears exactly once; the historical synthetic view keeps its separate 30-source inventory. Statuses, unknowns, waiting and verified zero stay distinct.
- Edge 153.0.4234.48 rendered both public historical and safe synthetic-current `file://` views at 1440×900, 960×900, 390×844, 320×800 and 720×450 CSS pixels (the reflow width equivalent to 200% of 1440). At 320, document `scrollWidth=clientWidth=305`; at 390, both are 375; at 720, both are 705. Eight anchors, Tab/Enter navigation, private table keyboard scroll, no-JavaScript content and the visible source legend were checked.
- Printed and visually inspected every page: 10 public and 51 safe synthetic-current pages. The repeated margin-box provenance, full hash appendix, table headers and rows are visible without overlap or clipping. The new receipt contains 73 hashed evidence members: 10 viewport captures, 2 PDFs and 61 page rasters. Receipt SHA-256: `ce2f548c069b94b3e7c5cd240191a4be16ce4ad39a692419db7537b841e28de9`.
- Rebuilt the public ZIP under ignored `.local/`: SHA-256 `482d01812f9003a4482170188dc7c0bf3fafacab2b47951eb8deb42723784874`. `audit_client_zip` passed for all 63 allowlisted members and 22 extracted local links; its manifest binds the receipt SHA-256. The ZIP has no private-current HTML/captures, filled cuts, native responses or credentials. The existing weekly package-stage tests preserve `WAITING_ANALYSTS` and the immutable cut semantics.

## Task Commits

1. **Task 1, RED contracts:** `203e431` — failing executive portal tests recorded before implementation.
2. **Task 2, GREEN implementation:** `47f8226` — executive layout, source map and truthful states; `8143521` — responsive and print refinements.
3. **Task 3, inspected evidence:** `607b214` — new exact visual receipt and page/capture inventory.

## Verification

- RED: `PortalExecutiveContractTests` failed four tests for the missing source map, domain coverage and executive layout before implementation.
- GREEN: nine executive/evidence tests PASS; six accessibility/client-kit tests PASS; two clean Git-archive package regressions PASS after the final task commits.
- `scripts/audit_release.py`: PASS, 550 publishable text files checked, zero findings. `git diff --check`: PASS.
- Full `unittest discover -s tests -v` was run during concurrent Phase 5 work and is not a clean 04-05 gate. One failure was the pre-existing workspace index hash for concurrently edited `AGENTS.md` (`abbf8f…` expected, `d06a96…` present). Two failures came from new, then-untracked 05-01 release-acceptance tests still in RED. The root orchestrator will rerun integrated verification after 05-01 stabilizes. No 04-05-owned test failed after the task commits.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed false numeric zeros from unverified cards.** Public historical exceptions/decisions now say `NO VERIFICADO`/`DESCONOCIDO`; current verified sets retain meaningful counts. Committed in `8143521`.

**2. [Rule 1 - Bug] Removed small-screen document overflow.** The synthetic 390/320 view had a 488px document width; responsive wrapping and narrow-width constraints now make `scrollWidth=clientWidth`. Committed in `8143521`.

**3. [Rule 1 - Bug] Kept printed provenance outside the content area.** A fixed print header overlapped coverage rows. The CSS page margin box repeats provenance on all pages without overlap; the final 61 pages were rerendered and reinspected. Committed in `8143521` and `607b214`.

**4. [Rule 3 - Blocking issue] Added the required empty `unexpected_files` receipt field.** The package verifier requires `[]` to accept the new PASS receipt; focused package tests passed after sealing the corrected receipt. Committed in `607b214`.

## Boundaries and Deferred Work

- Screenshots and PDFs contain only public historical or disposable synthetic-current fixtures. Current-cut source material remains under ignored `.local/`. The untracked public preview directory was removed after inspection.
- This is an analytical, local-only static view. No server, framework, remote asset or new dependency was added. It does not establish owner adoption, fiscal approval or observed business impact.
- Phase 5 deep PII content-mutation testing remains explicitly deferred; the release pattern audit and package allowlist are the Phase 4 checks.

## Known Stubs

None blocking the plan. The source search input's placeholder is user guidance, and the documented no-series/no-cut states are deliberate evidence states rather than mock data.

## Self-Check: PASSED

The modified portal/test files, 73 evidence members and this summary exist. All four task commit hashes resolve in Git; the receipt inventory and ZIP manifest hashes were independently checked. The summary is a separate documentation artifact from the task commits.
