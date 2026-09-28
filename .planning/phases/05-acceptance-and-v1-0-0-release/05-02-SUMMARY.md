---
phase: 05-acceptance-and-v1-0-0-release
plan: 02
subsystem: release-verification
tags: [workbooks, excel, visual-inspection, clean-archive, cross-platform-ci]

# Dependency graph
requires:
  - phase: 05-acceptance-and-v1-0-0-release
    plan: 01
    provides: Post-fix 9/9 deterministic acceptance and two-cut native evidence.
provides:
  - Final blank and synthetic operating workbooks with independent acceptance checks.
  - Fresh desktop Excel recalculation and complete rendered-page inspection evidence.
  - Clean committed-archive proof and same-SHA Windows/Ubuntu CI receipts.
affects: [05-03, v1.0-release]

# Tech tracking
tech-stack:
  added: []
  patterns: [integer-and-decimal-oracle, exact-byte-receipts, disposable-git-archive, same-sha-ci-readback]

key-files:
  created:
    - client/v1/Alma_de_Lujo_OPERACION_PLANTILLA.xlsx
    - client/v1/Alma_de_Lujo_OPERACION_EJEMPLO.xlsx
    - client/v1/workbook-manifest.json
    - evidence/v1.0/excel/excel-recalculation.json
    - evidence/v1.0/excel/visual-inspection.json
    - scripts/verify_release_archive.py
    - tests/test_release_archive.py
  modified:
    - scripts/verify_operating_workbooks.py
    - scripts/recalculate_operating_workbooks.ps1
    - .github/workflows/verify.yml
    - scripts/verify_v1.py

key-decisions:
  - "Treat the blank workbook as a capture surface; it is not a buildable analytical cut until populated."
  - "Require the archive runner and all child processes to use one disposable virtual environment."
  - "Keep mutable GitHub run and artifact provenance only in the ignored rehearsal sidecar."
  - "Compare Windows short and long path aliases by filesystem identity."

requirements-completed: [REL-02, REL-03]

# Metrics
duration: not recorded
completed: 2026-09-28
---

# Phase 5 Plan 02: Workbook, clean archive and CI summary

**The final operating books, fresh Excel evidence, clean committed archive and Windows/Ubuntu receipts are bound to reviewed bytes and one rehearsal SHA.**

## Accomplishments

- Generated the final blank and synthetic XLSX pair with all 22 operating relations and 25 print areas per workbook. The manifest records the exact post-Excel hashes, sheet dimensions, tables, validations and source-pack provenance.
- Verified the books with an independent integer/Decimal oracle and adversarial checks for formula injection, hidden content, external relationships, metadata and member/hash drift. The final focused workbook suite passed 11/11.
- Recalculated both books in Microsoft Excel 16.0 build 20326 and exported 50 PDFs. All 62 rendered pages were individually inspected and recorded as PASS. Seven pages have an incomplete Excel footer page-number field; their content and pagination remain readable.
- Implemented a fail-closed archive verifier that extracts only committed blobs, creates a disposable venv, installs the pinned optional requirements, executes deterministic, privacy/link, workbook and public-scope gates, and records canonical outputs without claiming that CI ran Excel.
- Fixed verified portability defects exposed by CI: relative venv paths, child-process interpreter leakage, nested deterministic workspace collision and Windows 8.3 path aliases. The focused archive/v1 suites passed 25/25 after the final isolation change; the operating-intake suite passed 17/17 after the path-identity correction.
- Proved rehearsal SHA `18ea43a7905074cc6e1636868aa650ead220a794` from a clean archive on local Windows 3.12.14 in 966.89 seconds. Its four gates passed: v1 deterministic, client package/privacy/links, final workbooks/receipts and publishable-source audit.
- GitHub Actions run [36496657719](https://github.com/erickinorganico/alma-de-lujo-growth-analytics/actions/runs/36496657719) completed successfully for both `ubuntu-latest` and `windows-latest`, with both job receipts declaring the exact rehearsal SHA.
- Read-only `prove --check-existing` passed and preserved receipt bytes. The local archive receipt SHA-256 is `8783221713ec47533ac6f0e060a232c53ff5ed397b59c416d38c95fef880f30f`; the ignored rehearsal sidecar SHA-256 is `674fae48cbd6ec68b70c8fe7db2b68eac1e7499679936cf942f7fb679244c455`.

## Evidence boundaries

- `evidence/v1.0/excel/` is committed evidence for the exact final workbook bytes. CI validates it but records `excel_executed=false`; only the local desktop receipt establishes actual Excel execution.
- `.local/release-evidence/v1.0.0-ci-rehearsal-p.json` and its downloaded receipts are ignored rehearsal evidence for SHA P. They are not final tag evidence and must not be packaged or committed.
- The workbook example and analytical cycles use synthetic data. They do not establish that Pilates socks are a winning product, prove owner adoption or authorize business execution.
- External gates remain `EXT-01=UNKNOWN`, `EXT-02=UNKNOWN` and `EXT-03=REVIEW`.

## Deviations and issues

Cross-platform CI revealed four portability defects that local Windows checks did not expose. Each failure was diagnosed from bounded, redacted output, fixed at its actual boundary and covered by a focused regression test. No gate was skipped or downgraded.

The rendered content is accepted, but seven pages retain an incomplete Excel footer page-number field. This is recorded as a limitation rather than represented as a perfect footer render.

## Next phase readiness

REL-02 and REL-03 are complete. Plan 05-03 may implement the deterministic outer release package, documentation, manifest and publication flow. It must create a separate final SHA-A archive/CI sidecar after all release inputs are committed; this rehearsal sidecar cannot substitute for final tag evidence.

---
*Phase: 05-acceptance-and-v1-0-0-release*
*Completed: 2026-09-28*
