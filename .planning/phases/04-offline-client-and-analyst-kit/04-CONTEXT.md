# Phase 4 Context — Offline Client and Analyst Kit

## Source and status

This context transcribes binding Phase 4 requirements from `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `04-UI-SPEC.md`, `AGENTS.md`, and the Phase 3 research. There was no Phase 4 discussion `CONTEXT.md` before planning. The identifiers below trace source contracts; they do not claim an additional owner decision. The UI specification was approved and then revised on 2026-09-23 to close plan-review gaps in continuation, parity, visual evidence and spreadsheet support boundaries.

## Decisions

- **D-01 — Complete contract-driven input.** The generated blank and synthetic-example workbook/source pack must cover every relation in the final Phase 1 v1 registry exactly once, with exact ordered import headers, grain, keys, units, provenance, coverage and version. The client kit also includes a separate versioned operating-metrics policy template in unapproved `REVIEW` state and a verified synthetic policy example; neither policy is counted as one of the 22 Phase 1 source relations. The XLSX is an editing surface; its adapter must first export the validated canonical CSV source pack, and that pack plus the immutable cut remain authoritative. Blank stays distinct from zero. An independent workbook→pack→manifest oracle covers all 22 relations, and a relation-by-relation omission suite proves the requiredness/completeness matrix. Desktop Excel is the supported spreadsheet engine; canonical CSV packs are the reader-neutral fallback, and no unexecuted third-party spreadsheet engine is claimed compatible. Source: CLIENT-01, the Phase 2 policy contract and `04-UI-SPEC.md`.
- **D-02 — Truthful offline portal.** Generate one static, local-file portal and a separate private current-cut instance under `.local/`. Show historical synthetic v0.2 and selected current-cut provenance as distinct dimensions. Derive status, dates, hashes, metrics, packets, exceptions and lineage from verified manifests and Phase 2–3 artifacts. Waiting native work stays waiting. A separate mart→portal→CSV→JSON oracle proves zero/unknown/partial/review/blocked, integer-cent and source-hash parity, while a hash-bound real-browser receipt owns desktop, narrow and print acceptance. Source: CLIENT-02 and `04-UI-SPEC.md`.
- **D-03 — One supported weekly launcher.** Document and implement `.\run.ps1 weekly --source-pack <filled-pack-or-workbook> --policy <policy.json> --output-root .local/client-runs [--prior-register <register-dir> --prior-anchor <anchor.json>]` from the repository root. A workbook input is converted first to the canonical source pack; the system derives the immutable `cut_id` and writes its child directory under `--output-root`. The two prior-cycle inputs are optional as a pair and are independently verified before carry-forward. The creation command validates/builds the cut, computes marts and report, prepares hash-bound native tasks, writes progress receipts and the private run index, and packages the public kit. After WAITING, the same launcher exposes `.\run.ps1 weekly-resume --run <private-run-dir> --action <record|submit|resume|packet|register>` with the exact action-specific evidence flags in the UI specification; it maps directly to Phase 3 and never rewrites earlier receipts. Restart is proven from a clean committed checkout with the ignored private run supplied explicitly, not from the client ZIP. It may advance analysis/review only through actual native task dispatch and accepted receipts, and register only an explicit owner decision event. Source: CLIENT-03, the Phase 1–3 command contracts, `04-UI-SPEC.md`, Phase 3 research and `agents/RUN-NATIVE-CYCLE.md`.
- **D-04 — Sanitized distribution.** A reproducible informational/synthetic client ZIP contains offline portal and local evidence, blank/example workbooks and source packs, an unapproved `REVIEW` policy template, a verified synthetic policy example, dictionary, guide, example decision walkthrough and path/hash manifest. It binds the Phase 4 workbook-parity and portal-visual receipt hashes as verification inputs but contains no analyst runtime. Private filled cuts, approved/private policy instances, current reports, native requests/responses/traces, register events, owner approval references, `.local/`, credentials and PII never enter the public package. Source: CLIENT-04, `04-UI-SPEC.md` and `AGENTS.md`.
- **D-05 — Existing product architecture.** Keep Python 3.11+, SQLite, CSV/JSON/XLSX and static HTML. Use existing pinned workbook libraries and v0.3 patterns; add no server, JavaScript framework, login, remote asset, new inference provider or external business executor. Preserve v0.2/v0.3 release outputs and regression behavior. Source: `.planning/PROJECT.md`, `AGENTS.md`, `04-UI-SPEC.md`.

## The agent's Discretion

- Exact v1 generator/adapter module names and generated filenames may follow implemented Phase 1–3 exports. Plans name proposed ownership and require verification against actual upstream interfaces before editing; a mismatch is resolved by using the final versioned contract, never by inventing rows or fake responses.
- Use native HTML controls and a small optional search script; critical content and navigation must work without JavaScript. Use Python `unittest`, temporary synthetic fixtures and the existing workbook toolchain.

## Deferred Ideas

- Real client-data correctness, owner adoption, fiscal/tax policy and validation of the Pilates-socks winner hypothesis remain EXT-01..03 external gates.
- Storefront, CRM, ERP, hosted web application, bank integration and autonomous business execution are out of scope.

## Phase 4 source coverage audit

| Source | Item | Plan | Status |
| --- | --- | --- | --- |
| GOAL | Client prepares a cut offline; analyst navigates, runs and packages the local workflow | 04-01..03 | COVERED |
| REQ | CLIENT-01 complete usable blank/example workbooks | 04-01 | COVERED |
| REQ | CLIENT-02 provenance-safe offline portal | 04-02 | COVERED |
| REQ | CLIENT-03 one-command weekly workflow | 04-03 | COVERED |
| REQ | CLIENT-04 sanitized offline client package | 04-03 | COVERED |
| RESEARCH | Phase 3 exact manifest/report hashes and v1 adapter, real native dispatch, distinct review, owner-controlled register | 04-02, 04-03 | COVERED |
| CONTEXT | D-01 complete registry-driven workbook, 22-relation omission matrix and workbook→pack→manifest oracle | 04-01 | COVERED |
| CONTEXT | D-02 provenance-safe static portal, mart→portal→CSV→JSON oracle, all eight sections and hash-bound visual evidence | 04-02 | COVERED |
| CONTEXT | D-03 creation plus exact weekly-resume record/submit/resume/packet/register continuation | 04-03 | COVERED |
| CONTEXT | D-04 public/private package separation | 04-03 | COVERED |
| CONTEXT | D-05 local architecture and backwards compatibility | 04-01..03 | COVERED |
| UI SPEC | Workbook usability, Spanish copy, semantic keyboard/print design, provenance badges, link and ZIP checks | 04-01..03 | COVERED |

Phase 4 consumes Phase 1–3 deliverables; those phases were unimplemented when this context was written. Execution starts only after those plans have produced their verified interfaces. No current-cut portal or owner-ready packet may be built from a mere prepared native request.
