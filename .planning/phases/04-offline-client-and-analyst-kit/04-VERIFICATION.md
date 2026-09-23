---
phase: 04-offline-client-and-analyst-kit
verified: 2026-09-23T23:39:23Z
status: gaps_found
score: 14/15 must-haves verified
overrides_applied: 0
gaps:
  - truth: "An analyst can follow one documented command path to initialize, validate, build, review, carry forward, and package a weekly cut without a server."
    status: failed
    reason: "The weekly command prepares a private cut through WAITING and weekly-resume exposes the five continuation actions, but neither command invokes the public kit builder or records a package stage. The analyst guide requires a separate direct Python package command, so the roadmap's integrated package step has no executable link or immutable run receipt."
    artifacts:
      - path: "alma/weekly.py"
        issue: "No import or call to build_client_kit; run-index receipts stop at source, workspace, marts, and native-waiting."
      - path: "run.ps1"
        issue: "Routes weekly and weekly-resume only; no package action is connected to the weekly run."
      - path: "docs/ANALYST-WEEKLY-v1.md"
        issue: "Documents `python scripts/package_client_v1.py` as a separate command rather than a receipted stage of the supported weekly path."
    missing:
      - "Invoke the sanitized public package builder from the supported weekly path independently of private review status."
      - "Record the package path, SHA-256, manifest hash and audit disposition in an immutable stage receipt/run index."
      - "Prove the integrated package stage from a clean checkout without copying private/native content."
deferred:
  - truth: "A self-consistently tampered allowed ZIP member containing PII-like or secret-like content must be rejected even when its package-manifest entry is rehashed."
    addressed_in: "Phase 5 Plan 05-03"
    evidence: "05-03 requires scripts/audit_release_v1.py to scan text/XML, binaries, workbook surfaces, secrets and PII-like content and to reject altered payloads before publication."
---

# Phase 4: Offline Client and Analyst Kit Verification Report

**Phase Goal:** A client can prepare a cut offline and an analyst can navigate, run, and package the full local weekly workflow.
**Verified:** 2026-09-23T23:39:23Z
**Status:** gaps_found
**Re-verification:** No - initial independent verification
**Commit verified:** `736b20f5e5456f4a1a980fad09e744e2360c607b`

## Goal Achievement

### Observable Truths

The roadmap criteria and all three PLAN frontmatters were merged. Roadmap criteria already restated by a more specific PLAN truth were counted once; the roadmap's integrated package-stage outcome remains a separate truth because no PLAN truth fully restates it.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Blank and visibly synthetic workbooks expose every registry relation exactly once with readable instructions and validation. | VERIFIED | Fresh generation and `OperatingWorkbookGenerationTests` confirm 22 ordered relations, support sheets, validation, print setup and distinct blank/synthetic markers. |
| 2 | Edited workbook rows export to a Phase 1-valid canonical pack while blank/null remains distinct from measured zero. | VERIFIED | `export_workbook_to_pack()` inspects the archive and surfaces, parses through `alma.operating_interchange.parse_pack`, writes atomically and records per-relation null/zero counts. |
| 3 | An independent workbook -> pack -> manifest oracle proves relation, row, null/zero, integer-cent, unit and source-hash parity for all 22 relations. | VERIFIED | Rebuilt synthetic workbook hash matches the receipt; `workbook-pack-parity.json` is PASS with 22/22 unique ordered relations, all dispositions PASS, observed nulls and observed zeros. |
| 4 | REVIEW and SYNTHETIC_EXAMPLE policy materials remain separate from the 22 source relations and make no owner-approval claim. | VERIFIED | Both versioned policy files validate; generator rejects APPROVED/owner-referenced public policies and the package inventories them outside `FUENTES/source-packs`. |
| 5 | Workbook failures identify sheet, row, field, issue and correction without mutating the submitted workbook. | VERIFIED | `WorkbookContractError` receives those fields through `_fail()`/`_upstream_error()`; the adapter rehashes the original before atomic publication and adversarial tests pass. |
| 6 | The complete public portal opens through `file://` and presents historical synthetic evidence first. | VERIFIED | `collect_portal_model(mode="public")` refuses private selections; the fresh public portal exactly matches all seven rendered-file hashes in the visual receipt. |
| 7 | A selected private cut exposes only its verified provenance, metrics, exceptions, packet, decisions and lineage. | VERIFIED | `_current_model()` calls `verify_cycle()`, verifies cut/status identity and reads current report/state/packet/register hashes only from an ignored `.local` path. |
| 8 | Missing, stale, blocked or waiting native evidence is labelled and never presented as owner approval or measured zero. | VERIFIED | Private portal projection emits `ESPERANDO_RESPUESTA`, `WAITING_ANALYSTS`, REVIEW/BLOCKED/UNKNOWN states and keeps the owner-decision stage pending/advisory. |
| 9 | Mart -> portal -> CSV -> JSON parity preserves IDs, values, cents, units, hashes and all boundary states. | VERIFIED | Boundary oracle passes with exact zero, null, 123456789 cents and MEASURED/UNKNOWN/PARTIAL/REVIEW/BLOCKED states across model, CSV and JSON. |
| 10 | Browser evidence binds public and safe synthetic-current desktop, 390px and every print surface to exact hashes. | VERIFIED | Independent rehash: 65/65 unique members present, 0 missing, 0 mismatched, 0 unexpected. Desktop/narrow captures and contact sheets covering all 11 public plus 48 current print pages were inspected without clipped provenance, warnings or tables. |
| 11 | `run.ps1 weekly` adapts workbook or pack input, validates policy and derives a new immutable private cut child. | VERIFIED | `create_weekly_run()` uses the workbook adapter/Phase 1 intake/Phase 2 marts/Phase 3 cycle, derives `cut_id`, requires `.local/client-runs`, refuses overwrite and returns WAITING_ANALYSTS. |
| 12 | Native analysis/review remains waiting until accepted dispatch/response evidence advances it. | VERIFIED | New runs write `native_execution_claimed=false`; record/submit delegate to the Phase 3 validators and tests cover all analytical roles plus a distinct reviewer. |
| 13 | A new process can continue through record, submit, resume, packet and register without rewriting initial receipts. | VERIFIED | Action grammar and wiring are explicit in `continue_weekly_run()`; current tests exercise all five actions and a separate clean `git archive` process resumes the restored private run with byte-identical initial receipts. |
| 14 | The public ZIP opens offline with guide, dictionary, complete blank/example inputs, policies and demo portal, with no private cut, native response or analyst runtime. | VERIFIED | Fresh build: PASS, 63 exact members, SHA-256 `f772b3fb4e5b73dfc5de35a7ae346c5604faa0f5eb5ca6b381f2d464097fa7bb`; all manifest hashes and links validate and no private/native/runtime member name is present. |
| 15 | The documented weekly command path also packages the cut through a receipted stage. | FAILED | `weekly.py` never calls `build_client_kit`; `run.ps1` has no package action; the run index has no package receipt; the runbook sends the analyst to a separate Python command. |

**Score:** 14/15 truths verified

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|--------------|----------|
| 1 | Self-consistent PII/secret injection into an allowlisted ZIP member is accepted by the Phase 4 auditor. | Phase 5 Plan 05-03 | Its Task 1 explicitly owns an exhaustive extracted-ZIP auditor with PII/secret scanning, binary/workbook inspection and tamper fixtures. The probe changed an allowlisted synthetic CSV `source_ref` to an email, rehashed its manifest entry, and `audit_client_zip()` incorrectly returned privacy PASS; this cannot satisfy final release privacy but is specifically contracted later. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/build_operating_workbooks.py` | Registry-driven workbooks/packs | VERIFIED | 512 lines; imports authoritative contracts; freshly regenerated deterministic bytes. |
| `alma/operating_workbook.py` | Safe workbook adapter | VERIFIED | 379 lines; substantive archive/surface/value validation, upstream parsing and atomic publication. |
| `client/v1/policies/*.json` | Separate public-safe policy materials | VERIFIED | REVIEW and SYNTHETIC_EXAMPLE validate with no approval reference. |
| `evidence/v1.0/workbooks/workbook-pack-parity.json` | 22-relation parity receipt | VERIFIED | Safe canonical receipt, PASS 22/22, no cell values or absolute paths. |
| `scripts/build_offline_portal_v1.py` | Verified public/private static portal | VERIFIED | 550 lines; private path/cycle/register verification and exact model/export/render path. |
| `client/portal-v1.css` | Responsive, keyboard and print presentation | VERIFIED | Focus-visible, wrapping, narrow and print contracts; inspected final captures. |
| `evidence/v1.0/portal/portal-visual-inspection.json` | Hash-bound browser inventory | VERIFIED | PASS receipt; exact Edge version, viewports, 59 reviewed print pages and 65-member bounded inventory. |
| `run.ps1` | Supported weekly/continuation launcher | PARTIAL | Exact weekly and five-action continuation interface works, but no integrated package stage. |
| `alma/weekly.py` | Immutable local orchestration | PARTIAL | Intake, marts, cycle, carry and continuation are wired; package generation/receipt is absent. |
| `scripts/package_client_v1.py` | Deterministic public kit and audit | VERIFIED for Phase 4 output | Fresh exact allowlisted build and normal audit pass. Deep content-tamper detection is deferred to the Phase 5 release auditor. |
| `client/v1/EMPIEZA_AQUI.md` / `GUIA_SEMANAL.html` | Client offline journey | VERIFIED | Source-first Spanish instructions, local relative links and public/private boundary present in actual packaged bytes. |
| `docs/ANALYST-WEEKLY-v1.md` | Analyst operation path | PARTIAL | Creation/continuation commands are exact, but packaging is documented as a detached Python command. |
| Phase 4 tests | Behavioral controls | VERIFIED | 27/27 focused tests plus 46/46 package/privacy regression tests passed on the verified commit. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| Workbook generator | Operating contracts | `SOURCE_NAMES`/`SOURCES` | WIRED | All 22 relations and fields derive from the authoritative registry. |
| Workbook adapter | Phase 1 interchange | `parse_pack()` | WIRED | Export is accepted only after whole-pack validation. |
| Workbook tests | Workbook, CSV pack, manifest | Independent direct cell/CSV/hash reads | WIRED | Receipt rebuilt and hash-matched. |
| Portal | Phase 1 cut | `verify_cycle()` plus report/state identity | WIRED | Changed report/path escape tests fail closed. |
| Portal | Phase 2 report/metric registry | report metric rows/definitions and source hashes | WIRED | Values flow to view model and exports. |
| Portal | Phase 3 packet/register | `verify_cycle()` / `verify_register()` | WIRED | Waiting, review, packet and decision states remain distinct. |
| Portal tests | Model/CSV/JSON | Independent boundary fixture | WIRED | Five measurement/authority states retain values and hashes. |
| Visual receipt | HTML/CSS/screens/PDF/pages | SHA-256 inventory | WIRED | 65/65 current artifacts rehash. |
| `run.ps1` | `alma.weekly` | `python -m alma.weekly` | WIRED | Exit status is preserved and help shows exact flags/actions. |
| `alma.weekly` | Phase 1-3 runtime | Direct intake/mart/cycle/register functions | WIRED | Current synthetic cut reaches immutable WAITING state and validated continuation. |
| Package builder | Workbook + public portal builders | Fresh generation and explicit allowlist | WIRED | 63-member ZIP is reproducible and link/hash audited. |
| Weekly run | Package builder | Expected receipted package stage | NOT_WIRED | No import, call, action or run-index package receipt exists. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| Operating workbook | relation sheets and source packs | Authoritative 22-relation registry plus blank/synthetic fixture rows | Yes, explicit blank or synthetic only | FLOWING |
| Private portal | cut/source/metric/native/decision model | Verified Phase 1 manifest, Phase 2 report, Phase 3 cycle/packet/register | Yes; current cut never falls back to demo | FLOWING |
| Public portal | historical demo model | Declared synthetic historical evidence | Intentional synthetic public data | FLOWING |
| Weekly run | run index, receipts, current cut and task bundle | Workbook/pack -> Phase 1 workspace -> Phase 2 marts -> Phase 3 cycle | Yes, private local cut; new run stops honestly at WAITING | FLOWING |
| Client ZIP | workbook, packs, portal, dictionary, guides | Fresh public generators plus accepted receipt hashes | Yes, blank/synthetic public material | FLOWING |
| Weekly package receipt | package path/hash/audit disposition | No source/call | No | DISCONNECTED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All Phase 4 focused contracts | `python -m unittest` over 7 declared test classes | 27 tests in 96.355s | PASS |
| Package/privacy compatibility | Declared package/privacy regression command | 46 tests in 3.618s | PASS |
| Publishable-tree audit | `python scripts/audit_release.py` | 542 files, 0 findings, license present | PASS |
| Workbook/portal bytes still match receipts | Fresh temp rebuild and direct SHA comparison | Workbook match; 7/7 public portal files match | PASS |
| Exact launcher surface | `run.ps1 weekly --help` and `weekly-resume --help` | Required flags and 5-action enum present | PASS |
| Fresh client package | Build, audit, extract and inventory | PASS, 63 members, all hashes/links exact | PASS |
| Allowed-member privacy mutation | Inject email/secret into allowed member, update its manifest hash, rerun audit | Incorrectly returned privacy PASS | DEFERRED TO 05-03 |
| Full repository suite | Not rerun | Current phase-scoped verification already ran 73 current tests plus release audit; no unrelated tracked changes were present | SKIP |

### Probe Execution

No Phase 4 PLAN/SUMMARY declares a shell probe and no conventional `scripts/**/tests/probe-*.sh` file exists. Probe execution is not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CLIENT-01 | 04-01 | Complete blank/example workbooks with instructions and validations | SATISFIED | 22 relations, policies, adapter, oracle and diagnostics verified. |
| CLIENT-02 | 04-02 | Offline portal separates demo/current and exposes all required evidence layers | SATISFIED | Private/public flow, parity, accessibility and exact visual inventory verified. |
| CLIENT-03 | 04-03 + roadmap SC3 | One documented no-server workflow initializes through package | BLOCKED | Creation and continuation work; integrated package stage/receipt is missing. |
| CLIENT-04 | 04-03 | Extractable public kit with blank/example materials and no private/native content | SATISFIED | Fresh 63-member package audit and extraction pass. Final adversarial content scanning remains a Phase 5 release gate. |

No orphaned Phase 4 requirement was found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| Phase 4 implementation set | - | No TBD/FIXME/XXX, empty handler, static empty output or unreferenced implementation found | INFO | No debt-marker blocker. |
| `tests/test_offline_portal_v1.py` | 285, 289 | Duplicate `if __name__ == "__main__"` block | INFO | Harmless under unittest discovery; first call exits in direct execution. |
| `scripts/build_offline_portal_v1.py` | 465 | HTML `placeholder` attribute | INFO | Instructional search copy, not stub data. |

### Visual and External-State Verification

The exact desktop and 390px public/current captures were inspected. Contact sheets covering every hash-bound print page (11 public and 48 safe synthetic-current) showed the expected sections, provenance, states and tables without horizontal clipping. The receipt's HTML/CSS/export hashes match a fresh public rebuild.

Phase 4 does not promote external business evidence: EXT-01 remains UNKNOWN, EXT-02 remains UNKNOWN and EXT-03 remains REVIEW in the requirements contract. The portal and package label public evidence synthetic/historical, private-current synthetic evidence advisory, and external execution PROHIBITED.

Desktop Excel recalculation and final delivered-workbook page inspection remain explicitly assigned to Phase 5 Plan 05-02; Phase 4 proves OOXML structure, input validation and canonical parity without claiming final Excel acceptance.

### Gaps Summary

The client workbooks, portal, native continuation and standalone public kit are substantive and connected. The phase goal still fails at its final orchestration link: the supported weekly command path does not package or receipt the sanitized client kit. Closing that one link should preserve the current privacy boundary by invoking only the public blank/synthetic builder, recording its hashes, and never copying the private run into the ZIP.

---

_Verified: 2026-09-23T23:39:23Z_
_Verifier: Codex phase verifier_
