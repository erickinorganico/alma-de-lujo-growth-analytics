---
phase: 04
slug: offline-client-and-analyst-kit
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-22
---

# Phase 04 — Validation Strategy

> Contrato de validación para libros operativos, portal offline, ciclo semanal y paquete público.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python 3.11 `unittest` + validadores XLSX/HTML/ZIP existentes |
| **Config file** | `tests/` discovery; no config file |
| **Quick run command** | `.venv\Scripts\python.exe -m unittest tests.test_operating_workbooks tests.test_offline_portal_v1 tests.test_weekly_kit -v` |
| **Full suite command** | `.venv\Scripts\python.exe -m unittest discover -s tests -v` |
| **Estimated runtime** | ~120 seconds before browser/Excel evidence |

## Sampling Rate

- **After every task commit:** Run the affected test module named in the plan.
- **After every plan wave:** Run all three Phase 04 modules.
- **Before `$gsd-verify-work`:** Full suite must be green and generated links must resolve from an extracted package.
- **Max feedback latency:** 180 seconds.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CLIENT-01 | T-04-01/02/03 | Registry-complete, safe blank/example workbook generation | integration | `.venv\Scripts\python.exe -m unittest tests.test_operating_workbooks.OperatingWorkbookGenerationTests -v` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | CLIENT-01 | T-04-01/02 | Workbook input fails closed before canonical export | adversarial | `.venv\Scripts\python.exe -m unittest tests.test_operating_workbooks -v` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | CLIENT-02 | T-04-04/05/06 | Demo/private provenance and hashes cannot mix | integration | `.venv\Scripts\python.exe -m unittest tests.test_offline_portal_v1.PortalEvidenceTests -v` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | CLIENT-02 | T-04-06/07 | Static portal is escaped, accessible and link-complete | integration | `.venv\Scripts\python.exe -m unittest tests.test_offline_portal_v1 -v` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | CLIENT-03 | T-04-08/09/11 | Weekly command preserves waiting/blocked/native boundaries | end-to-end | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.WeeklyCommandTests -v` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 2 | CLIENT-04 | T-04-10 | Public ZIP excludes private/native content and resolves offline | adversarial | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit.ClientKitTests -v` | ❌ W0 | ⬜ pending |
| 04-03-03 | 03 | 2 | CLIENT-03/04 | T-04-08/10/11 | Guides, launcher help and package paths agree | integration | `.venv\Scripts\python.exe -m unittest tests.test_weekly_kit -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [ ] `tests/test_operating_workbooks.py` — CLIENT-01 generation and import controls.
- [ ] `tests/test_offline_portal_v1.py` — CLIENT-02 provenance, accessibility and links.
- [ ] `tests/test_weekly_kit.py` — CLIENT-03/04 command, privacy and extracted package controls.
- Existing Python/XLSX/HTML/ZIP infrastructure is reused; no package install is planned.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Desktop/narrow/print portal inspection | CLIENT-02 | Visual hierarchy and print legibility need rendered inspection | Open public and private fixtures via `file://`, inspect desktop/narrow/print, keyboard focus, provenance and warning visibility; save screenshots/receipt under Phase 05 evidence. |
| Excel desktop open/recalculation when formulas change | CLIENT-01 | Microsoft Excel behavior cannot be inferred from openpyxl | Recalculate the delivered bytes with the pinned PowerShell script, reopen read-only, inspect sheets/print setup and record hash-bound receipt. |

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [ ] Wave 0 creates every missing test file before implementation continues.
- [x] No watch-mode flags.
- [x] Feedback latency target is under 180 seconds.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** strategy approved for autonomous execution; evidence remains pending.
