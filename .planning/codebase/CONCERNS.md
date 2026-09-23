# Codebase Concerns

**Analysis Date:** 2026-09-22

## Tech Debt

**Two independent analytical paths (Phase 1, then Phase 3):**
- Issue: `alma/client_review.py` validates an aggregate workbook and writes `informe.json`, `informe.html`, corrections and a native-analysis brief; `alma/workspace.py` builds the 30-table v0.2 synthetic warehouse and starts its own process requests. There is no shared current-cut manifest or route from the private aggregate report into current marts and native review.
- Files: `alma/client_review.py`, `alma/workspace.py`, `alma/process_engine.py`, `scripts/review_client_workbook.py`, `.planning/research/INTEGRATION-GAPS.md`.
- Impact: A successful workbook review does not imply that an analyst or independent reviewer ran on that cut; v0.2 decision packets cannot be presented as current private-cut decisions.
- Fix approach: In Phase 1, create an aggregate-specific, immutable v1 workspace with source hashes, coverage and relational marts. In Phase 3, bind its exact report hash to native requests, response validation and a distinct reviewer. Preserve the released v0.2 path and do not manufacture row-level orders or customers from aggregate input.

**Hardcoded cost and operations extension (Phase 1 and Phase 2):**
- Issue: `scripts/build_costs_operations.py` defines a generated eight-source example and calculates cost, receipts, obligations and cash separately from the workbook and `models/marts/*.sql`. Its manifest identifies these as local synthetic evidence.
- Files: `scripts/build_costs_operations.py`, `client/operating-data/cost_versions.csv`, `client/operating-data/purchase_receipts_ops.csv`, `client/operating-data/obligations.csv`, `client/costs-operations-manifest.json`, `specs/COSTS-OPERATIONS-v3.md`.
- Impact: The example is useful for contract illustration but does not reconcile a private cut's cost, inventory, obligations or cash with canonical source facts.
- Fix approach: Phase 1 should version and validate source packs with shared SKU/event identities. Phase 2 should compute cost, receipt, obligation and cash marts from those canonical facts, including exact residual cents and source-to-mart reconciliation.

**Manual decision register (Phase 3):**
- Issue: The distributed register is only a header and the current package checks that it remains blank. There is no implemented validator for source hash, owner, due date, state transition, closure evidence or next-cut carry-forward.
- Files: `client/REGISTRO_DECISIONES.csv`, `scripts/package_client.py`, `.planning/REQUIREMENTS.md`.
- Impact: Owner actions can be recorded manually, but stale or contradictory decisions cannot be detected by the analytical cycle.
- Fix approach: Phase 3 should define a private, validated decision ledger and immutable cut linkage; carry open items forward and flag overdue or stale actions without performing the business action.

**Historical atlas and separate deliverables (Phase 4):**
- Issue: `scripts/build_client_system.py` renders the historical synthetic v0.2 atlas, and `scripts/package_client.py` packages v0.3 blank/example workbooks plus that atlas. The private validator and native cycle are not packaged as a runnable analyst workflow.
- Files: `scripts/build_client_system.py`, `scripts/package_client.py`, `client/SISTEMA_ANALITICO.html`, `agents/RUN-NATIVE-CYCLE.md`, `.planning/research/INTEGRATION-GAPS.md`.
- Impact: A recipient can inspect the demonstration while mistaking its historical packets for a current cut unless the private report and portal are clearly separated.
- Fix approach: Phase 4 should generate the portal from a declared selected cut, label public demo versus private current evidence on every decision surface, and ship a documented analyst CLI workflow while excluding private outputs.

## Known Bugs

**No unresolved reproduced defect in the reviewed v0.2/v0.3 scope:**
- Symptoms: Not detected in the final dispositions of the bounded adversarial reviews; earlier tamper, coverage, cohort, spend, report-escaping and malformed-input findings were repaired and replayed.
- Files: `docs/ADVERSARIAL-REVIEW.md`, `docs/ADVERSARIAL-REVIEW-v2.md`, `tests/test_adversarial.py`, `tests/test_process_engine.py`, `tests/test_warehouse.py`.
- Trigger: Not applicable for an open defect. The reviews do not establish behavior for the planned v1 aggregate intake and two-week cycle.
- Workaround: Preserve the existing negative controls while adding v1 tests at each new boundary.

## Security Considerations

**Private source data and public release boundary (Phase 1, Phase 4 and Phase 5):**
- Risk: A filled workbook, private report or generated file outside the approved public fixture set could disclose business or personal data if copied into Git or a package. A short `source_ref` and synthetic declaration are input constraints, not proof that arbitrary text contains no private information.
- Files: `alma/client_review.py`, `scripts/package_client.py`, `scripts/audit_release.py`, `client/contract.json`, `docs/CLIENT-OPERATIONS-v3.md`, `AGENTS.md`.
- Current mitigation: The private reviewer restricts output to `.local/client-runs`; workbook input rejects macros/external links and checks size; packaging compares generated blank/synthetic workbook content and exact hashes; the release audit scans publishable text for bounded secret patterns.
- Recommendations: Keep all filled cuts, responses and exports under ignored private paths. Phase 1 should enforce a non-PII source schema and quarantine invalid packs; Phases 4–5 should audit every new public artifact by allowlist, hashes and content/provenance review. The pattern audit must continue to state its limits.

**Native analysis provenance and authority (Phase 3):**
- Risk: A current-cut native response could appear authoritative if its request hash, runtime dispatch, analyst/reviewer identity or terminal packet is not bound and rechecked. Schema checks cannot establish whether arbitrary prose is semantically correct.
- Files: `alma/native_agents.py`, `alma/process_engine.py`, `contracts/native-agent-response.schema.json`, `agents/RUN-NATIVE-CYCLE.md`, `docs/ADVERSARIAL-REVIEW-v2.md`.
- Current mitigation: The v0.2 process engine anchors requests, checkpoints, responses, dispatches and packets to journal/workspace evidence, requires a different reviewer identity, and keeps `external_execution='PROHIBITED'`.
- Recommendations: Reuse these invariants in the v1 bridge, reject stale hashes and same-agent review, and require a substantive independent review of values and interpretation. Do not describe request preparation as an executed model call.

## Performance Bottlenecks

**Workbook review scans fixed sheets and 91 cash days (Phase 1, if limits change):**
- Problem: `alma/client_review.py` reads each populated row within fixed sheet ranges and recomputes each of 91 daily cash periods by scanning cash rows; its current contract intentionally caps the input.
- Files: `alma/client_review.py`, `client/contract.json`, `tests/test_client_review.py`.
- Cause: The local workbook validator favors transparent, bounded computation over indexed/event-table processing.
- Improvement path: Keep the existing contract limits for the workbook. If v1 source packs exceed those limits, index normalized cash events by date in the SQLite operating workspace and benchmark with realistic synthetic sizes before increasing capacity.

**Whole-artifact package and audit passes (Phase 5, if package grows):**
- Problem: `scripts/package_client.py` compares generated workbook content and hashes all atlas evidence; `scripts/audit_release.py` walks Git publishable scope and reads allowed SQLite dumps/workbook XML.
- Files: `scripts/package_client.py`, `scripts/audit_release.py`, `client/system-manifest.json`.
- Cause: Publication checks deliberately reread complete artifacts to prove bytes and privacy boundaries.
- Improvement path: Retain full verification as the release gate. Measure its runtime when v1 adds sources; optimize only if the check exceeds CI's 15-minute job limit, without replacing content verification with untrusted manifest counts.

## Fragile Areas

**Financial and event-grain semantics (Phase 2):**
- Files: `alma/client_review.py`, `models/marts/cash_daily.sql`, `models/marts/finance_monthly.sql`, `scripts/build_costs_operations.py`, `docs/DOMAIN.md`, `docs/CLIENT-OPERATIONS-v3.md`.
- Why fragile: Sales delivery, credits, refunds, physical receipt, inventory acceptance, obligation and payment have different recognition dates and grains. Aggregating or joining them casually can duplicate money/units or turn missing coverage into a false zero. The client reviewer computes with `Decimal` but `clean_json` serializes Decimal values as JSON numbers via Python `float`; v1 canonical relational money must be converted to integer MXN cents at intake rather than trusting that report serialization as an exact ledger.
- Safe modification: Define a fact/event identity for each domain, preserve source status and timestamp, use integer cents in SQLite, reconcile independent source totals and carry unknowns through dependent marts.
- Test coverage: Existing v0.2/v0.3 hand-calculated and negative tests cover their own models in `tests/test_analytics.py`, `tests/test_warehouse.py`, `tests/test_costs_operations.py` and `tests/test_client_review.py`; new v1 canonical joins, residual-cent allocations and two-week carry-forward require separate tests.

**Excel formula acceptance (Phase 4 and Phase 5):**
- Files: `scripts/build_client_workbook.py`, `scripts/recalculate_client_excel.ps1`, `scripts/verify_client_v3.py`, `.github/workflows/verify.yml`, `docs/CLIENT-OPERATIONS-v3.md`.
- Why fragile: CI checks recorded Excel-engine receipts and independent arithmetic on Linux; it does not perform a fresh Excel recalculation. Workbook formula changes can alter cached values or visual output despite green non-Excel checks.
- Safe modification: After a formula change, run the Windows desktop Excel script on newly generated blank/example files, verify exact post-save hashes against the Decimal oracle, inspect rendered sheets and record a new receipt before packaging.
- Test coverage: `tests/test_client_review.py` and `scripts/verify_client_v3.py` exercise calculations and recorded receipts; fresh Excel recalculation is an external execution gate, not covered by Linux CI.

## Scaling Limits

**Client workbook capacity:**
- Current capacity: 100 SKUs, 1,000 date/SKU sales aggregates, 250 cash-plan rows and 13 forecast weeks, declared in `client/contract.json` and enforced by `alma/client_review.py`.
- Limit: Rows beyond the contract range receive a capacity issue and are excluded from analysis; workbook files over 20 MB, archives over 100 MB uncompressed or over 1,000 members are refused by `alma/client_review.py`.
- Scaling path: Phase 1 should use versioned CSV and SQLite packs for larger or richer operating cuts while keeping the workbook as a bounded intake/export interface; do not silently expand formulas or truncate data.

**Local, single-operator runtime:**
- Current capacity: One immutable output directory per `alma/workspace.py` build or `alma/client_review.py` run; `alma/process_engine.py` serializes process mutations with a file lock.
- Limit: No multi-user server, concurrent shared database service or automated external scheduler is defined in `alma/__main__.py` or `.github/workflows/verify.yml`.
- Scaling path: For the agreed local analytical product, make cut creation, export/restore and idempotent replay reliable first (Phase 1 and Phase 3). Any shared runtime would require a separate product decision and authority model.

## Dependencies at Risk

**Desktop Excel availability:**
- Risk: `scripts/recalculate_client_excel.ps1` depends on Windows desktop Excel and an interactive session; the Linux CI workflow cannot reproduce a fresh engine receipt.
- Impact: Formula-changing workbook releases cannot be fully accepted by CI alone.
- Migration plan: Keep `scripts/verify_client_v3.py` as the independent arithmetic oracle and require a fresh Excel-engine receipt only when formulas or workbook rendering change. Keep the client-facing offline spreadsheet optional to the Python/SQLite core.

## Missing Critical Features

**Versioned current-cut intake and restore (Phase 1):**
- Problem: `alma/workspace.py` accepts the v0.2 synthetic schema; `alma/client_review.py` accepts four aggregate workbook sheets, but neither creates a v1 canonical operating cut with the domains and export/restore integrity required by `DATA-01..05` in `.planning/REQUIREMENTS.md`.
- Blocks: Current private cost/stock/obligation/cash marts, stable cut identity and trustworthy follow-up analysis.

**Decision-ready v1 marts and exceptions (Phase 2):**
- Problem: `models/marts/*.sql` model the v0.2 synthetic warehouse, while `scripts/build_costs_operations.py` covers only a fixed example. Budget/drop/channel, quality, sales readiness, loan custody, complete cost history and reconciled cash layers are not unified as v1 facts and marts.
- Blocks: Requirements `MET-01..07` in `.planning/REQUIREMENTS.md`, including an owner/action/date/closure exception queue and controlled sales-facing views.

**Current-cut native review and closure (Phase 3):**
- Problem: `alma/client_review.py` prepares an analyst brief but does not validate a live response, independently review it or persist its decision closure; `client/REGISTRO_DECISIONES.csv` is blank.
- Blocks: Requirements `FLOW-01..05` in `.planning/REQUIREMENTS.md` and a credible two-week decision trail.

**Real data and business-policy gates (external owner, not code defects):**
- Problem: No authorized private first cut, reconciled opening bank position, approved tax/accounting treatment, content rights or business role assignment is in the inspected source or acceptance evidence. The Pilates-socks winner hypothesis has no eligible observed launch window.
- Files: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/research/DOMAIN.md`, `.planning/research/INTEGRATION-GAPS.md`, `docs/CLIENT-SYSTEM-ACCEPTANCE.md`.
- Blocks: Real-data correctness/adoption claims, fiscal or net-margin claims, owner approval of actions and product-winner claims. Keep `EXT-01..03` explicitly UNKNOWN/REVIEW until owner or qualified evidence arrives; Phases 1–5 can finish with blank and synthetic inputs.

## Test Coverage Gaps

**Aggregate v1 intake and reconciliation (High; Phase 1 and Phase 2):**
- What's not tested: Immutable v1 source-pack validation, duplicate/conflicting receipt quarantine, exact relationship restore, residual-cent allocation, double-count prevention and partial coverage propagation across the new canonical marts.
- Files: `.planning/REQUIREMENTS.md`, `tests/test_warehouse.py`, `tests/test_costs_operations.py`, `alma/warehouse.py`, `scripts/build_costs_operations.py`.
- Risk: A new v1 join or import could publish plausible but duplicated money or stock while existing v0.2/v0.3 suites remain green.
- Priority: High.

**Two distinct weekly cuts with native review (High; Phase 3):**
- What's not tested: A current private aggregate report feeding an actual native analyst, a distinct reviewer, a hash-bound decision register and carried open/closed items in week two; tamper and stale-response failures for that new bridge.
- Files: `alma/client_review.py`, `alma/process_engine.py`, `tests/test_process_engine.py`, `client/REGISTRO_DECISIONES.csv`, `.planning/REQUIREMENTS.md`.
- Risk: A process may look complete because the historical v0.2 packets replay, while current-cut decisions have no verified analyst or closure chain.
- Priority: High.

**Final package on both operating-system boundaries (Medium; Phase 5):**
- What's not tested: A clean extracted v1.0.0 kit with new source packs, portal and CLI on Windows and Linux. The current `.github/workflows/verify.yml` has one Ubuntu job and packages v0.3 artifacts.
- Files: `.github/workflows/verify.yml`, `scripts/package_client.py`, `scripts/audit_release.py`, `.planning/REQUIREMENTS.md`.
- Risk: Path, Excel and package-link behavior can differ from the published local release gate.
- Priority: Medium.

---

*Concerns audit: 2026-09-22*
