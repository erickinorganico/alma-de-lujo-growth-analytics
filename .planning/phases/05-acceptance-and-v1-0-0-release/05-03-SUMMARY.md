---
phase: 05-acceptance-and-v1-0-0-release
plan: 03
subsystem: release-publication
tags: [deterministic-package, tag-bound-release, github-readback, client-delivery]

# Dependency graph
requires:
  - phase: 05-acceptance-and-v1-0-0-release
    plan: 01
    provides: Two-cut synthetic native acceptance and 9/9 deterministic gates.
  - phase: 05-acceptance-and-v1-0-0-release
    plan: 02
    provides: Final workbooks, Excel/visual evidence and clean-archive verification.
provides:
  - Frozen and published Alma OS v1.0.0 client release bound to one exact commit.
  - Deterministic 69-member offline package, checksum and external acceptance receipt.
  - Windows/Ubuntu CI, clean-archive proof and published-asset readback evidence.
affects: [v1.0-release, client-handoff, future-release-verifier]

# Tech tracking
tech-stack:
  added: []
  patterns: [literal release allowlist, reproducible zip, immutable evidence sidecar, published asset readback]

key-files:
  created:
    - client/v1/release-manifest.json
    - client/v1/acceptance-summary.json
    - docs/RUNBOOK-v1.md
    - docs/ACCEPTANCE-v1.md
    - docs/RELEASE-v1.md
    - scripts/package_release_v1.py
    - scripts/audit_release_v1.py
    - tests/test_release_v1.py
    - .planning/phases/05-acceptance-and-v1-0-0-release/05-03-SUMMARY.md
  modified:
    - scripts/verify_release_archive.py
    - tests/test_release_archive.py
    - .github/workflows/verify.yml

key-decisions:
  - "Freeze v1.0.0 at commit 233ff26cc69836538d47c4af60aa7c2c13948437 and keep the documentation summary outside the tag."
  - "Ship exactly three public assets: the deterministic ZIP, its lowercase SHA-256 checksum and the external acceptance receipt."
  - "Keep mutable CI receipts under ignored .local evidence and bind them by hash from the acceptance receipt."
  - "Preserve explicit synthetic and unknown-evidence boundaries; publication does not establish product-market outcomes or authorize business execution."

requirements-completed: [REL-04]

# Metrics
duration: not recorded
completed: 2026-09-28
---

# Phase 5 Plan 03: Alma OS v1.0.0 release summary

**Alma OS v1.0.0 is published as a deterministic offline client package, tied to one frozen commit and independently read back from GitHub.**

## Release result

- **Release:** [Alma OS v1.0.0](https://github.com/erickinorganico/alma-de-lujo-growth-analytics/releases/tag/v1.0.0)
- **Frozen SHA A:** `233ff26cc69836538d47c4af60aa7c2c13948437`
- **Primary CI:** [Verify analytical release 36505261932](https://github.com/erickinorganico/alma-de-lujo-growth-analytics/actions/runs/36505261932), with Ubuntu PASS in 6m56s and Windows PASS in 11m25s.
- **Tag-triggered CI:** [Verify analytical release 36507363150](https://github.com/erickinorganico/alma-de-lujo-growth-analytics/actions/runs/36507363150), also PASS, with Ubuntu in 6m8s and Windows in 12m15s.
- **Package:** `Alma_OS_v1.0.0.zip`, 497,398 bytes, 69 exact allowlisted members.
- **ZIP SHA-256:** `48f68dbf5bd93c6267eb318a0db14cbe744ba028f748ebdfc790c2d2d792e83a`.
- **Checksum asset SHA-256:** `f651ad224b53ccf1610ebca8612512b03efe14fc46e3fd18482fd31ed0ca4aca`.
- **Acceptance asset SHA-256:** `6a9e0eb408ee52faa789315ddfe2cf940d41fcac8c2ba38d3d0a8cd25af7a65b`.
- **Inner manifest SHA-256:** `e9aa0a813d3cf95668aa8c65c58099daa4eaa83d875a216c7cb9d2f2db9c163b`.
- **Exact tagged LICENSE SHA-256:** `4d60f94f197e876592f859c38f67ad2a9dafb2ecb5ecd78672f4e2e58ed74d82`.

The release is public, is neither a draft nor a prerelease, and contains exactly the ZIP, checksum and acceptance JSON. Published readback downloaded all three into a fresh directory and returned `status=PASS`, `asset_count=3`, the exact tag target, `privacy=PASS`, `links=PASS` and the expected ZIP hash.

## Verification evidence

- The final archive proof was created once from annotated tag `v1.0.0` after both primary CI jobs were green. It returned `PASS` for SHA A after the archive workspace was moved out of the OneDrive tree.
- The canonical archive receipt SHA-256 is `0cb71901e586099c113401306571f07fe3bf14fa3d9ac2a03cbc1bc12588bd54`.
- The ignored Windows/Ubuntu CI sidecar SHA-256 is `1c5ac0dea964f4641bece538f941326baa2258ddc037a78b0b2ba0c21db1cdea`. It binds run 36505261932, both archive receipts and both four-command release-preflight receipts to SHA A.
- Two independent tag builds produced byte-identical ZIP, checksum and acceptance assets. The package auditor returned 69 members, exact manifest and LICENSE hashes, `privacy=PASS`, `links=PASS` and `status=PASS`.
- The extracted offline smoke opened all 69 members with zero unreadable entries. The legacy publishable-scope audit inspected 575 text files and returned no findings.
- The final focused archive and release suites passed 32/32 before SHA A. The broader deterministic v1 acceptance remains 9/9 PASS, with two synthetic cuts and 14 distinct native tasks.

## Deviation discovered after publication

Pushing the tag legitimately triggered a second workflow for the same commit. That run also completed successfully on Windows and Ubuntu and published all four expected receipts. The prescribed post-publication `prove --check-existing` command selects the newest same-SHA run instead of the run ID already frozen in the sidecar; it therefore blocked with `same-SHA workflow run is not successful` while the tag-triggered run was active, and its strict run-ID comparison cannot accept the newer successful run. It did not rewrite either evidence file.

A supplemental read-only validation pinned to saved run 36505261932 re-downloaded and revalidated both operating-system archive receipts and both preflight receipts. It returned `PASS` and preserved the archive and sidecar hashes byte for byte. The published-release verifier also passed against freshly downloaded assets. The release, tag, assets and immutable sidecar were retained; the good release was not deleted or replaced. The future verifier should read back the run ID saved in an existing sidecar rather than select the newest same-SHA run.

## Evidence boundaries and client limitations

- Both business cycles and the populated workbook are explicitly synthetic. They demonstrate the operating process and decision controls; they do not prove that Pilates socks are a commercial winner.
- External evidence gates remain `EXT-01=UNKNOWN`, `EXT-02=UNKNOWN` and `EXT-03=REVIEW`.
- No real customer data, credentials, private response prose or query contents are included. No third-party redistributable assets are bundled.
- Desktop Excel 16.0 build 20326 recalculated the exact delivered books. All 62 rendered pages passed visual inspection; seven pages retain an incomplete footer page-number field while their content remains readable.
- The client ZIP is an offline analytical handoff for capture, review and operating guidance. It does not execute external business actions and is not a store, CRM or ERP.

## Publication model

The tag remains on SHA A. This summary is the sole planned tracked byte after the tag and is not included in the ZIP. Direct publication to the authorized `erickinorganico` repository was used; no pull request was created for this final direct-main flow.

---
*Phase: 05-acceptance-and-v1-0-0-release*
*Completed: 2026-09-28*
