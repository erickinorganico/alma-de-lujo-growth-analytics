---
phase: 04-offline-client-and-analyst-kit
plan: 03
subsystem: client-operations
tags: [weekly-cycle, powershell, deterministic-zip, offline-kit, privacy, tdd]

# Dependency graph
requires:
  - phase: 04-01
    provides: Canonical blank/synthetic workbook generation, workbook-to-pack adapter and parity receipt
  - phase: 04-02
    provides: Offline public portal and hash-bound visual inspection receipt
  - phase: 03-governed-weekly-decision-cycle
    provides: Native task, review, packet and decision-register contracts
provides:
  - One supported weekly creation and five-action continuation interface
  - Reproducible allowlisted public client ZIP with exhaustive audit
  - Spanish client journey and analyst weekly operating runbook
affects: [05-acceptance-and-release, weekly-operations, public-client-delivery]

# Tech tracking
tech-stack:
  added: []
  patterns: [immutable-derived-cut, action-specific-cli, deterministic-allowlisted-zip, receipt-bound-release]

key-files:
  created:
    - alma/weekly.py
    - scripts/package_client_v1.py
    - client/v1/EMPIEZA_AQUI.md
    - client/v1/GUIA_SEMANAL.html
    - docs/ANALYST-WEEKLY-v1.md
    - tests/test_weekly_kit.py
  modified:
    - run.ps1

key-decisions:
  - "Weekly runs accept only a private .local/client-runs root and derive the immutable cut child from verified inputs."
  - "Continuation exposes exactly record, submit, resume, packet and register, with action-specific evidence validation and no automatic owner decision."
  - "The distributable ZIP is rebuilt from an exact blank/synthetic allowlist and is bound to the accepted workbook and portal receipts without copying private evidence."

patterns-established:
  - "Restart proof: resume a copied private run from a clean git archive checkout and compare every earlier receipt byte."
  - "Public package proof: deterministic member order and metadata, manifest hash per member, offline link audit and embedded workbook/policy inspection."

requirements-completed: [CLIENT-03, CLIENT-04]

# Metrics
duration: 41min
completed: 2026-09-23
---

# Phase 04 Plan 03: Weekly Operation and Client Kit Summary

**Immutable weekly cut preparation and restart-safe continuation with a reproducible, audited 63-member offline client kit**

## Performance

- **Duration:** 41 min
- **Started:** 2026-09-23T15:41:18-07:00
- **Completed:** 2026-09-23T16:22:02-07:00
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Added the exact PowerShell/Python weekly command that adapts a workbook or consumes a canonical pack, validates policy and optional carry-forward anchors, derives an immutable cut, builds verified marts and leaves native work honestly at WAITING.
- Added restart-safe `weekly-resume` actions for recording and submitting real response evidence, resuming state, building the owner packet and registering only an explicit owner decision event.
- Built a byte-reproducible public ZIP from freshly generated blank/synthetic materials and the public portal, with exact allowlisting, member hashes, policy checks, local-link validation, workbook-surface checks and upstream receipt hashes.
- Delivered Spanish client and analyst instructions that separate the public demo journey from private analytical operation and enumerate the canonical 22-table source registry.

## Task Commits

Each task was committed atomically:

1. **Task 1: Run and resume the local weekly cut** — `fd1e09a` (RED), `d09ac2f` (GREEN), `5c3b12a` (clean-archive restart proof)
2. **Task 2: Build and audit the public client kit** — `d0ec5c4` (RED), `563cbc5` (GREEN)
3. **Task 3: Publish Spanish client and analyst instructions** — `e6aec29` (RED), `3c13ec5` (GREEN), `be02efd` (registry-alignment fix)

## Files Created/Modified

- `run.ps1` — Routes the supported `weekly` and `weekly-resume` commands while preserving Python exit status.
- `alma/weekly.py` — Creates immutable weekly cuts and validates each continuation action against Phase 3 contracts.
- `scripts/package_client_v1.py` — Generates and audits the deterministic public ZIP.
- `client/v1/EMPIEZA_AQUI.md` — Source-first Spanish client starting guide.
- `client/v1/GUIA_SEMANAL.html` — Browser-readable offline client workflow and state guide.
- `docs/ANALYST-WEEKLY-v1.md` — Exact analyst command, native receipt, review, packet and owner-decision runbook.
- `tests/test_weekly_kit.py` — Command, restart, package, privacy, link and guide contract coverage.

## Decisions Made

- A weekly output root must resolve to `.local/client-runs`; the system derives `<output-root>/<cut_id>/` and rejects an existing child instead of rewriting it.
- Prior decisions can cross cuts only when both register and anchor are supplied and verify together.
- Public packaging consumes the accepted workbook parity and portal visual receipt hashes as verification inputs, while private cuts, browser captures, task requests and native responses remain outside the ZIP.
- The public ZIP contains guidance and synthetic/blank evidence only; it does not contain the analyst runtime and cannot run a private cut.

## TDD Gate Compliance

- Task 1 RED `fd1e09a` preceded GREEN `d09ac2f`; `5c3b12a` strengthened the required clean-archive restart proof.
- Task 2 RED `d0ec5c4` preceded GREEN `563cbc5`.
- Task 3 RED `e6aec29` preceded GREEN `3c13ec5`; `be02efd` added a registry-bound regression after factual review.

## Verification

- `WeeklyCommandTests`: 5/5 PASS, including a second process from a clean `git archive` checkout and byte-identical prior receipts.
- `ClientKitTests`: 2/2 PASS with reproducible ZIP and private/native/runtime/credential/traversal/policy negative controls.
- `GuideContractTests`: 3/3 PASS using the real packaged guides and extracted-link audit.
- Package/privacy regression set: 46/46 PASS.
- Full suite: 251/251 PASS in 521.222 s.
- `scripts/audit_release.py`: PASS, 541 text files checked, zero findings.
- PowerShell help exposed the exact creation flags, five-action enum and continuation evidence flags.
- Python compilation, public-guide privacy scan and `git diff --check 1934c39..HEAD`: PASS.
- Real build `.local/releases/alma-os-client-v1-verified-be02efd.zip`: PASS, 63 members, ZIP SHA-256 `f772b3fb4e5b73dfc5de35a7ae346c5604faa0f5eb5ca6b381f2d464097fa7bb`, manifest SHA-256 `da017387aa96648c5b58d4acbba977368e6a28c615314e53a810da13283dce5f`; extraction rehashed all 62 manifest-listed members successfully.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Aligned the client source description with the canonical registry**
- **Found during:** Task 3 factual review
- **Issue:** The first guide draft named domains that do not exist in the final 22-relation registry.
- **Fix:** Replaced the prose inventory with all 22 canonical relation names and bound the guide test directly to `SOURCE_NAMES`.
- **Files modified:** `client/v1/EMPIEZA_AQUI.md`, `tests/test_weekly_kit.py`
- **Verification:** `GuideContractTests` and the full suite passed.
- **Committed in:** `be02efd`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix prevents documentation drift and adds no product scope.

## Issues Encountered

- Deep Windows fixture paths required extended-path handling during weekly run preparation and clean-archive copying. The implementation retained the same private-root and no-overwrite boundaries, and the archive restart test passes from a checkout containing only committed code plus the explicitly restored private run.

## Known Stubs

None.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration or new dependency is required.

## Next Phase Readiness

- CLIENT-03 and CLIENT-04 have executable contracts, public deliverables and regression evidence ready for Phase 5 acceptance.
- The full two-week live native cycle remains Phase 5 work by design; this plan uses fixture responses only to test validators and does not claim a live native run.
- No blockers remain.

## Self-Check: PASSED

- All seven plan-owned implementation files and this summary exist.
- All eight RED/GREEN/restart/correction commits resolve in repository history.

---
*Phase: 04-offline-client-and-analyst-kit*
*Completed: 2026-09-23*
