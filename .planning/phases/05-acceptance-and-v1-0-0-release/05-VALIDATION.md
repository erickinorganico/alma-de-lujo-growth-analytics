---
phase: 05
slug: acceptance-and-v1-0-0-release
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-22
---

# Phase 05 — Validation Strategy

> Contrato Nyquist del hito final: aceptación integrada, evidencia Office, archivo limpio, CI y release reproducible.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python 3.11 `unittest`, PowerShell, Microsoft Excel evidence, Git/GitHub Actions |
| **Config file** | `.github/workflows/verify.yml`, `tests/` discovery |
| **Quick run command** | `.venv\Scripts\python.exe -m unittest tests.test_v1_acceptance tests.test_v1_release -v` |
| **Full suite command** | `.venv\Scripts\python.exe -m unittest discover -s tests -v` |
| **Estimated runtime** | ~5 minutes locally, excluding native-agent waits and remote CI |

## Sampling Rate

- **After every task commit:** Run the affected acceptance/release module and its upstream focused modules.
- **After every plan wave:** Run the full suite plus the wave-specific artifact auditor.
- **Before `$gsd-verify-work`:** Full suite, two-cut acceptance, privacy audit, clean archive and extracted-ZIP audit must be green.
- **Max feedback latency:** 10 minutes for deterministic checks; native/CI evidence has explicit waiting state.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | REL-01 | plan threat refs | Positive/partial/tamper/duplicate/double-count matrix preserves invariants | adversarial | `.venv\Scripts\python.exe -m unittest tests.test_v1_acceptance -v` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | REL-01 | plan threat refs | Two distinct cuts carry one reviewed decision to closure or stale | end-to-end | `.venv\Scripts\python.exe -m unittest tests.test_v1_acceptance.TwoCutAcceptanceTests -v` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | REL-01 | plan threat refs | Actual native receipts and independent review revalidate | integration | `.venv\Scripts\python.exe scripts/run_weekly_cycle.py verify-acceptance --receipt evidence/v1/native-cycle-acceptance.json` | planned | ⬜ pending |
| 05-02-01 | 02 | 2 | REL-02 | plan threat refs | Independent Decimal oracle agrees with workbook arithmetic | oracle | `.venv\Scripts\python.exe -m unittest tests.test_v1_excel_acceptance -v` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | REL-02 | plan threat refs | Delivered workbook bytes have fresh recalculation/visual receipt when formulas changed | artifact | `.venv\Scripts\python.exe scripts/verify_v1_office_evidence.py` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | REL-03 | plan threat refs | Clean Git archive reproduces tests/build/hashes/privacy and CI matrix | reproducibility | `.venv\Scripts\python.exe scripts/verify_v1_clean_archive.py` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 3 | REL-04 | plan threat refs | ZIP allowlist, paths, hashes, PII/secrets and links audit after extraction | adversarial | `.venv\Scripts\python.exe -m unittest tests.test_v1_release -v` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 3 | REL-04 | plan threat refs | Runbook/acceptance/checksum bind exact release bytes | integration | `.venv\Scripts\python.exe scripts/audit_v1_release.py --release-dir dist/v1.0.0` | ❌ W0 | ⬜ pending |
| 05-03-03 | 03 | 3 | REL-04 | plan threat refs | GitHub tag/release assets and checksum match clean local evidence | release | `.\scripts\github-personal.ps1 release view v1.0.0` | existing wrapper | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [ ] `tests/test_v1_acceptance.py` — integrated adversarial and two-cut acceptance.
- [ ] `tests/test_v1_excel_acceptance.py` — independent workbook arithmetic/structure checks.
- [ ] `tests/test_v1_release.py` — extracted package, checksum, privacy and link checks.
- [ ] Verification scripts named in the plans are created before their plan task can turn green.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Excel rendered inspection | REL-02 | Formula engine and visual layout need desktop Office evidence | Recalculate the exact release workbook, inspect key sheets and print preview, then hash the receipt and screenshots. |
| GitHub checks and release publication | REL-03/04 | External service state cannot be proven by local tests | Use the isolated `erickinorganico` wrapper, wait for Windows/Linux checks, compare published asset hashes and attach the PR artifact. |

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or an explicit external evidence gate.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [ ] Wave 0 creates every missing acceptance test/script before implementation continues.
- [x] No watch-mode flags.
- [x] Deterministic local feedback target is under 10 minutes.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** strategy approved for autonomous execution; final evidence and external CI/release state remain pending.
