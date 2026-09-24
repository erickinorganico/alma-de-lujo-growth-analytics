# Phase 5: Acceptance and v1.0.0 Release — Research

**Researched:** 2026-09-22  
**Domain:** Integrated analytical acceptance, offline packaging, release provenance  
**Confidence:** HIGH for existing gates and constraints; MEDIUM for the proposed v1 gate design, which depends on Phases 1–4

## User Constraints

No Phase 5 `CONTEXT.md` exists. The following governing constraints are copied from `.planning/PROJECT.md` and `.planning/REQUIREMENTS.md`; Phase 5 must preserve them. [VERIFIED: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`]

> - **Architecture**: Python 3.11+, SQLite, CSV/JSON/XLSX and offline HTML; no required server or paid inference provider.
> - **Money**: Integer MXN cents in relational data and Decimal at input boundaries; binary floats are prohibited for financial truth.
> - **Unknowns**: Missing, partial, zero, not applicable, estimated and error remain distinct.
> - **Privacy**: Public Git/release artifacts contain blank or synthetic data only; private cuts stay under ignored `.local/` paths.
> - **Agents**: Native Codex tasks provide interpretation; SQL/Python own exact calculations. A different agent reviews each analysis.
> - **Authority**: External business execution is always `PROHIBITED`.
> - **Compatibility**: Existing v0.2 and v0.3 evidence and release behavior remain regression protected.

The release goal is a reproducible, private, backward-compatible package supported by a current two-week operational proof. `REL-01` through `REL-04` are Phase 5 requirements. Real client correctness/adoption (`EXT-01`), fiscal/opening-bank policy (`EXT-02`), and the Pilates-socks winner claim (`EXT-03`) are external gates and stay UNKNOWN/REVIEW without separate observed evidence. [VERIFIED: `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`]

## Project Constraints (from AGENTS.md)

- Use `scripts/github-personal.ps1` for any GitHub CLI call; the target account is `erickinorganico`. Keep Git credentials and author repository-local, never switch global accounts, and do not publish `.local/`, `.local-archive/`, credentials, or real customer data. [VERIFIED: `AGENTS.md`, `docs/GITHUB-ACCESS.md`]
- The current `AGENTS.md` still routes Alma de Lujo cycles to historical `agents/RUN-NATIVE-CYCLE.md`, while the Phase 3 aggregate-v1 contract defines `agents/RUN-NATIVE-CYCLE-v1.md` and `agents/native-cycle-v1.roles.json`. Phase 5 must first update `AGENTS.md` so aggregate-v1 uses those v1 artifacts and the historical runbook remains v0.2 regression-only. The v1 route requires actual native execution, registered-query trace plus response/dispatch hash validation, and a distinct independent Astra reviewer whose frozen request binds all accepted analyst digests; deterministic scripts do not count as agent runs. [VERIFIED: current `AGENTS.md`, Phase 3 plans; RECOMMENDATION: Phase 5 routing update]
- Exact calculations belong in SQL/Python; preserve unknown coverage, temporal recognition, integer MXN cents, synthetic markers and source hashes. Recommendations need a primary metric, guardrail, population, window and closure rule. [VERIFIED: `AGENTS.md`]
- Keep the product a CLI/relational analytical system; do not add a frontend server, HTTP backend, storefront, CRM or ERP. No real customer data or external business execution is authorized by this analytical release. [VERIFIED: `AGENTS.md`, `.planning/PROJECT.md`]

<phase_requirements>

## Phase Requirements

| ID | Description (verbatim) | Research support |
|---|---|---|
| REL-01 | Existing v0.2/v0.3 regression suite remains green and v1 adds positive, partial, tamper, duplicate, double-count and two-week E2E tests. | Acceptance matrix, negative controls, preserved `verify_v2.py` and v0.3 gates below. [VERIFIED: `.planning/REQUIREMENTS.md`, `.github/workflows/verify.yml`] |
| REL-02 | Generated workbooks pass independent arithmetic checks and a fresh Excel-engine recalculation/visual inspection whenever formulas change. | Excel receipt and byte-binding workflow below. [VERIFIED: `.planning/REQUIREMENTS.md`, `scripts/verify_client_v3.py`, `scripts/recalculate_client_excel.ps1`] |
| REL-03 | Clean Git archive and GitHub Actions reproduce tests, build, source hashes, privacy audit and package link checks on Windows/Linux boundaries. | Clean-tree and two-OS CI gate below. [VERIFIED: `.planning/REQUIREMENTS.md`, `.github/workflows/verify.yml`] |
| REL-04 | A versioned v1.0.0 release contains the final offline package, checksum, acceptance evidence, runbook and no secrets/PII. | ZIP, checksum, manifest, audit, and evidence record below. [VERIFIED: `.planning/REQUIREMENTS.md`, `scripts/package_client.py`, `scripts/audit_release.py`] |

</phase_requirements>

## Summary

Use the v0.2 and v0.3 verifiers unchanged as regression gates, then add one v1 acceptance runner that creates two **different** synthetic weekly cuts in temporary private directories and checks the complete chain from source pack to reviewed decision and next-cut closure. An identical replay is a separate idempotence control; it cannot stand in for week two. Keep native execution evidence distinct from deterministic replay, including actual task IDs, request/response/registered-query-trace/dispatch hashes, a different reviewer identity, a reviewer request frozen over every analyst digest and a challenge disposition. [VERIFIED: `scripts/verify_v2.py`, Phase 3 v1 contracts, `.planning/ROADMAP.md`; RECOMMENDATION]

Build the final ZIP only from verified blank/synthetic files and a committed clean Git state. Test the *extracted* package, its local links, exact hashes, workbook bytes and offline behavior on Windows and Linux. Preserve the existing Excel receipt check in CI, while requiring a new desktop Excel recalculation and visual inspection if any delivered formula or rendering changes. Release evidence must say which gates actually ran and bind every result to the candidate commit and artifact SHA-256. [VERIFIED: `.github/workflows/verify.yml`, `scripts/package_client.py`, `scripts/verify_client_v3.py`, `docs/CLIENT-OPERATIONS-v3.md`; RECOMMENDATION]

Keep the inner release manifest non-recursive: generate it only after the runbook, release notes and tracked acceptance summary are final; its `entries` list covers every ZIP payload member except the manifest itself, and the auditor requires `member_set = entries + {release-manifest.json}`. Commit that final manifest with its payloads before freezing the release SHA. The manifest's own bytes are bound only by the outer ZIP SHA-256 and external acceptance sidecar; they never appear in their own preimage. [RECOMMENDATION]

**Primary recommendation:** Make a single fail-closed v1 release verifier produce a machine-readable acceptance record, and publish `v1.0.0` only from the exact commit and ZIP hashes recorded in that result. [RECOMMENDATION]

## Architectural Responsibility Map

| Capability | Primary tier | Secondary tier | Rationale |
|---|---|---|---|
| Two-week cut/decision proof | Local CLI/test runner | SQLite workspace | The CLI orchestrates immutable cuts and v1 native evidence; SQL owns exact facts and reconciliation. [VERIFIED: `.planning/PROJECT.md`, Phase 3 v1 contracts] |
| Arithmetic and event invariants | SQLite/Python | `unittest` | Existing analytical verifiers and workbook oracle use these boundaries. [VERIFIED: `scripts/verify_v2.py`, `alma/client_review.py`] |
| Client workbook check | Windows Excel | Python Decimal verifier | Excel calculates and saves bytes; Python compares cached outputs against independent arithmetic. [VERIFIED: `scripts/recalculate_client_excel.ps1`, `scripts/verify_client_v3.py`] |
| Offline portal/link check | Extracted static files | Python package test | The package has no server dependency; links must resolve relative to extracted files. [VERIFIED: `tests/test_client_system.py`, `scripts/package_client.py`] |
| Publication gate | Git archive/CI | ZIP manifest and audit | A commit identifies source, while the package manifest/checksum identifies shipped bytes. [CITED: https://git-scm.com/docs/git-archive; VERIFIED: `.github/workflows/verify.yml`, `scripts/package_client.py`] |

## Standard Stack

No new dependency is needed for Phase 5. Reuse the repository's pinned and installed components; this phase should not add an inference provider or service. [VERIFIED: `requirements-client.txt`, `.planning/PROJECT.md`, project `.venv` importlib metadata probe]

| Component | Verified local/pinned version | Purpose |
|---|---|---|
| Python standard library (`unittest`, `sqlite3`, `decimal`, `hashlib`, `zipfile`, `html.parser`) | Project `.venv`: Python 3.12.14; project floor 3.11+ | Tests, exact calculations, hashes, ZIP and local-link checks. [VERIFIED: `.planning/PROJECT.md`, `scripts/verify_v2.py`, `tests/test_client_system.py`, local version probe] |
| `openpyxl` | 3.1.5 pinned and installed | Inspect formula/cached XLSX cells and complete workbook content. [VERIFIED: `requirements-client.txt`, `scripts/verify_client_v3.py`, local importlib metadata probe] |
| `XlsxWriter` | 3.2.9 pinned and installed | Existing workbook generator; keep existing pin for regression. [VERIFIED: `requirements-client.txt`, `scripts/build_client_workbook.py`, local importlib metadata probe] |
| `et-xmlfile` | 2.0.0 pinned and installed | Existing client dependency pin. [VERIFIED: `requirements-client.txt`, local importlib metadata probe] |
| Git and GitHub Actions | Git 2.53.0.windows.1 locally; workflow uses Ubuntu runner and Python 3.12 | Archive and CI provenance. [VERIFIED: local version probe, `.github/workflows/verify.yml`] |
| Microsoft Excel desktop | COM registration `Excel.Application.16` detected locally; actual COM recalculation was **not** run in this research | Formula-change release gate on Windows. [VERIFIED: registry probe, `scripts/recalculate_client_excel.ps1`] |

**Package legitimacy audit:** Phase 5 recommends no new package and no changed dependency pin. Existing CI installs `requirements-client.txt`; if a plan changes that file, rerun registry, official-source and slopcheck checks before the install. This research did not perform those checks and does not claim package-registry approval. [VERIFIED: `.github/workflows/verify.yml`, `requirements-client.txt`; RECOMMENDATION]

## Architecture Patterns

### Acceptance flow

```text
synthetic week 1 pack -> validate/import -> canonical marts -> native analyst
         |                    |                  |                |
         |                    +-> source/hash/coverage controls        v
         |                                           distinct native reviewer
         |                                                    |
         |                                           reviewed decision register
         v                                                    |
synthetic week 2 pack -> validate/import -> changed cut/hash -> carry-forward
                                                              |
                                       closure evidence OR explicit stale flag
                                                              |
                         acceptance JSON -> CI/archive -> audited v1.0.0 ZIP
```

The weekly flow and its authority boundaries come from the Phase 3 contract; the final acceptance runner is a Phase 5 recommendation, not an existing command. [VERIFIED: `.planning/ROADMAP.md`, `.planning/phases/03-governed-weekly-decision-cycle/03-RESEARCH.md`; RECOMMENDATION]

### Exact two-week acceptance contract

1. Build week 1 and week 2 from distinct synthetic source packs, with different cutoff dates, cut IDs and source hashes. Assert both import, restore/export, relationship checks, source/mart lineage and required metrics pass. Use a week 1 valid decision with exact report/source hash, owner, due date, status, metric, guardrail, population, window and closure rule. [VERIFIED: `.planning/REQUIREMENTS.md`; RECOMMENDATION]
2. Dispatch real native analysis under `agents/RUN-NATIVE-CYCLE-v1.md` for the bound synthetic evidence and a **different** reviewer. Retain request, response, registered-query trace, actual task/dispatch receipt, frozen reviewer request, reviewer challenge, validated terminal packet and SHA-256 for each. A prepared request or synthetic replay alone is not live native analysis. [VERIFIED: Phase 3 v1 contracts, `.planning/REQUIREMENTS.md`]
3. Carry the reviewed decision to week 2 with its original anchor. Close it only when a week 2 evidence reference and closure rule validate; otherwise leave it open or mark stale using the due date. Test both the successful closure branch and the stale branch. Neither branch executes a business action. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/phases/03-governed-weekly-decision-cycle/03-RESEARCH.md`; RECOMMENDATION]
4. Independently compare source totals to every affected mart in integer cents/units and assert scope-specific unknown propagation. Verify a repeated exact week 1 import is idempotent, but the distinct week 2 cut changes the manifest hash. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/research/DOMAIN.md`; RECOMMENDATION]

### Negative controls and regression matrix

| Gate | Positive proof | Required negative control / expected failure |
|---|---|---|
| Intake/restore | Exact export/restore hashes, rows and relationships | Mutate source bytes or restored manifest; missing hash, malformed/PII column, broken relation and conflicting duplicate block publication. [VERIFIED: `.planning/REQUIREMENTS.md`, `tests/test_security.py`; RECOMMENDATION] |
| Money/stock | Source-to-mart cents and units reconcile at event grain | Same receipt plus inventory movement cannot add twice; same invoice/obligation/payment reference cannot multiply commitment or paid cash; repeated return/credit/refund remains distinct. [VERIFIED: `.planning/research/DOMAIN.md`, `docs/CLIENT-SYSTEM-ACCEPTANCE.md`; RECOMMENDATION] |
| Partial coverage | Known sum remains known, dependent complete cost/cash/margin becomes UNKNOWN; explicit zero remains zero | Remove cost component, settlement date, inventory movement coverage or eligible availability and assert no zero substitution, fabricated date, confident recommendation or stockout-as-weak-demand claim. [VERIFIED: `.planning/PROJECT.md`, `.planning/research/DOMAIN.md`; RECOMMENDATION] |
| Native evidence | Current-cut values and refs, distinct reviewer, terminal packet | Changed value, stale request/report hash, altered analyst after reviewer dispatch, identical reviewer identity, forged task receipt, journal/packet tamper, external action claim all fail closed. [VERIFIED: `tests/test_process_engine.py`, `.planning/phases/03-governed-weekly-decision-cycle/03-RESEARCH.md`; RECOMMENDATION] |
| Decision carry | Week 1 reviewed decision linked to week 2 closure/stale status | Duplicate decision ID, forged closure ref, changed prior anchor, absent owner/due date and CSV formula injection rejected. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/phases/03-governed-weekly-decision-cycle/03-RESEARCH.md`; RECOMMENDATION] |
| Offline release | Extracted ZIP opens, local links/hashes pass, no private data | Broken/escaping/external URL, hidden workbook value/comment/link/metadata, active Excel part, unlisted ZIP member, private cut/native response/secret marker or changed binary fails package gate. [VERIFIED: `tests/test_client_system.py`, `scripts/package_client.py`, `scripts/audit_release.py`; RECOMMENDATION] |

Keep these established checks in the Phase 5 matrix: `scripts/verify_v2.py` (the full `unittest` suite plus six scenarios and replay), `scripts/check_scope_v2.py` (published v0.2 native/scope evidence), `scripts/verify_client_v3.py check` (delivered workbook hashes/Decimal), `scripts/build_client_system.py --check` (atlas lineage/links), `scripts/package_client.py` (generated blank/synthetic package), and `scripts/audit_release.py` (bounded public scope audit). The current Ubuntu workflow runs all except the explicit atlas `--check`; the planner should add a CI step for it and any v1 equivalent. [VERIFIED: `.github/workflows/verify.yml`, `docs/CLIENT-SYSTEM-ACCEPTANCE.md`, listed scripts]

### Clean Git archive and CI gate

Resolve each proof ref once and use that same immutable SHA for its local archive plus Windows/Ubuntu jobs. Phase 5 may rehearse the flow on pre-merge SHA P, but after merge the reviewed commit becomes final **SHA A**; rerun the complete archive/CI proof for A and make no further tracked mutation before tagging. Use `git archive` of the proven SHA in a disposable directory, then run the build and checks there using documented dependencies. `git archive` excludes hidden untracked dependencies. Compare generated manifests, canonical source/mart exports and expected source hashes to that commit's receipts. Store live CI run/job URLs, conclusions and downloaded receipt hashes only in an ignored external sidecar keyed by the proven SHA; committing that mutable remote state would create commit B and invalidate same-commit proof. Do not require byte-identical freshly built SQLite database files: canonical data/exports/relationships and declared hashes are the contract. [CITED: https://git-scm.com/docs/git-archive; VERIFIED: `docs/RELEASE.md`; RECOMMENDATION]

Expand `.github/workflows/verify.yml` from its current one-job Ubuntu runner to Linux/Windows boundary checks. Both should run the deterministic suite, v1 synthetic acceptance, build, privacy/link and extracted-ZIP checks under Python 3.12. The Windows job may verify the committed Excel receipt and workbook bytes; do **not** label that as a new Excel run. Record each job's OS, Python version, commit SHA, command results and artifact hashes. GitHub documents matrix jobs for operating-system combinations and read-only token permissions. [VERIFIED: `.github/workflows/verify.yml`; CITED: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax, https://docs.github.com/en/actions/reference/security/secure-use; RECOMMENDATION]

### Excel evidence rule

For any delivered formula or rendered workbook change, regenerate synthetic adversarial probes, recalculate those and the blank/example deliverables in a **new** desktop Excel instance, save/normalize metadata, and record engine/version/build plus post-save SHA-256. Then run the independent v1 oracle against the exact delivered files and receipt. Export every nonempty print area for both delivered books, render every PDF page to an immutable PNG, inspect every PNG through the local visual tool, and record page index, PNG/PDF/workbook hashes and an honest clipping/legibility disposition. The verifier rejects missing, duplicate, unhashed or undisposed pages. Rebuild the ZIP after the final Excel save and verify its workbook member bytes match the receipt and release manifest. [VERIFIED: prior Excel procedure; RECOMMENDATION]

The historical v0.3 receipt records Excel 16.0 build 20326, two delivered workbook hashes, and six PDF names; historical acceptance reports 28 recalculated adversarial workbooks, 5,349 comparisons and six visually inspected PDFs. Those are baseline regression evidence only. CI validates recorded bytes and cached values without running Excel. Desktop Excel and an interactive Windows session remain a separate formula-change gate; no LibreOffice compatibility is established. [VERIFIED: `evidence/v0.3/excel/excel-recalculation.json`, `evidence/v0.3/workbook-checks.json`, `docs/CLIENT-SYSTEM-ACCEPTANCE.md`, `.planning/codebase/TESTING.md`]

## Don't Hand-Roll

| Problem | Use instead | Reason |
|---|---|---|
| Exact finance and inventory acceptance | Existing canonical SQL/Python plus an independent `Decimal` oracle | A package manifest or agent prose is not an arithmetic oracle; cents and event grain are governed in code. [VERIFIED: `AGENTS.md`, `scripts/verify_client_v3.py`, `.planning/PROJECT.md`] |
| XLSX formula execution | Desktop Excel via `scripts/recalculate_client_excel.ps1` | `openpyxl` reads formula/cache values but the current verification procedure explicitly delegates recalculation to Excel. [VERIFIED: `scripts/verify_client_v3.py`, `scripts/recalculate_client_excel.ps1`] |
| Native cognition/review | Actual v1 native Codex bridge, role contract and recorded dispatches/query traces | Prepared JSON or deterministic replay cannot prove an analyst or reviewer actually ran. [VERIFIED: Phase 3 v1 contracts] |
| ZIP/manifest hashing | `hashlib.sha256`, `zipfile`, package allowlist and existing audit | These standard-library primitives already underpin the repo's package and audit code. [VERIFIED: `scripts/package_client.py`, `scripts/audit_release.py`] |

## Common Pitfalls

- **Week-two theater:** Two files with the same cut identity or a replay of week 1 falsely satisfies the calendar story. Assert distinct cutoff/source/cut hashes and an anchored carry-forward event. [VERIFIED: `.planning/REQUIREMENTS.md`; RECOMMENDATION]
- **Duplicate money or units:** Joining invoice, obligation, payment, receipt and movement by SKU/date instead of unique event references can multiply values. Reconcile each layer independently and inject a duplicate into acceptance. [VERIFIED: `.planning/research/DOMAIN.md`, `.planning/codebase/CONCERNS.md`; RECOMMENDATION]
- **Green CI mistaken for new Excel evidence:** Ubuntu currently checks a historical receipt. Require a fresh Excel/PDF receipt after formula or rendering changes, then bind hashes to package bytes. [VERIFIED: `.github/workflows/verify.yml`, `docs/CLIENT-OPERATIONS-v3.md`]
- **Audit blind spots:** `audit_release.py` skips `.png`, `.pdf`, `.gif`, `.zip` by suffix and only pattern-scans text plus approved XLSX/SQLite. That bounded audit cannot alone certify a new v1 ZIP or arbitrary PII. Scan ZIP membership/content using a public allowlist and inspect all newly published binary assets before release. [VERIFIED: `scripts/audit_release.py`; RECOMMENDATION]
- **Development checkout contamination:** Existing packaging reads repository files and writes `client/release-manifest.json` and a ZIP under `.local/releases`; a clean archive proves the package has no hidden untracked dependency. [VERIFIED: `scripts/package_client.py`; CITED: https://git-scm.com/docs/git-archive]
- **Historical synthetic evidence misread as current/real:** Label demo and current synthetic cut separately, keep native responses private, and retain `EXT-01..03` as external unknowns. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/codebase/CONCERNS.md`]

## Code Examples

The following is a *planning pattern*, not an existing v1 CLI command. Use the final Phase 1–4 interfaces and report schema when implementing it. [RECOMMENDATION]

```python
from hashlib import sha256

assert week_1.cut_id != week_2.cut_id
assert week_1.cutoff < week_2.cutoff
assert week_1.source_hashes != week_2.source_hashes
assert sha256(week_1.report_bytes).hexdigest() == decision.source_report_sha256
assert decision.decision_id in week_2.carried_decision_ids
assert week_2.closure_status in {"CLOSED_WITH_EVIDENCE", "STALE"}
assert analyst.task_id != reviewer.task_id
assert all(control.passed for control in reconciliations)
```

Record each gate with `status=PASS/FAIL/BLOCKED`, input commit/hash, artifact hash, evidence path, limits, and time; missing native/Excel/cross-platform evidence is `BLOCKED`, never inferred from a successful script. This follows existing v0.2 scope handling and is the proposed v1 release record shape. [VERIFIED: `scripts/check_scope_v2.py`, `.planning/REQUIREMENTS.md`; RECOMMENDATION]

## State of the Art and Current Limits

| Existing state (2026-09-22) | Phase 5 consequence |
|---|---|
| The project has a committed v0.2 synthetic warehouse and v0.3 client ZIP checks, but Phases 1–4 of v1 are pending. [VERIFIED: `.planning/ROADMAP.md`, `.planning/codebase/CONCERNS.md`] | Plan Phase 5 against delivered Phase 1–4 contracts; do not claim current two-week proof. [RECOMMENDATION] |
| CI is Ubuntu-only, 15 minutes, Python 3.12, with full v0.2 verifier and recorded Excel receipt check. [VERIFIED: `.github/workflows/verify.yml`] | Add Windows boundary and v1 acceptance while retaining every existing gate. [RECOMMENDATION] |
| Local project Python is 3.12.14; global `python` shim has no selected version; the `.venv` has required client packages but no `pip` module. [VERIFIED: local probes] | Use the project interpreter locally and a fresh CI Python/install in archive tests; record any environment setup failure. [RECOMMENDATION] |
| Excel COM is registered as `Excel.Application.16`, but no live recalculation was attempted in this research. [VERIFIED: registry probe] | Treat Excel execution as unverified until a new receipt from an actual interactive run. [RECOMMENDATION] |

## Environment Availability

| Dependency | Required by | Availability | Fallback |
|---|---|---|---|
| Project Python | All local checks | `.venv/Scripts/python.exe` 3.12.14 works; global shim unavailable. [VERIFIED: local probe] | Use explicit `.venv` locally; Actions `setup-python` in CI. [VERIFIED: `.github/workflows/verify.yml`] |
| Client XLSX libraries | Workbook checks/build | All three pinned modules import from `.venv`; `pip` module is absent there. [VERIFIED: importlib metadata and pip probes] | CI installs pins; do not require local reinstall for research. [VERIFIED: `.github/workflows/verify.yml`] |
| Git / GitHub CLI | Archive/CI evidence | Git 2.53.0.windows.1 and `gh` 2.87.3 available. [VERIFIED: local probe] | Use Git locally; route any GitHub CLI action through project wrapper. [VERIFIED: `AGENTS.md`] |
| Desktop Excel | Formula-change gate | COM registration exists; actual session/start not verified. [VERIFIED: registry probe] | If unavailable, formula-changing release remains BLOCKED; existing receipt can support unchanged delivered bytes only. [VERIFIED: `docs/CLIENT-OPERATIONS-v3.md`; RECOMMENDATION] |
| Native Codex runtime | Live analyst/reviewer proof | Available to the orchestrating Codex workflow, not callable by deterministic Python alone. [VERIFIED: Phase 3 v1 contracts] | Keep `WAITING_AGENT`/`BLOCKED` until real v1 dispatch, trace and review evidence exists. [VERIFIED: Phase 3 v1 contracts] |

## Validation Architecture

| Property | Value |
|---|---|
| Framework | Python stdlib `unittest`; no separate test config. [VERIFIED: `.planning/codebase/TESTING.md`] |
| Existing quick run | `.venv/Scripts/python.exe -m unittest tests.test_client_review tests.test_client_system tests.test_process_engine -q` on this Windows machine. [VERIFIED: test modules and local interpreter probe] |
| Existing full run | `.venv/Scripts/python.exe scripts/verify_v2.py --output build/verification-v2` on Windows; `python scripts/verify_v2.py --output build/ci-verification` in Actions. [VERIFIED: `scripts/verify_v2.py`, `.github/workflows/verify.yml`] |

| Requirement | Test type and essential command | Wave 0 gap |
|---|---|---|
| REL-01 | New `unittest` integration and adversarial tests, e.g. `python -m unittest tests.test_v1_release_acceptance -q`; full `verify_v2.py` regression. [RECOMMENDATION] | `tests/test_v1_release_acceptance.py` and synthetic two-cut fixtures/expected cent/unit totals need Phase 1–4 interfaces. [VERIFIED: `.planning/ROADMAP.md`; RECOMMENDATION] |
| REL-02 | `python scripts/verify_client_v3.py check ...` against final workbook/receipt; Windows Excel recalculation plus PDF visual record when changed. [VERIFIED: `docs/CLIENT-OPERATIONS-v3.md`] | Adapt oracle to new v1 books/formulas; define exact changed-formula detection and visual receipt. [RECOMMENDATION] |
| REL-03 | Archive/extract smoke test and Windows/Ubuntu CI matrix; inspect CI job logs and SHA-256 receipts. [CITED: https://git-scm.com/docs/git-archive, https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax; RECOMMENDATION] | New `tests/test_release_archive.py` and CI matrix. [RECOMMENDATION] |
| REL-04 | Build ZIP, verify checksum and entry allowlist, extract and resolve every local link, compare member hashes, run privacy audit. [VERIFIED: `scripts/package_client.py`, `tests/test_client_system.py`; RECOMMENDATION] | Versioned release manifest/acceptance JSON/runbook and extracted-package test. [RECOMMENDATION] |

**Sampling:** Run affected quick tests after a task; full regression plus v1 acceptance per wave; clean archive, both CI OS jobs, Excel gate when triggered, extracted ZIP/hash/privacy/links and reviewed release record at the phase gate. [RECOMMENDATION]

## Security Domain

OWASP ASVS 5.0 is web-application guidance; apply its relevant validation, file and data-protection controls to the local CLI/package boundary without implying that this project has an HTTP auth/session surface. [CITED: https://github.com/OWASP/ASVS/blob/master/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json; VERIFIED: `.planning/PROJECT.md`]

| ASVS 5.0 category | Applies | Release control |
|---|---|---|
| V1 Encoding/Sanitization | Yes | Reject spreadsheet formula injection in CSV fields; escape private report HTML. [CITED: https://github.com/OWASP/ASVS/blob/master/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.flat.json; VERIFIED: `tests/test_client_review.py`] |
| V2 Validation/Business Logic | Yes | Strict source schema, event uniqueness, atomic failures, no duplicate money/stock and governed review transitions. [CITED: https://github.com/OWASP/ASVS/blob/master/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json; VERIFIED: `.planning/REQUIREMENTS.md`] |
| V5 File Handling | Yes | Validate XLSX/ZIP entry types, sizes, paths, count, members and generated content before accepting/publishing. [CITED: https://github.com/OWASP/ASVS/blob/master/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.flat.json; VERIFIED: `scripts/package_client.py`, `scripts/audit_release.py`] |
| V14 Data Protection | Yes | Public allowlist, synthetic-only content, private `.local/` cuts and outputs, no external resources. [CITED: https://github.com/OWASP/ASVS/blob/master/5.0/en/0x23-V14-Data-Protection.md; VERIFIED: `AGENTS.md`, `.gitignore`, `tests/test_client_system.py`] |
| V6 Authentication / V7 Session / V8 Authorization | No app login/session or public API in this phase | Retain local GitHub credential isolation and business-action prohibition; do not invent web auth. [VERIFIED: `.planning/PROJECT.md`, `AGENTS.md`] |

## Release Evidence Required for Final

Produce a reviewable acceptance record keyed by frozen candidate SHA A and release ZIP SHA-256, with: exact test/CI commands and results on Windows/Linux; week 1/2 input hashes and cut IDs; source/mart reconciliation receipts; actual native analyst/reviewer task, response, query-trace and dispatch hashes; closure or stale evidence; negative-control outcomes; workbook oracle/Excel/PDF/rendered-page hashes; clean-archive build results; package member allowlist/hash and local-link audit; privacy audit with its limits; runbook and versioned checksum. Keep mutable remote CI metadata in the ignored same-SHA sidecar and bind its hash into the external release acceptance sidecar. Mark unavailable gates BLOCKED, and retain external `EXT-01..03` as UNKNOWN/REVIEW. The package contains only reviewed public blank/synthetic artifacts; private workspaces, filled books, native responses and credentials remain out of it. [VERIFIED: `.planning/REQUIREMENTS.md`, `AGENTS.md`, Phase 3 v1 contracts; RECOMMENDATION]

## Assumptions Log

| # | Claim | Risk if wrong |
|---|---|---|
| A1 | The final Phase 1–4 CLI can expose a stable cut ID, source hashes, mart reconciliation and decision carry-forward to a Phase 5 runner. [ASSUMED] | Acceptance adapter may need a small CLI/JSON export task before tests. |
| A2 | New v1 workbook domains can be checked by extending the current Decimal/Excel procedure without a separate spreadsheet engine. [ASSUMED] | Planner may need a new oracle mapping and receipt schema. |

## Open Questions (RESOLVED)

1. **Phase 1–4 command and schema names — RESOLVED:** each Phase 5 executor reads the completed upstream summaries first and binds only their final exported interfaces. For the native boundary this explicitly means updating `AGENTS.md` before live work so aggregate-v1 routes to `agents/RUN-NATIVE-CYCLE-v1.md`, `agents/native-cycle-v1.roles.json` and `scripts/run_weekly_cycle.py`; historical interfaces remain regression-only.
2. **Workbook-change trigger — RESOLVED:** D-05 classifies both v1 operational workbooks as a changed delivery surface. Fresh desktop Excel recalculation, independent arithmetic and complete rendered-page inspection are mandatory regardless of similarity to v0.3 hashes.
3. **CI duration — RESOLVED:** measure the clean archive and both matrix jobs for frozen SHA A, set an explicit justified Actions timeout above the observed duration, and retain every historical/v1, hash, privacy, package and link gate. A timeout is BLOCKED and never authorizes removing a check.

## Sources

**Primary project evidence:** `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`, `AGENTS.md`, Phase 3 v1 plans/contracts, `docs/CLIENT-SYSTEM-ACCEPTANCE.md`, `docs/CLIENT-OPERATIONS-v3.md`, `.github/workflows/verify.yml`, `scripts/verify_v2.py`, `scripts/check_scope_v2.py`, `scripts/verify_client_v3.py`, `scripts/recalculate_client_excel.ps1`, `scripts/package_client.py`, `scripts/audit_release.py`, `tests/test_client_system.py`, `tests/test_client_review.py`, `tests/test_process_engine.py`, `evidence/v0.3/excel/excel-recalculation.json`. [VERIFIED: codebase inspection]

**Official external references:** [Git archive](https://git-scm.com/docs/git-archive), [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use), [OWASP ASVS 5.0 JSON](https://github.com/OWASP/ASVS/blob/master/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json), [OWASP ASVS V14](https://github.com/OWASP/ASVS/blob/master/5.0/en/0x23-V14-Data-Protection.md). [CITED: linked official sources]

## Metadata

**Confidence breakdown:** Existing stack/regression gates HIGH (direct code and receipt inspection); v1 architecture MEDIUM (requirements are locked, implementation pending); pitfalls HIGH (documented code paths and adversarial tests); two-week fixture shape MEDIUM (final CLI/schema pending).  
**Research date:** 2026-09-22  
**Valid until:** Recheck after Phases 1–4 implementation or 2026-10-06, whichever comes first. [RECOMMENDATION]
