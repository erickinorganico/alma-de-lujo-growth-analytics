---
phase: 04
slug: offline-client-and-analyst-kit
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-22
---

# Phase 04 — Validation Strategy

> Contrato de validación para libros operativos, portal offline, ciclo semanal y paquete público.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python 3.11 `unittest` + validadores XLSX/HTML/ZIP existentes |
| **Config file** | `tests/` discovery; no config file |
| **Focused smoke command** | Run the affected test class named in the per-task map with `.venv\Scripts\python.exe`; each target stays under 30 seconds |
| **Package/privacy regression** | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.ClientKitTests tests.test_client_system tests.test_client_review tests.test_security -v` |
| **Full suite command** | `.venv\Scripts\python.exe -m unittest discover -s tests -v` |
| **Release audit command** | `.venv\Scripts\python.exe scripts/audit_release.py` |
| **Focused smoke target** | Each per-task class/module command completes in under 30 seconds on local synthetic fixtures |
| **Slower final gates** | Full discovery, package/privacy regressions and release audit run after the focused Task 3 smoke and may exceed 30 seconds |

## Sampling Rate

- **After every task commit:** Run the affected test module named in the plan.
- **After every plan wave:** Run all three Phase 04 modules as a slower wave gate after focused feedback.
- **Before `$gsd-verify-work`:** Package/privacy regressions, full suite and release audit must be green, and generated links must resolve from an extracted package.
- **Focused feedback latency target:** under 30 seconds; slower full-suite, package/privacy and release-audit gates run only as the final Task 3 regression set.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CLIENT-01 | T-04-01/02/03 | Registry-complete generation plus parameterized omission state for each of 22 relations | integration | `.venv\Scripts\python.exe -m unittest tests.test_operating_workbooks.OperatingWorkbookGenerationTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-01-02 | 01 | 1 | CLIENT-01 | T-04-01/02 | Independent workbook→pack→manifest oracle and fail-closed canonical export | adversarial | `.venv\Scripts\python.exe -m unittest tests.test_operating_workbooks.WorkbookImportTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-02-01 | 02 | 2 | CLIENT-02 | T-04-04/05/06 | Demo/private provenance and hashes cannot mix | integration | `.venv\Scripts\python.exe -m unittest tests.test_offline_portal_v1.PortalEvidenceTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-02-02 | 02 | 2 | CLIENT-02 | T-04-06/07 | Mart→portal→CSV→JSON boundary parity, accessible rendering and hash-bound visual evidence | integration | `.venv\Scripts\python.exe -m unittest tests.test_offline_portal_v1.PortalAccessibilityTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-03-01 | 03 | 3 | CLIENT-03 | T-04-08/09/11 | Weekly creation plus exact record/submit/resume/packet/register continuation from a clean checkout | end-to-end | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.WeeklyCommandTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-03-02 | 03 | 3 | CLIENT-04 | T-04-10 | Informational/synthetic public ZIP excludes runtime/private/native content and resolves offline | adversarial | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.ClientKitTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-03-03 | 03 | 3 | CLIENT-03/04 | T-04-08/10/11 | Creation/continuation help, clean-checkout restart and public-kit boundaries agree | integration | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.GuideContractTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-04-01 | 04 | 4 | CLIENT-03 | T-04-12/13/14/15/16 | Integrated package-stage exact contract, determinism, replay refusal, atomic failure, tamper rejection and clean-process restart | end-to-end | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.WeeklyPackageStageTests tests.test_weekly_kit.GuideContractTests -v` | task extends in RED | ⬜ planned RED |
| 04-04-02 | 04 | 4 | CLIENT-03 | T-04-12/13/14/15/16 | Public-only builder/auditor reuse, immutable package receipt/index and truthful weekly result | integration | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.WeeklyPackageStageTests tests.test_weekly_kit.WeeklyCommandTests tests.test_weekly_kit.ClientKitTests tests.test_weekly_kit.GuideContractTests -v` | Task 1 creates RED contract | ⬜ planned GREEN |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Same-Task TDD Contract

- [x] Existing Python `unittest` discovery plus XLSX/HTML/ZIP validators satisfies Wave 0; no package install or separate test-infrastructure task is required.
- [x] Every implementation task owns the named test file/class and first creates or extends a failing test, runs its focused command to record the expected RED result, and only then changes production or generated-output code until GREEN.
- [x] No plan depends on a missing Wave 0 test file: test creation is an explicit first step inside the same task that implements the behavior.
- [x] Task 04-03-03 runs its focused guide-contract smoke first, then the slower package/privacy regressions, full `unittest` discovery and release audit as final gates.
- [x] Wave order is explicit: 04-01 workbook truth → 04-02 portal/parity/visual truth → 04-03 weekly/package integration.
- [x] Gap-closure Wave 4 runs only after 04-03 and uses a dedicated RED contract before wiring `weekly` to the existing public package builder/auditor.
- [x] Phase 5 Plan 05-03 retains ownership of deep self-consistent secret/PII scanning inside allowlisted members; 04-04 does not broaden or claim that audit.
- [x] The two independent parity oracles have non-overlapping ownership: workbook→pack→manifest in 04-01 and mart→portal→CSV→JSON in 04-02.
- [x] Portal visual evidence is owned and blocking in 04-02; it is not deferred to an unowned Phase 5 step.
- [x] Phase 5 Plan 05-02 already owns fresh Excel formula/cache/page evidence for final bytes; Phase 4 makes no broader unexecuted spreadsheet-engine claim.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Desktop/narrow/print portal inspection | CLIENT-02 | Visual hierarchy and print legibility need rendered inspection | Owned by 04-02 Task 2: open exact public and safe synthetic-current fixtures via `file://`; capture desktop 1440px, narrow 390px and every print/PDF page; inspect focus, clipping, provenance, warnings and links; write `evidence/v1.0/portal/portal-visual-inspection.json` with exact hashes and dispositions. Missing or BLOCKED evidence prevents 04-02 completion. |
| Excel desktop open/recalculation for final delivered bytes | CLIENT-01 / REL-02 | Microsoft Excel behavior cannot be inferred from openpyxl | Phase 4 proves OOXML structure and workbook→pack→manifest parity. Phase 5 Plan 05-02 treats the books as changed, recalculates the exact final bytes in desktop Excel, independently checks formulas/caches and records hash-bound page evidence. Desktop Excel is the declared engine boundary; CSV is the reader-neutral fallback, so no unexecuted LibreOffice claim remains. |
| Clean-checkout process restart | CLIENT-03 | Process and filesystem isolation must be exercised across OS processes | Owned by 04-03 Task 1: start a synthetic cut to WAITING, terminate, continue from a second process in a clean `git archive`/repository checkout with the ignored private run supplied explicitly, exercise record/submit/resume/packet/register and prove all earlier receipt bytes unchanged. |

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Same-task RED stages create or extend every planned test before implementation continues.
- [x] No watch-mode flags.
- [x] Focused per-task feedback target is under 30 seconds; slower full final gates are identified separately.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** strategy revised and approved 2026-09-23; execution evidence remains pending.
