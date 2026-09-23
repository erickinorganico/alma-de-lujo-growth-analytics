---
phase: 05
slug: acceptance-and-v1-0-0-release
status: architecture-approved
execution_status: pending
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-22
updated: 2026-09-22
---

# Phase 05 — Validation Strategy

> Nyquist contract for the final milestone: integrated acceptance, actual native v1 evidence, Office evidence, one frozen committed archive, same-SHA CI and release readback.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python 3.12 `unittest`, PowerShell, Microsoft Excel evidence, Git/GitHub Actions |
| **Config files** | `.github/workflows/verify.yml`, `tests/` discovery |
| **Quick run command** | `.venv\Scripts\python.exe -m unittest tests.test_v1_release_acceptance tests.test_release_v1 -v` |
| **Full suite command** | `.venv\Scripts\python.exe -m unittest discover -s tests -v` |
| **Deterministic release command** | `.venv\Scripts\python.exe scripts/verify_v1.py deterministic --output evidence/v1.0/regression-acceptance.json` |
| **Expected local latency** | Under 10 minutes for focused deterministic checks; clean archive, native, Excel and remote CI have explicit bounded external states |

## Sampling Rate

- **During each TDD task:** write the named test in that same task, observe its target failure, implement, and run the exact `<automated>` command before completion.
- **After every task commit:** rerun the affected module and the upstream focused modules named by that task.
- **After every plan wave:** run the full suite plus the wave-specific artifact verifier.
- **Before `$gsd-verify-work`:** full regression, two-cut acceptance, actual native v1 receipt, Excel/rendered-page evidence, clean archive, both same-SHA CI jobs and downloaded release audit must be green.
- **No inferred evidence:** fixture responses never prove native execution; CI never proves fresh Excel; a local pass never substitutes for either remote OS job or published-asset readback.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure behavior | Automated command | Test availability | Status |
|---------|------|------|-------------|-----------------|-------------------|-------------------|--------|
| 05-01-01 | 01 | 1 | REL-01 | Positive, partial, tamper, duplicate, double-count, replay and two-distinct-cut invariants | `.venv/Scripts/python.exe -m unittest tests.test_v1_release_acceptance -v` | Same-task TDD: `tests/test_v1_release_acceptance.py` | pending |
| 05-01-02 | 01 | 1 | REL-01 | Historical and v1 deterministic gates fail closed and produce a sanitized receipt | `.venv/Scripts/python.exe scripts/verify_v1.py deterministic --output evidence/v1.0/regression-acceptance.json` | Same-task TDD extends `tests/test_v1_release_acceptance.py` | pending |
| 05-01-03 | 01 | 1 | REL-01 | Actual v1 request/response/query-trace/dispatch/reviewer/packet/register chain and distinct reviewer revalidate | `.venv/Scripts/python.exe scripts/verify_v1.py finalize-live --run .local/v1-acceptance --summary evidence/v1.0/two-week-native.json` | Validator implemented and tested by 05-01-02; live evidence produced in task | pending |
| 05-02-01 | 02 | 2 | REL-02 | Independent Decimal/integer oracle agrees with formulas, cached values and round-trip semantics | `.venv/Scripts/python.exe -m unittest tests.test_operating_workbook_acceptance -v` | Same-task TDD: `tests/test_operating_workbook_acceptance.py` | pending |
| 05-02-02 | 02 | 2 | REL-02 | Exact books have fresh Excel evidence plus one hashed inspected PNG per PDF page | `.venv/Scripts/python.exe scripts/verify_operating_workbooks.py check --manifest client/v1/workbook-manifest.json --excel-receipt evidence/v1.0/excel/excel-recalculation.json --visual-receipt evidence/v1.0/excel/visual-inspection.json` | Same-task artifacts; verifier from 05-02-01 | pending |
| 05-02-03 | 02 | 2 | REL-03 | Clean archive and downloaded Windows/Ubuntu receipts bind one frozen pre-merge SHA P; verifier is reused for final A | `.venv/Scripts/python.exe -m unittest tests.test_release_archive -v && .venv/Scripts/python.exe scripts/verify_release_archive.py prove --ref HEAD --output .local/release-archive --archive-receipt .local/release-evidence/v1.0.0-archive.json --remote-sidecar .local/release-evidence/v1.0.0-ci-reproducibility.json` | Same-task TDD: `tests/test_release_archive.py`; run after tracked inputs are committed/pushed | pending |
| 05-03-01 | 03 | 3 | REL-04 | Deterministic ZIP allowlist, extraction bounds, hashes, binary inventory, privacy and links | `.venv/Scripts/python.exe -m unittest tests.test_release_v1 -v` | Same-task TDD: `tests/test_release_v1.py` | pending |
| 05-03-02 | 03 | 3 | REL-04 | Runbook, acceptance summary and all other payload bytes exist before the final non-recursive manifest is generated and checked | `.venv/Scripts/python.exe -m unittest tests.test_release_v1.ReleaseDocumentationTests -v && .venv/Scripts/python.exe scripts/audit_release_v1.py check-manifest --manifest client/v1/release-manifest.json --source-root . --require-version 1.0.0` | Same-task test class in `tests/test_release_v1.py`; final manifest owned by this task | pending |
| 05-03-03 | 03 | 3 | REL-04 | Canonical tag-resolved SHA A sidecar is created once before publication; read-only check, local audit and wrapper-downloaded assets preserve and revalidate it | `.venv/Scripts/python.exe scripts/verify_release_archive.py prove --check-existing --ref v1.0.0 --archive-receipt .local/release-evidence/v1.0.0-archive-final.json --remote-sidecar .local/release-evidence/v1.0.0-ci-reproducibility.json && .venv/Scripts/python.exe scripts/audit_release_v1.py --zip .local/releases/Alma_OS_v1.0.0.zip --checksum .local/releases/Alma_OS_v1.0.0.zip.sha256 --acceptance .local/releases/Alma_OS_v1.0.0.acceptance.json --ci-sidecar .local/release-evidence/v1.0.0-ci-reproducibility.json --require-version 1.0.0 && .venv/Scripts/python.exe scripts/audit_release_v1.py verify-published --tag v1.0.0 --github-wrapper scripts/github-personal.ps1 --ci-sidecar .local/release-evidence/v1.0.0-ci-reproducibility.json --download-dir .local/releases/readback-v1.0.0 --require-version 1.0.0` | `prove --check-existing` nonmutation covered by `tests/test_release_archive.py`; publisher/readback covered by `tests/test_release_v1.py` | pending |

## Wave 0 Decision

No separate Wave 0 plan is required. Every implementation task that introduces a test uses same-task TDD and names the created test file in `<files>`. Tasks that consume Excel, native Codex or GitHub state use a previously tested fail-closed validator plus an exact automated receipt/readback command. Therefore there are no `MISSING` test references and no task depends on an unplanned future test.

## External Evidence Boundaries

| Boundary | Requirement | Evidence rule |
|----------|-------------|---------------|
| Native Codex | REL-01 | Follow `agents/RUN-NATIVE-CYCLE-v1.md`; retain private responses/query traces locally and publish only validator-approved hashes/status. |
| Desktop Excel and visual inspection | REL-02 | Recalculate exact books in a fresh Excel instance, render every exported PDF page to PNG, inspect every PNG, and validate page count/hashes/dispositions. |
| GitHub Actions | REL-03 | Freeze SHA A after tracked inputs are committed; wrapper-only readback must show successful Windows and Ubuntu jobs with `headSha=A`; store mutable provenance only in ignored sidecar. |
| GitHub release | REL-04 | Wrapper-only view/download to a fresh directory followed by complete checksum, acceptance and extracted-ZIP re-audit; `verify-published --ci-sidecar` rehashes the ignored local CI proof against the downloaded acceptance sidecar and requires both OS receipts to name tag target A. |

## Nyquist Sign-Off

- [x] All nine tasks contain an exact `<automated>` command.
- [x] Every created test is owned by its same implementation task; no missing Wave 0 path exists.
- [x] Every wave has continuous automated sampling; no three-task window lacks checks.
- [x] No watch-mode or unbounded retry command exists.
- [x] External states have fail-closed validators and cannot be upgraded by local or fixture evidence.
- [x] The command/file names and Python 3.12 boundary match `05-01/02/03-PLAN.md`.

**Validation architecture approval:** internally complete. **Release execution:** PENDING and remains BLOCKED until the actual native, Excel, same-SHA CI and published-release readback evidence exists. No acceptance summary may label the release approved before those external receipts pass.
