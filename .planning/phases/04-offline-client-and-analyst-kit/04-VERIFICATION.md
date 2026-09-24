---
phase: 04-offline-client-and-analyst-kit
verified: 2026-09-24T19:48:08Z
status: gaps_found
score: 20/21 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 14/15
  gaps_closed:
    - "The supported weekly command now builds, audits, receipts and restart-verifies the public client package."
    - "Analysis now reaches PASS only when all expected verified analyst roles are accepted; 0/6, 1/6, 5/6 and 6/6 are covered."
  gaps_remaining:
    - "Actual 200 percent browser zoom and reduced-motion runtime observations remain uncaptured."
  regressions: []
gaps:
  - truth: "The redesigned portal's committed visual evidence demonstrates actual 200 percent browser zoom and reduced-motion behavior for both safe contexts."
    status: partial
    reason: "The receipt explicitly records a 720x450 CSS reflow equivalent to 200 percent of 1440 while labeling captures zoom_percent=200. It does not establish actual browser zoom, and no reduced-motion observation is recorded. CSS implementation exists; runtime behavior is UNCERTAIN, not observably broken."
    artifacts:
      - path: evidence/v1.0/portal/portal-visual-inspection.json
        issue: "critical_content_checks says '720 CSS pixel reflow equivalent to 200% of 1440'; no reduced-motion activation/result exists."
      - path: tests/test_offline_portal_v1.py
        issue: "Receipt validation accepts capture labels and PASS values without requiring zoom mechanism/measurement or reduced-motion observations."
    missing:
      - "Record actual browser zoom at 200 percent in both safe contexts, with mechanism, effective viewport, no-page-overflow measurement and inspected disposition; alternatively obtain an explicit approved override accepting reflow equivalence."
      - "Record activated prefers-reduced-motion: reduce and observed computed scroll-behavior:auto in both contexts."
      - "Bind observations to exact final HTML/CSS in the committed receipt, strengthen receipt assertions and rebuild the public ZIP to bind its new receipt SHA-256."
deferred:
  - truth: "Self-consistently rehashed allowed ZIP members containing secret-like or PII-like content must be rejected."
    addressed_in: "Phase 5 Plan 05-03"
    evidence: "Phase 5 owns final secrets/PII content scanning and content-mutation controls. Phase 4 checks generated-material boundaries, allowlisted members, hashes, workbook/policy surfaces and links."
---

# Phase 4: Offline Client and Analyst Kit Verification Report

**Phase Goal:** A client can prepare a cut offline and an analyst can navigate, run, and package the full local weekly workflow.
**Verified:** 2026-09-24T01:40:00Z
**Status:** gaps_found
**Re-verification:** Yes — package gap closure 04-04 and executive redesign 04-05.
**Phase 4 baseline:** `3f956604c9498ebb3d7c1f99605f6dbc74b84c31`.

The package and partial-native-state blockers are closed. One **WARNING** remains for incomplete browser acceptance evidence. No override accepts that warning, so the phase remains `gaps_found` without an open functional blocker.

Concurrent Phase 5 work advanced HEAD to `ed83b7ee4108ef02e7fe95d400cb9b682eafc50e` during inspection. A scoped diff against `3f95660` confirmed unchanged Phase 4 implementation, tests, CSS and visual evidence. AGENTS.md, legacy client/manifests and Phase 5 script changes were preserved. **The parent will rerun the final integrated suite after Phase 5 stabilizes; this report does not claim that gate passed.** Only this verification report was edited, with no commit.

## Goal Achievement

### Observable Truths

The original 15 truths are retained for regression traceability. Roadmap SC1–4 remain mandatory; plans 04-04 and 04-05 add six distinct checks after deduplicating invocation, privacy, parity and evidence requirements. Code, direct execution and hash-bound artifacts are evidence; SUMMARY completion claims are not.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Blank and visibly synthetic workbooks expose every registry relation exactly once with instructions and validation. | VERIFIED | `scripts/build_operating_workbooks.py:263,319,347` consumes SOURCE_NAMES; fresh generation test passes with 22 ordered relations, support sheets, validation and print metadata. |
| 2 | Workbook rows export through canonical intake while preserving missing versus measured zero. | VERIFIED | `alma/operating_workbook.py:193,238,328` checks types/surfaces, parses the pack and publishes atomically; fresh round-trip oracle passes. |
| 3 | Independent workbook → pack → manifest parity covers all 22 relations, rows, cents, units, nulls, zeros and hashes. | VERIFIED | `WorkbookImportTests.test_workbook_pack_manifest_oracle_covers_all_relations` and public-receipt check pass independently. |
| 4 | REVIEW and SYNTHETIC_EXAMPLE policies remain separate from the source relations and claim no owner approval. | VERIFIED | Policy validation at `scripts/build_operating_workbooks.py:337`; fresh package policy audit and authority-negative controls pass. |
| 5 | Workbook failures identify sheet, row, field, issue and correction without rewriting source. | VERIFIED | WorkbookContractError, _fail, _upstream_error and source rehash at `alma/operating_workbook.py:39,69,286,359`; prior passed code unchanged. |
| 6 | Complete public portal opens through local files and begins with historical synthetic provenance. | VERIFIED | Static local-only renderer; public/unselected tests pass. Fresh public generation matches 7/7 rendered-file receipt hashes; desktop capture shows warning before figures. |
| 7 | Current portal data derives from verified source/report/native/register evidence without demo contamination. | VERIFIED | `_current_model` calls verify_cycle, checks identity and derives current metric/source hashes. Public/unselected and tamper tests pass. Stage completion is separately assessed in truth 8. |
| 8 | Missing, partial, blocked or waiting native work remains pending throughout the portal. | VERIFIED | Analysis requires the complete nonempty expected-role set; 0/6, 1/6 and 5/6 remain ESPERANDO_RESPUESTA while 6/6 reaches PASS. Reviewer and owner states remain separate. |
| 9 | Metric model → HTML/CSV/JSON preserves exact values, units, hashes and boundary states. | VERIFIED | Boundary oracle passes for measured 0, null, 123456789 cents and MEASURED/UNKNOWN/PARTIAL/REVIEW/BLOCKED; current report flow inspected at lines 273–288. |
| 10 | Committed screen/print artifacts form a complete hash-bound inventory. | VERIFIED | 73/73 unique members rehashed, no mismatches or unexpected members: 10 viewport captures, 2 PDFs, 61 page rasters. Fresh public rebuild matches all seven rendered files. Runtime evidence sufficiency is truth 21. |
| 11 | Weekly creation adapts workbook/pack input and derives a new immutable private cut. | VERIFIED | `create_weekly_run` calls intake/policy/workspace/marts/cycle, refuses existing cuts, enforces `.local/client-runs` and retains WAITING_ANALYSTS. |
| 12 | Core native/reviewer/owner authority advances only through validated evidence. | VERIFIED | Continuation invokes Phase 3 record/submit/resume/packet/register APIs. The partial-role fixture stays WAITING_ANALYSTS; package success retains native_execution_claimed=false and execution PROHIBITED. The core pipeline does not share the display defect. |
| 13 | New-process continuation preserves earlier immutable evidence and exact supported actions. | VERIFIED | Action-specific grammar remains at `alma/weekly.py:384`; fresh clean-archive resume preserves package/receipt/index bytes. Other continuation wiring is unchanged from prior verification. |
| 14 | Public ZIP includes guide, dictionary, complete blank/example inputs, policies and demo portal without private/native/runtime members. | VERIFIED | Fresh disposable build/audit: 63 exact members, 22 resolved file links; unsafe member and policy-authority tests pass. |
| 15 | Supported weekly path itself builds and receipts the public package. | VERIFIED — prior gap closed | `alma/weekly.py:275–320`: build_client_kit(package) → audit_client_zip(package) → canonical receipt/index/result. Builder receives only output path; direct test passes. |
| 16 | Package receipt/index/result expose exact bounded identity and audit fields. | VERIFIED | `_package_identity` / `_verify_package_identity`, lines 118–162; exact-key tests verify relative path, ZIP/manifest hashes, member count and allowlist/privacy/links dispositions. |
| 17 | Identical public inputs reproduce bytes; replay and builder/auditor failure preserve atomicity. | VERIFIED | Both reproducibility/replay and injected builder/auditor failure tests pass; old bytes unchanged, partial new cut removed. |
| 18 | Clean-process resume revalidates package bytes, receipt and index before continuation. | VERIFIED | `_load_run` invokes package verification before actions; clean Git-archive subprocess and byte/receipt tamper tests pass. |
| 19 | Executive desktop overview places provenance, summaries, coverage and next exception/decision before full hashes. | VERIFIED | Both final desktop captures inspected: compact rail, coverage SVG/table and next-action panel precede details. |
| 20 | Five v1 domains account for 22 sources exactly once; historical inventory uses its own denominator. | VERIFIED | 5+5+5+4+3 unique SOURCE_DOMAINS entries equal SOURCE_NAMES; partition/rejection/count tests pass. Historical inventory is separately 30 sources. |
| 21 | Eight sections have verified responsive/no-JS/keyboard/reduced-motion/print behavior, including actual 200% browser zoom. | **UNCERTAIN — WARNING** | Required viewport captures and no-JS/keyboard observations exist; CSS includes reduced motion. Receipt only establishes 720px reflow equivalence and contains no reduced-motion observation. |

**Score: 20/21 truths verified.**

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/build_operating_workbooks.py` | Registry-complete workbooks/packs/policies | VERIFIED | Substantive builders consumed by package; generation/parity tests pass. |
| `alma/operating_workbook.py` | Validated canonical adapter | VERIFIED | Surface/cell checks precede parse_pack and atomic export; weekly calls it for XLSX. |
| `client/v1/policies/*.json` | Separate REVIEW and synthetic policies | VERIFIED | Package audit and negative controls pass. |
| `evidence/v1.0/workbooks/workbook-pack-parity.json` | 22-relation oracle | VERIFIED | Fresh oracle/receipt checks pass; SHA below. |
| `scripts/build_offline_portal_v1.py` | Truthful current/public static portal | VERIFIED | Current source flow exists and analysis completion requires equality with the full expected-role set. |
| `client/portal-v1.css` | Responsive/focus/reduced-motion/print styles | VERIFIED implementation | Bundled bytes match receipt; reduced-motion runtime proof incomplete. |
| `evidence/v1.0/portal/portal-visual-inspection.json` | Final bounded visual acceptance | HASH VERIFIED; acceptance PARTIAL | 73 members match; actual zoom and reduced-motion observations missing. |
| `run.ps1`, `alma/weekly.py` | Creation/continuation/package | VERIFIED | Supported module route, package stage and restart tests pass. |
| `scripts/package_client_v1.py` | Deterministic sanitized ZIP | VERIFIED within Phase 4 boundary | Fresh package and hostile-member/policy controls pass; deeper content scan belongs to Phase 5. |
| Client/analyst guides | Exact operating instructions | VERIFIED | Exact-command guide test passes; package resolves 22 file links. |
| Three Phase 4 test modules | Executable contracts | VERIFIED with coverage gaps | 16 selected existing tests pass; independent partial-role check exposes missing coverage. |

`gsd-tools query verify.artifacts` returned 6/6, 4/4, 7/7, 3/3 and 5/5 for plans 04-01 through 04-05. Existence/substance alone does not prove behavior.

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| Workbook generator | Source registry | SOURCE_NAMES/SOURCES imports and loops | WIRED | 22 authoritative schemas. |
| Workbook adapter | Canonical intake | parse_pack before publication | WIRED | `alma/operating_workbook.py:352`. |
| Private portal | Cut/marts/native cycle | verify_cycle → current-cut/report/state | WIRED | Lines 234–288; only analysis completion is incorrectly projected. |
| Portal | Decision register | verify_register/event projection | WIRED | Lines 210–230, unchanged verified flow. |
| Portal model | SVG/table/CSV/JSON | Shared coverage and metric projection | WIRED | Registry/count and boundary-value tests pass. |
| Visual receipt | Screens/PDF/pages | Exact SHA-256 inventory | WIRED | 73/73 rehash, acceptance observations incomplete. |
| `run.ps1` | `alma.weekly` | `-m alma.weekly` | WIRED | Launcher lines 18–19. |
| Weekly create | Public builder/auditor | Output-only direct calls | WIRED | Direct test verifies safe call arguments. |
| Package receipt | Index/resume | Canonical hash and fresh audit | WIRED | Exact-key, equality, tamper and restart checks pass. |
| Package manifest | Workbook/visual receipt | verification_inputs | WIRED | Fresh ZIP binds exact committed receipt hashes. |

The generic key-link query found 1/17 patterns: it does not recognize Python dotted imports, prose targets, generated receipt paths or the overescaped patterns in 04-04. Manual import/call tracing and direct execution above resolve these scanner false negatives. The old package link is demonstrably connected.

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Status |
|----------|------|--------|--------|
| Workbooks | Relation rows | Authoritative registry and explicit blank/synthetic fixture | FLOWING |
| Current portal | Sources/metrics/hashes | Verified current-cut report from canonical marts | FLOWING; no historical fallback |
| Analysis stage | Completion status | Actual verified accepted-role set | FLOWING; strict subsets remain pending and only the full expected-role set passes. |
| Native panel | Per-role status | Expected/accepted roles and response/dispatch hashes | FLOWING; partial fixture correctly waits |
| Coverage SVG/table | Integer state counts | Verified source inventory | FLOWING; exact 22/22 partition |
| Metric downloads | Value/unit/state/hash | Same model | FLOWING; zero/null preserved |
| Weekly package identity | Path/hashes/audit | Fresh public ZIP | FLOWING; immutable receipt/index and revalidation |
| Public ZIP | Workbooks/packs/portal/guides | Fresh public generators plus committed receipt inputs | FLOWING; no private cut supplied |

### Behavioral Spot-Checks

These tests were invoked by this verifier. Disposable fixtures use temporary test roots; no server, business action, full suite or new rasterization was run. Command prefix: `.venv/Scripts/python.exe -m unittest ... -v`.

| Selectors / check | Result | Status |
|-------------------|--------|--------|
| PortalExecutiveContractTests + visual receipt inventory test + analyst guide exact-command test | 7 tests, 0.726s | PASS |
| WeeklyPackageStageTests.test_success_binds_exact_safe_package_identity_and_public_inventory + portal boundary oracle + workbook public parity receipt | 3 tests, 3.048s | PASS |
| WeeklyPackageStageTests.test_tamper_fails_closed_and_clean_archive_process_revalidates_package | 1 test, 5.487s; clean Git archive/new process | PASS |
| WeeklyPackageStageTests.test_identical_public_inputs_are_reproducible_and_replay_changes_nothing + test_builder_and_post_build_audit_failures_remove_the_new_cut | 2 tests, 6.531s | PASS |
| Workbook generation contract + complete workbook/pack oracle + package unsafe-member/policy-authority negative controls | 3 tests, 4.798s | PASS |
| Analysis-stage role-count regression | 0/6, 1/6 and 5/6 pending; 6/6 PASS; reviewer remains independently pending | PASS |
| Fresh disposable build_client_kit → audit_client_zip → direct manifest/link/hash reads | 63 members, 22 file links, 7/7 public receipt-file hashes match | PASS |
| Committed visual inventory rehash | 73 unique members; zero mismatch/unexpected; no reduced-motion observation | Hash PASS; acceptance WARNING |
| Optional PDF text extraction | fitz/pypdf/PyPDF2/pdfplumber unavailable; no dependency installed | SKIP; existing PNG samples inspected |
| Final integrated suite | Parent will rerun after Phase 5 stabilizes | NOT CLAIMED |

#### Exact functional reproduction

Run from repository root. These synthetic fixture responses exercise validators; they are not actual native execution evidence.

```powershell
.venv/Scripts/python.exe -c 'import json,tempfile; from pathlib import Path; from tests.test_weekly_cycle import upstream; from tests.test_native_agents_v1 import response_for,trace_for,receipt_for; from tests.test_decision_register import MODELS; from tests.test_weekly_kit import canonical_file; from alma.weekly_cycle import start_cycle,record_dispatch,submit_response,verify_cycle; from scripts.build_offline_portal_v1 import collect_portal_model; t=tempfile.TemporaryDirectory(); h=Path(t.name); c,m=upstream(h); p=Path(start_cycle(c,m,h/".local"/"weekly-cycles")["destination"]); role=sorted(MODELS)[0]; q=json.loads((p/"tasks"/(role+".request.json")).read_bytes()); r,x=response_for(q),trace_for(q); rp=canonical_file(p/"tasks"/(role+".response.json"),r); xp=canonical_file(p/"tasks"/(role+".query-trace.json"),x); receipt=receipt_for(q,r,x,MODELS[role]); record_dispatch(p,role,rp,xp,receipt); submit_response(p,role,rp,xp,p/"tasks"/(role+".dispatch.json")); model=collect_portal_model(mode="private",selected_cycle=p); state=json.loads((p/"state.json").read_bytes()); print(json.dumps({"verified_cycle":verify_cycle(p)["status"],"accepted":len(state["accepted_roles"]),"expected":len(state["expected_roles"]),"analysis_stage":[s for s in model["stages"] if s["name"]=="Análisis"],"native_status":model["native"]["status"]},ensure_ascii=True)); t.cleanup()'
```

Observed after correction: `accepted=1/6` keeps `Análisis=ESPERANDO_RESPUESTA`; the bounded 0/6, 1/6, 5/6 and 6/6 regression passes.

### Exact Package and Visual Evidence

| Artifact | SHA-256 |
|----------|---------|
| Fresh disposable public ZIP | `482d01812f9003a4482170188dc7c0bf3fafacab2b47951eb8deb42723784874` |
| Fresh package manifest | `5bc31dc544e6c537e57930ef5cfc4064a38c828aab4224e44c216de30070093b` |
| Committed visual receipt | `ce2f548c069b94b3e7c5cd240191a4be16ce4ad39a692419db7537b841e28de9` |
| Workbook receipt | `14a04d8a2b7737836b85b2f30ab22e27b69c7af3f57cae08e2f367ddf43852c0` |
| Public HTML | `c425ef4e7b63d4b4cce493d5b5cbf64f60caa64715b762292d791870f82d3c14` |
| CSS | `0da05684f15f8df23740a66d445fcabe89a3d3cefae5196337d8f8d12af6e416` |

Receipt: Microsoft Edge 153.0.4234.48, 1440×900 / 960×900 / 390×844 / 320×800 / 720×450 CSS captures per context; 10 public and 51 synthetic-current print pages. The last capture is explicitly described as reflow equivalence; `zoom_percent: 200` alone does not establish actual browser zoom. Reduced-motion CSS exists but no corresponding observation is recorded.

Both desktop images, current 320px, public final print page and current first/last/lineage print pages were visually inspected. They retain provenance/status, first-screen density and full hashes. The 61 rasters were not regenerated or all re-reviewed: exact inventory/hashes were checked, and the committed receipt records earlier executor/root all-page inspection. No ignored artifact is accepted as durable release proof: the ZIP above was independently regenerated in a disposable directory. Final publication/CI proof remains Phase 5.

### Probe Execution

No Phase 4 plan declares a shell probe, and no conventional `scripts/**/tests/probe-*.sh` exists. Probe execution is not applicable; direct Python checks are recorded above.

### Requirements Coverage

| Requirement | Source plans | Status | Evidence |
|-------------|--------------|--------|----------|
| CLIENT-01 | 04-01 | SATISFIED | 22-relation generation/round-trip oracle, adapter validation and separate policies. |
| CLIENT-02 | 04-02, 04-05 | **BLOCKED** | Partial-native analysis incorrectly renders PASS; actual zoom/reduced-motion evidence also incomplete. |
| CLIENT-03 | 04-03, 04-04 | SATISFIED | Integrated package, immutable identity, atomicity/replay and clean restart pass. |
| CLIENT-04 | 04-03, 04-05 | SATISFIED at package boundary | Fresh 63-member/22-link ZIP binds current receipt and excludes private/native materials; receipt acceptance limitations remain attached to CLIENT-02. |

All four CLIENT requirements occur in plan frontmatter; no orphaned Phase 4 requirement. EXT-01/02/03 remain external gates, not adoption/fiscal/business-impact claims here.

### Anti-Patterns and Disconfirmation

| File | Line | Finding | Severity | Impact |
|------|------|---------|----------|--------|
| `scripts/build_offline_portal_v1.py` | 265 | Any accepted role produces analysis PASS | BLOCKER | Partial native work appears complete. |
| `tests/test_offline_portal_v1.py` | 147,354 | Zero-role waiting test; receipt labels accepted without actual zoom/motion evidence | WARNING | Green tests miss the failed/uncertain outcomes. |
| `evidence/v1.0/portal/portal-visual-inspection.json` | 1 | Reflow equivalence labeled zoom=200; no reduced-motion observation | WARNING | Browser acceptance incomplete. |
| Phase 4-owned implementation/test/guide files | — | No unreferenced TBD/FIXME/XXX marker found | INFO | No debt-marker blocker; Spanish TODOS is not TODO debt. |
| Source-search placeholder and empty/no-series states | — | Intentional instructional/unknown states | INFO | Not disconnected data stubs. |

Disconfirmation found a partial requirement (analysis completion), a misleading green check (receipt acceptance without actual zoom observation) and an uncovered edge case (strict subsets of accepted analysts). The old SUMMARY pass counts do not waive these findings.

### Human Verification Required

#### 1. Actual 200 percent browser zoom

**Test:** Open both safe final file views, activate actual browser zoom 200%, inspect all eight sections and keyboard/table navigation. Record activation mechanism, effective viewport, document scroll/client widths and screenshot bound to final HTML/CSS.

**Expected:** No page-level horizontal overflow, hidden provenance/warnings or obscured navigation. A 720px viewport alone is not represented as proof of zoom activation.

**Why human/runtime:** Committed evidence establishes reflow equivalence only. Supply this runtime check or explicitly approve an override accepting equivalence; none exists currently.

#### 2. Reduced-motion activation

**Test:** Activate `prefers-reduced-motion: reduce` in both contexts; record a matching media query, computed root `scroll-behavior:auto`, visible focus and anchor behavior.

**Expected:** Anchor navigation avoids smooth scrolling. Commit bounded observations and rebuild the package to bind the revised receipt.

**Why human/runtime:** CSS exists, but activation was not observed in committed evidence. This is UNCERTAIN, not an absent implementation.

No PLAN `<human-check>` block adds another item. The functional BLOCKER takes precedence over `human_needed` for overall status.

### Deferred Items

| Item | Owner | Basis |
|------|-------|-------|
| Rehashed allowed-member secret/PII payload detection | Phase 5 / 05-03 | Explicit final content scan and mutation controls; Phase 4 privacy PASS is narrower. |
| Final desktop Excel engine and delivered-byte page acceptance | Phase 5 / 05-02 | Roadmap SC2 and workbook plan assign the engine gate there. |
| Integrated regression, release archive/CI and publication acceptance | Phase 5 / 05-01..03 | Parent reruns after stabilization; no final release claim here. |

No later-phase goal specifically owns truthful partial-native portal stages or the redesigned portal's browser checks; those remain Phase 4 gaps.

### Gaps Summary

04-04 closes the previously disconnected package stage. 04-05 supplies the executive layout, exact source partition, bounded 73-member visual inventory and reproducible 63-member/22-link public kit. The remaining functional defect falsely completes analysis at 1/6 accepted responses. Fix its projection and subset regressions, resolve zoom/reduced-motion evidence, then refresh affected receipt/package bindings and relevant phase checks. The parent retains the final integrated-suite gate after Phase 5 stabilization.

---

_Verified: 2026-09-24T01:40:00Z_
_Verifier: independent Codex phase verifier; report-only ownership; no commit_
