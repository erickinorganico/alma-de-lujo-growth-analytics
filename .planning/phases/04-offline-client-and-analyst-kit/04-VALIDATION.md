---
phase: 04
slug: offline-client-and-analyst-kit
status: draft
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
| 04-01-01 | 01 | 1 | CLIENT-01 | T-04-01/02/03 | Registry-complete, safe blank/example workbook and policy-material generation | integration | `.venv\Scripts\python.exe -m unittest tests.test_operating_workbooks.OperatingWorkbookGenerationTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-01-02 | 01 | 1 | CLIENT-01 | T-04-01/02 | Workbook input fails closed before canonical export | adversarial | `.venv\Scripts\python.exe -m unittest tests.test_operating_workbooks.WorkbookImportTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-02-01 | 02 | 1 | CLIENT-02 | T-04-04/05/06 | Demo/private provenance and hashes cannot mix | integration | `.venv\Scripts\python.exe -m unittest tests.test_offline_portal_v1.PortalEvidenceTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-02-02 | 02 | 1 | CLIENT-02 | T-04-06/07 | Static portal is escaped, accessible and link-complete | integration | `.venv\Scripts\python.exe -m unittest tests.test_offline_portal_v1.PortalAccessibilityTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-03-01 | 03 | 2 | CLIENT-03 | T-04-08/09/11 | Weekly command preserves policy, prior-cycle and waiting/native boundaries | end-to-end | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.WeeklyCommandTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-03-02 | 03 | 2 | CLIENT-04 | T-04-10 | Public ZIP excludes private/native content and resolves offline | adversarial | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.ClientKitTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |
| 04-03-03 | 03 | 2 | CLIENT-03/04 | T-04-08/10/11 | Guides, launcher help and package paths agree | integration | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.GuideContractTests -v` | task creates/extends in RED | ⬜ planned RED/GREEN |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Same-Task TDD Contract

- [x] Existing Python `unittest` discovery plus XLSX/HTML/ZIP validators satisfies Wave 0; no package install or separate test-infrastructure task is required.
- [x] Every implementation task owns the named test file/class and first creates or extends a failing test, runs its focused command to record the expected RED result, and only then changes production or generated-output code until GREEN.
- [x] No plan depends on a missing Wave 0 test file: test creation is an explicit first step inside the same task that implements the behavior.
- [x] Task 04-03-03 runs its focused guide-contract smoke first, then the slower package/privacy regressions, full `unittest` discovery and release audit as final gates.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Desktop/narrow/print portal inspection | CLIENT-02 | Visual hierarchy and print legibility need rendered inspection | Open public and private fixtures via `file://`, inspect desktop/narrow/print, keyboard focus, provenance and warning visibility; save screenshots/receipt under Phase 05 evidence. |
| Excel desktop open/recalculation when formulas change | CLIENT-01 | Microsoft Excel behavior cannot be inferred from openpyxl | Recalculate the delivered bytes with the pinned PowerShell script, reopen read-only, inspect sheets/print setup and record hash-bound receipt. |

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Same-task RED stages create or extend every planned test before implementation continues.
- [x] No watch-mode flags.
- [x] Focused per-task feedback target is under 30 seconds; slower full final gates are identified separately.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** strategy approved for autonomous execution; evidence remains pending.
