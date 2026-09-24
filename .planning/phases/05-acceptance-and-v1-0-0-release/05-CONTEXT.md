# Phase 5 Context — Acceptance and v1.0.0 Release

## Source and status

This context turns the binding release requirements in `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `05-RESEARCH.md`, `AGENTS.md`, and the planned Phase 1–4 contracts into implementation decisions. There was no Phase 5 discussion context before planning. These decisions govern acceptance and publication; they do not convert external client, fiscal, adoption, or product-market evidence into software acceptance.

## Decisions

- **D-01 — Regression plus v1 acceptance is one release gate.** The unchanged v0.2 and v0.3 verification commands remain blocking, and v1 adds positive, partial, tamper, duplicate, double-count and two-distinct-week coverage. A v1 pass cannot compensate for a historical regression, and a historical pass cannot stand in for v1 evidence. Source: REL-01 and `05-RESEARCH.md`.
- **D-02 — Week two must be a different cut.** Acceptance uses two synthetic operating packs with different cutoffs, cut IDs, source hashes and changed observations. An exact replay proves idempotence separately. At least one reviewed week-one decision must retain its original anchor in week two and reach either validated closure or a deterministic stale state; both closure and stale branches are tested. Source: REL-01, FLOW-05 and `05-RESEARCH.md`.
- **D-03 — Live native evidence stays distinct from deterministic CI.** Before any aggregate-v1 live execution, Phase 5 updates the repository routing instruction in `AGENTS.md`: aggregate-v1 cycles must use `agents/RUN-NATIVE-CYCLE-v1.md` and the sole v1 role contract `agents/native-cycle-v1.roles.json`; the historical `agents/RUN-NATIVE-CYCLE.md` remains a v0.2 regression input only. The release run then executes actual aggregate-v1 native Codex analyst tasks and a different independent reviewer under that authoritative route. Every accepted analyst receipt binds the request, response, registered-query trace and dispatch hashes; the reviewer request binds every accepted analyst digest before the separate Astra task starts. Full requests, responses, query traces and registers stay in ignored `.local/`; the public acceptance record contains only safe runtime identifiers, roles/models, timestamps, hashes, challenge disposition and final process state. Fixture responses test validators but never count as live inference. Source: current `AGENTS.md`, Phase 3 v1 contracts, REL-01 and `05-RESEARCH.md`.
- **D-04 — Exact arithmetic has an independent oracle.** Source-to-mart cents and units, partial coverage, complete-versus-known cost, obligations/payments/cash layers and decision closure are independently recomputed with Python `Decimal` and integers. SQLite file bytes need not be identical after a clean rebuild; canonical rows, exports, relationships and declared hashes must be identical. Source: REL-01, REL-02 and `05-RESEARCH.md`.
- **D-05 — New workbook delivery requires fresh Excel evidence.** Compare delivered workbook formulas, layout and bytes to the accepted v0.3 baseline. The new v1 operational books are a changed delivery surface, so the v1 release runs a fresh desktop Excel recalculation, independent Decimal comparison and complete-page visual inspection tied to final workbook/PDF hashes. CI verifies the recorded evidence and exact bytes; it does not claim to rerun Excel. Source: REL-02 and `05-RESEARCH.md`.
- **D-06 — Reproducibility starts from one frozen committed archive.** Every archive/CI proof resolves its ref once and uses the same immutable SHA for the local archive and both OS jobs. A pre-merge rehearsal may use candidate SHA P, but it never substitutes for release proof and writes only `.local/release-evidence/v1.0.0-ci-rehearsal-p.json`. After merge, the reviewed commit becomes final SHA A; no release input or other tracked file may change before tagging, archive proof, publication and readback. Archive plus Windows/Ubuntu CI are rerun for exactly A before tagging. Actual CI run/job URLs, conclusions and downloaded receipt hashes live in an ignored external sidecar bound to the proven SHA. After successful publication/readback, exactly one documentation-only commit B may add `.planning/phases/05-acceptance-and-v1-0-0-release/05-03-SUMMARY.md`; `git diff --name-only A..B` must contain only that path, B is never tagged or used to rebuild/upload assets, and every release receipt continues to identify A. No other tracked mutation follows. Install only pinned existing dependencies. The project wrapper `scripts/github-personal.ps1` is the only GitHub CLI route and must validate `erickinorganico`. Source: REL-03, `AGENTS.md` and `05-RESEARCH.md`.
- **D-07 — Audit the extracted release, including binary surfaces and licensing.** The v1 gate uses an explicit member allowlist, normalized paths, per-member SHA-256, decompression bounds, workbook XML/metadata/comment/link/macro inspection, PDF/image inventory, offline link resolution and secret/PII/private-artifact scanning. The repository `LICENSE` is a literal required ZIP member and manifest entry whose bytes must match the tagged tree. If any third-party code, font, template or other redistributable asset is bundled, a manifest classification and `THIRD-PARTY-NOTICES-v1.md` with name, version, source and license are also mandatory; if none is bundled, acceptance records `third_party_bundled=false`. The existing bounded `audit_release.py` remains a regression check but cannot alone certify the v1 ZIP. Source: REL-04 and `05-RESEARCH.md`.
- **D-08 — Release provenance is non-recursive and exact.** The reviewed merge commit is final SHA A. The SHA-P rehearsal sidecar has a distinct filename and can never be accepted as final evidence. Create the annotated tag locally on A, then run the tag-resolved clean-archive/CI proof exactly once to produce canonical `.local/release-evidence/v1.0.0-ci-reproducibility.json`; push the tag or publish nothing until that proof passes. The tag produces `Alma_OS_v1.0.0.zip`; a checksum sidecar records its SHA-256, and a separate ignored acceptance sidecar binds that ZIP hash, tag, A, same-A CI sidecar, native summary, Excel evidence, archive proof and gate results. Subsequent verification uses a read-only `--check-existing` path and cannot rewrite the bound sidecar. No tracked file records mutable CI URLs or its own future commit. The ZIP contains the runbook and an inner acceptance summary that does not claim its own outer ZIP hash. Its inner release manifest is generated only after all tracked payloads are final, lists and hashes every payload entry except the manifest itself, and is committed before A is frozen; the exact member set is `entries + {release-manifest.json}`, and the manifest bytes are bound only by the outer ZIP hash and external acceptance sidecar. All public business bytes are blank or explicitly synthetic. Source: REL-04 and `05-RESEARCH.md`.
- **D-09 — External gates remain explicit.** EXT-01 real client correctness/adoption stays `UNKNOWN`, EXT-02 fiscal/opening-bank policy stays `UNKNOWN`, and EXT-03 the Pilates-socks winner hypothesis stays `REVIEW` unless separate authorized observed evidence exists. A software release never upgrades those states. Source: `.planning/REQUIREMENTS.md`.
- **D-10 — Authority remains analytical.** The final package is a local Python/SQLite/CSV/JSON/XLSX/static-HTML system. Native recommendations remain advisory, `execution` stays `PROHIBITED`, and release automation performs no purchase, payment, refund, price change, publication or customer communication. Source: `.planning/PROJECT.md` and `AGENTS.md`.
- **D-11 — Rollback is portable and preserves private work.** Installations use versioned sibling extraction directories. The documented rollback verifies the prior ZIP/checksum, extracts it to a fresh prior-version directory, runs its offline smoke/help checks and resumes with an explicitly supplied private output root outside every package directory. Update, uninstall and rollback must never delete, move or overwrite `.local` or another user-selected private root. A disposable smoke test preserves a sentinel private cut byte-for-byte across update, rollback and uninstall. Source: REL-04 and the client operating boundary.

## The agent's Discretion

- Use the exact Phase 1–4 exports and final summary files at execution time. The proposed release modules may adapt names at their boundary, but acceptance must consume the canonical cut, mart, native-cycle, register, workbook, portal and package interfaces rather than duplicate business logic.
- Store complete live-native and temporary archive evidence below ignored `.local/` paths. Commit only sanitized machine-readable receipts, documentation, deterministic fixtures and public blank/synthetic evidence.
- Keep the current dependency pins. No new package install is planned; a later dependency change requires a package legitimacy audit before installation.

## Deferred Ideas

- Real private-cut owner walkthrough, adoption and business-impact claims remain EXT-01.
- Fiscal/tax treatment and opening-bank reconciliation remain EXT-02.
- A winner claim for multicolor Pilates socks remains EXT-03 until an eligible observed validation window exists.
- Storefront, CRM, ERP, hosted application, bank integration, paid inference provider and autonomous business execution remain out of scope.

## Phase 5 source coverage audit

| Source | Item | Plan | Status |
| --- | --- | --- | --- |
| GOAL | Reproducible, private, backward-compatible v1.0.0 supported by current two-week operational evidence | 05-01..03 | COVERED |
| REQ | REL-01 historical regression plus positive/partial/tamper/duplicate/double-count/two-week v1 acceptance | 05-01 | COVERED |
| REQ | REL-02 independent arithmetic and fresh Excel/visual evidence for changed books | 05-02 | COVERED |
| REQ | REL-03 clean Git archive and Windows/Ubuntu CI reproduction, including final SHA-A package commands | 05-02, 05-03 | COVERED |
| REQ | REL-04 versioned ZIP, checksum, acceptance evidence, runbook and privacy | 05-03 | COVERED |
| RESEARCH | Distinct two-cut scenario, replay control, closure and stale branches | 05-01 | COVERED |
| RESEARCH | Actual native analyst/reviewer receipts separate from fixtures | 05-01 | COVERED |
| RESEARCH | Exact cents/units oracle, unknown propagation and double-count controls | 05-01, 05-02 | COVERED |
| RESEARCH | Formula/layout change detection, desktop Excel, PDFs and byte binding | 05-02 | COVERED |
| RESEARCH | Clean committed archive, pinned install and two-OS matrix | 05-02 | COVERED |
| RESEARCH | Extracted ZIP allowlist, hashes, binaries, privacy and local links | 05-03 | COVERED |
| RESEARCH | Machine-readable acceptance keyed to commit and artifact SHA-256 | 05-01..03 | COVERED |
| RESEARCH | Preserve every v0.2/v0.3 gate and add atlas/v1 checks | 05-01, 05-02 | COVERED |
| CONTEXT | D-01 unified historical/v1 gate | 05-01 | COVERED |
| CONTEXT | D-02 truly distinct weeks and decision continuity | 05-01 | COVERED |
| CONTEXT | D-03 real native evidence and sanitized summary | 05-01 | COVERED |
| CONTEXT | D-04 independent exact oracle and canonical rebuild comparison | 05-01, 05-02 | COVERED |
| CONTEXT | D-05 fresh Excel evidence | 05-02 | COVERED |
| CONTEXT | D-06 clean archive, cross-platform CI and sole-file post-release commit B | 05-02, 05-03 | COVERED |
| CONTEXT | D-07 exhaustive extracted-package audit | 05-03 | COVERED |
| CONTEXT | D-08 distinct rehearsal P and exact final release provenance | 05-02, 05-03 | COVERED |
| CONTEXT | D-09 external gates remain unclaimed | 05-01..03 | COVERED |
| CONTEXT | D-10 local analytical authority boundary | 05-01..03 | COVERED |
| CONTEXT | D-11 portable rollback preserving private work | 05-03 | COVERED |

No source item is omitted. Phase 5 begins only after Phase 4 and consumes verified Phase 1–4 summaries. Missing live native, Excel, CI, archive, privacy or package evidence produces `BLOCKED`; it cannot be changed to PASS by documentation.
