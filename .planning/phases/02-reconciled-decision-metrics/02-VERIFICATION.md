---
phase: 02-reconciled-decision-metrics
verified: 2026-09-23T05:31:00Z
status: gaps_found
score: 2/10 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Economics reconcile to the cent across reporting partitions and preserve estimated cost quality."
    status: failed
    reason: "Realized COGS resets residual ordinals for every channel/window, and estimated complete costs become MEASURED economics."
    artifacts:
      - path: alma/operating_cost_inventory.py
        issue: "Lines 173-189 initialize per-call ordinals; line 198 ignores ESTIMATED input quality."
    missing:
      - "Allocate cents against stable canonical sales/unit ordinals before channel/window filtering; prove partition additivity."
      - "Propagate estimated cost quality into contribution, margin, markup and their metric rows."
  - truth: "Mature return and quality rates use eligible linked cohorts with correct denominators."
    status: failed
    reason: "The oldest sale date matures all sales in the window; quality rows are selected for the SKU without matching the selected delivery cohorts."
    artifacts:
      - path: alma/operating_learning_exceptions.py
        issue: "Lines 230-254 aggregate all sales and use min(sales_date) for both return and defect maturity."
      - path: models/operating_learning_exceptions.sql
        issue: "quality_events filters SKU and event_date only; no selected-cohort join."
    missing:
      - "Evaluate maturity, numerator, denominator and coverage per delivery_cohort_id; aggregate only eligible cohorts."
      - "Exclude returns/inspections from cohorts outside the denominator and retain immature/unlinked rows as UNKNOWN."
      - "Test mixed mature/immature and out-of-window linked cohorts through project_learning, not only scalar helpers."
  - truth: "Cash marts accept canonical reconciled inflows and publish all separate cash layers."
    status: failed
    reason: "Phase 2 rejects observed cash inflows allowed by Phase 1 because every reconciled event must have a payable payment_id; normalized cash rows omit reconciled, committed and expected layers."
    artifacts:
      - path: alma/operating_finance_marts.py
        issue: "active_cash_events requires payment_id for all RECONCILED events, including independently evidenced INFLOW."
      - path: alma/operating_marts.py
        issue: "Lines 156-164 look for committed_cents/planned_cents, but cash_horizons supplies layers_cents with RECONCILED/COMMITTED/EXPECTED."
    missing:
      - "Honor Phase 1 observed-source inflow/outflow evidence and preserve payment checks only for obligation-linked settlements."
      - "Serialize the actual nested cash-layer contract into normalized rows for both horizons with truthful statuses and lineage."
      - "Test a valid observed inflow plus nonzero committed/expected events end to end."
  - truth: "A missing or zero-event source blocks only dependent complete metrics, not unrelated families."
    status: failed
    reason: "A valid Phase 1 cut with ZERO unmet_demand fails the whole bundle because registry IDs must equal emitted row IDs."
    artifacts:
      - path: alma/operating_marts.py
        issue: "Line 180 requires every registered metric to emit a row, although event-grain domains legitimately have no rows."
    missing:
      - "Require every emitted metric to have a definition without requiring invented event rows for empty domains."
      - "Represent empty/unknown domain coverage explicitly and preserve unrelated metrics."
      - "Build a valid zero-unmet-demand bundle and exercise missing/zero sales, budgets, payments and cash domains."
  - truth: "Every published metric exposes its formula, grain, unit, window, sources, unknown rule, guardrail, owner and decision use."
    status: failed
    reason: "The registry covers selected normalized metrics only; published known cost, markup, gross margin, contribution margin and financial-state measures have no individual definitions."
    artifacts:
      - path: alma/operating_marts.py
        issue: "COST_DEFINITIONS contains only complete cost, available units, purchase remaining and realized contribution; families.json also publishes additional decision metrics."
      - path: alma/operating_finance_marts.py
        issue: "FINANCE_DEFINITIONS covers headroom but not the separately published approved/committed/incurred/paid/outstanding/unallocated measures."
    missing:
      - "Inventory all decision measures in families.json and give each a complete definition and faithful normalized representation, or explicitly model documented facts separately."
      - "Check semantic registry coverage against published measures rather than only comparing the already-selected metric_rows IDs."
---

# Phase 2: Reconciled Decision Metrics Verification Report

**Phase Goal:** Analysts and owners can inspect one exact, coverage-aware account of costs, units, cash, demand learning, and actionable exceptions for a cut.

**Verified:** 2026-09-23T05:31:00Z  
**Status:** gaps_found  
**Re-verification:** No — initial verification; no previous verification or overrides existed.  
**Inspected HEAD:** `33d512c8db31a968339448cebbb683aec80b0f8c`

## Goal Achievement

The implementation is substantive and the existing tests pass, but the goal is not achieved. Five groups of reproducible blockers affect exact economics, cohort learning, cash admissibility and serialization, empty-domain publication, and complete metric documentation. No code or source data was changed by this verification. Tests used disposable synthetic fixtures; additional arithmetic checks used in-memory SQLite.

### Observable Truths

The five roadmap criteria are retained verbatim. Five additional plan requirements cover behaviors not fully stated in those criteria; repeated plan formulations were merged into the roadmap wording.

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | An owner can compare known cost, complete cost, markup, gross margin, and contribution by effective cost version; allocations reconcile to the cent and incomplete costs remain unknown. | FAILED — BLOCKER | Cost version/coverage code exists, but `realized_economics` resets its ordinal at each call: combined 101-cent COGS becomes 102 cents across three daily windows. |
| 2 | An analyst can reconcile ordered, received, inspected, accepted, rejected, non-sellable, loaned, reserved, and available units once, with no duplicate receipt or return event inflating stock. | VERIFIED | `reconcile_purchase`, `project_purchases`, `project_inventory` and SQL use one accepted movement per receipt, distinct restock IDs, count variance and custody/reservation controls. Focused receipt/custody/variance tests pass with 20 ordered, 18 received, 16 accepted, 2 inspection, 21 available. |
| 3 | An owner can view outstanding obligations and applied payments alongside separate reconciled, committed, expected, undated, and scenario cash in eight- and thirteen-week windows; budget and drop/channel financial states reconcile without double counting. | FAILED — BLOCKER | Obligations and ordinary budget calculations pass, but a Phase 1-valid observed inflow is rejected by `active_cash_events`. Normalized rows include only undated/scenario cash; the other layers remain stranded in nested family facts. |
| 4 | An owner can inspect launch sell-through, variant mix, mature return/quality rates, stock exposure, and recorded unmet demand with explicit denominators, windows, and coverage; an exposed stockout does not become a weak-preference claim. | FAILED — BLOCKER | Ten mature deliveries plus ninety one-day-old deliveries yield a MEASURED return rate of 1/100 instead of a mature-cohort denominator of 10, or an explicitly unknown pooled rate. |
| 5 | Sales-facing readiness and quality/loan exceptions show an owner, action, date, and closure state without internal cost disclosure; every metric exposes its formula, unit, grain, sources, unknown rule, guardrail, owner, and decision use. | FAILED — BLOCKER | Fixed public category/field/value validation works; missing due/closure evidence stays unresolved as allowed by Plan 02-03. However many metrics exposed in families.json have no definition. |
| 6 | Missing Phase 1 input or incomplete source coverage blocks only dependent complete metrics and never converts unknown into zero. | FAILED — BLOCKER | Empty `unmet_demand.csv` plus coverage ZERO passes real intake, then the bundle fails `metric registry and emitted rows differ`; unrelated metrics cannot be published. |
| 7 | Documented and estimated complete costs remain distinguishable in dependent economics. | FAILED — BLOCKER | A Phase 1-valid ESTIMATED component produces cost status ESTIMATED and economics status MEASURED. The helper-only estimated-cost test does not inspect the consumer. |
| 8 | One obligation balance retains recorded unpaid under partial application coverage while withholding authoritative outstanding. | VERIFIED | `reconcile_obligation`/`project_obligations`; independently rerun 180000 minus 100000 oracle, partial coverage, overapplication, duplicate payment and VOID controls pass. |
| 9 | Unavailable variants, immature/unlinked return cohorts and absent unmet-demand logging cannot produce false preference or zero-demand claims. | FAILED — BLOCKER | Exposure and recorded-demand safeguards exist, but the mixed-cohort runtime counterexample violates the immature-cohort clause. |
| 10 | All Phase 2 metric definitions and results validate together; missing/stale policy, unsafe paths or failed reconciliation publish no derived bundle. | FAILED — BLOCKER | Hash/path/staging negative controls pass, but cash contract mismatch silently omits three layers and registry equality incorrectly rejects a valid zero-event domain. |

**Score:** 2/10 truths verified. Every failed truth is a BLOCKER; none is treated as uncertain or accepted by override.

### Required Artifacts

All 13 plan artifacts exist and contain substantive implementation. GSD `verify.artifacts` returned 6/6, 3/3 and 4/4; these are existence/shape checks, not behavioral proof.

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `alma/operating_mart_contracts.py` | Verified cut binding, policy and row contracts | VERIFIED with warning | Reads actual SQLite/source hashes, semantic fields, PK/FKs and read-only connection. Policy validated manually rather than by loading its JSON schema. |
| `contracts/operating-metrics-policy-v1.schema.json` | Policy contract | WARNING — runtime link incomplete | Present, substantive; `load_policy` duplicates validation rules without loading this artifact. |
| `policies/operating-metrics-synthetic-v1.json` | Explicit synthetic policy | VERIFIED | Read by load_policy; canonical SHA-256 and status/effective interval checked. |
| `alma/operating_cost_inventory.py` | Exact costs and unit conservation | FAILED | Wired calculations; cents partitioning and estimated economics defects above. |
| `models/operating_cost_inventory.sql` | Source-grain projections | VERIFIED | `_query` reads named SQL and actual cut connection executes it. |
| `tests/test_operating_marts_cost_inventory.py` | Cost/unit hand oracles | VERIFIED, incomplete coverage | 8 existing tests pass; no partitioned residual or estimated downstream-economics test. |
| `alma/operating_finance_marts.py` | Obligations/cash/budget controls | FAILED | Actual finance computations; rejects valid non-payable reconciled cash. |
| `models/operating_finance_marts.sql` | Canonical finance aggregates | VERIFIED | Used by project functions with integer sums and dated filters. |
| `tests/test_operating_marts_finance.py` | Finance oracles | VERIFIED, incomplete coverage | 6 tests pass; reconciled example uses payable outflow only. |
| `alma/operating_learning_exceptions.py` | Learning and exceptions | FAILED | Real source queries and public allowlists; cohort maturity/grain violation. |
| `models/operating_learning_exceptions.sql` | Cohort/exposure source queries | FAILED | Used at runtime, but quality selection lacks denominator-cohort restriction. |
| `alma/operating_marts.py` | Registry and private atomic bundle | FAILED | Real staging/hashing/publication; serializer/registry defects above. |
| `tests/test_operating_marts_learning.py` | Learning/privacy/publication tests | VERIFIED, incomplete coverage | 8 tests pass; no mixed-cohort projection or valid zero-event bundle test. |

### Key Link Verification

The GSD text-pattern helper reported all 8 plan links unverified because targets use prose, Python module imports and composed Path expressions. Manual tracing supersedes these false negatives where actual calls exist.

| From | To | Via | Status | Details |
|---|---|---|---|---|
| Shared contracts | Phase 1 schema/manifest | bind_cut and relationship_summary | WIRED | Actual source bytes, manifest, SQLite and semantic checks. |
| Cost/inventory Python | Cost/inventory SQL | SQL_PATH, _query, connection.execute | WIRED | Runtime tests exercise the named queries. |
| Finance Python | Shared contracts and finance SQL | Imports, _query, MetricRow | WIRED | Actual inputs and output rows. |
| Learning Python | Shared contracts/learning SQL | Imports, _query, MetricRow | WIRED, behavior defective | SQL-selected cohort facts are aggregated at the wrong grain. |
| Bundle builder | Cost/inventory/finance/learning | _collect | PARTIAL — BLOCKER | Calls all builders; finance `layers_cents` contract is not consumed faithfully. |
| Bundle builder | Private output directory | _private_root, stage, os.replace | WIRED | Disposable synthetic bundle test verifies artifacts/hashes and unsafe path failures. |
| Builder/load_policy | JSON policy schema | Manual validation | PARTIAL — WARNING | The schema file itself is not read at runtime; document or remove the duplicated contract after reconciliation. |

### Data-Flow Trace (Level 4)

No dynamic UI belongs to this phase; equivalent traces cover its serialized analytical outputs.

| Artifact | Data variable | Source | Real data | Status |
|---|---|---|---|---|
| Cost/economics family | cost rows, cogs, ratios | SQLite cost components/allocations and sales_aggregates | Yes | FLOWING, arithmetic/status defects |
| Inventory/purchase family | custody and receipt units | SQLite unique movement, receipt, count, loan and reservation rows | Yes | FLOWING |
| Finance family | obligations, targets, horizons | SQLite obligation/payment/cash/evidence/budget rows | Yes | FLOWING with admissibility defect |
| Normalized cash rows | metrics | project_cash.horizons.layers_cents | Yes upstream | DISCONNECTED for RECONCILED/COMMITTED/EXPECTED |
| Learning family | return/defect rates | SQLite sales and quality rows | Yes | FLOWING at incorrect cohort grain |
| Public readiness | allowlisted exception fields | Canonical exceptions and SKU variant codes | Yes | FLOWING, fixed public allowlists |
| Registry | definition dictionaries | 15 selected definitions | Static metadata by design | Incomplete coverage of published decision measures |

### Behavioral Spot-Checks

Existing tests and additional verifier commands were run independently, not inferred from summaries. In-memory checks used `parse_pack` on the checked-in synthetic pack, the actual STRICT schema and production projection functions; only the specified synthetic inputs were varied. End-to-end fixture checks below used disposable directories and the real intake/build functions. No repository source or accepted cut was mutated.

| Behavior | Command / exact setup | Result | Status |
|---|---|---|---|
| Phase 2 focused suite | `.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_operating_marts_*.py' -v` | 22 tests, 4.785 seconds, exit 0 | PASS |
| Repository regression | `.venv/Scripts/python.exe -m unittest discover -s tests -v` | 172 tests, 57.350 seconds, exit 0 | PASS |
| COGS partition invariance | Python stdin, in-memory schema; one 101-cent component, quantity_basis=3, three one-unit sales on Sep 15/16/17; compare `realized_economics(..., Sep15, Sep18)` with three one-day calls | Combined 101; daily `[34,34,34]`, sum 102 | FAIL |
| Estimated quality propagation | Python stdin; disposable synthetic pack with complete sales/cost coverage and component quality ESTIMATED, validated through build_operating_workspace/bind_cut | `project_cost.status=ESTIMATED`; `realized_economics.status=MEASURED` | FAIL |
| Mixed cohort maturity | Python stdin; in-memory production projection, 10 deliveries Sep15 and 90 Oct20, one linked physical return on Oct1, as_of Oct21, policy maturity 30 days | `{'numerator':1,'denominator':100,'value':'0.01','status':'MEASURED'}` | FAIL |
| Valid observed inflow | Python stdin; append independent 100-cent RECONCILED INFLOW with unique source/event identity, no obligation/payment, increase observed closing balance by 100; real Phase 1 build/bind, then project_cash | Phase 1 valid; Phase 2 raises `settled cash lacks payment evidence` | FAIL |
| Valid ZERO unmet domain | Python stdin; keep unmet CSV header, delete its observations, set metadata coverage ZERO; real Phase 1 build then build_operating_marts | Phase 1 valid; `metric registry and emitted rows differ`; output root absent | FAIL |
| Normalized cash-layer wiring | Python stdin; production `_collect` on in-memory checked-in synthetic rows | Fact keys RECONCILED/COMMITTED/EXPECTED exist; normalized layer dimensions only undated_cents/scenario_cents for both horizons | FAIL |

The extra stdin checks each finished in under 3 seconds. The 57-second regression is the requested test suite, not a bounded spot-check. No server or external service was started. `scripts/verify_v2.py` was inspected but not rerun in this verification; earlier SUMMARY claims about that driver are not counted as fresh evidence. Existing final regression and the reproduced Phase 2 blockers suffice for this failing verdict.

### Probe Execution

No declared `probe-*.sh` or conventional shell probe was found. Not applicable. Python tests and stdin counterexamples were independently executed as recorded above.

### Requirements Coverage

All MET-01..07 appear in plan frontmatter; no Phase 2 requirement is orphaned.

| Requirement | Source plan | Description | Status | Evidence |
|---|---|---|---|---|
| MET-01 | 02-01 | Versioned exact cost and economics | BLOCKED | Partition changes COGS; estimated status lost downstream. |
| MET-02 | 02-01 | Canonical units and custody | SATISFIED | Actual event/count/custody code and focused negative controls. |
| MET-03 | 02-02 | Obligations and layered 8/13-week cash | BLOCKED | Valid independent cash inflows rejected; normalized layers omitted. |
| MET-04 | 02-03 | Eligible product learning | BLOCKED | Mixed mature/immature denominator and absent cohort restriction. |
| MET-05 | 02-02 | Distinct reconciled budget/drop/channel states | SATISFIED for tested canonical contract | Native-grain source bridge, payment non-additivity, residual cent controls and complete/partial headroom tests pass. |
| MET-06 | 02-03 | Governed exceptions and sales privacy | SATISFIED | Deterministic IDs, policy owner/action, due/closure fields, unresolved missing evidence, exact public field/category/value validation. |
| MET-07 | All three | Complete definitions for every metric | BLOCKED | Extra family measures lack definitions; selected-row equality hides omissions and rejects legitimate empty domains. |

### Anti-Patterns Found

No unreferenced TBD/FIXME/XXX or TODO/HACK/PLACEHOLDER markers were found in the phase implementation/test/model/policy files. Null returns inspected are legitimate undefined-ratio/no-issue outcomes. There are no placeholder modules; these are semantic and wiring failures.

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| alma/operating_cost_inventory.py | 173 | Per-call residual ordinal | BLOCKER | Report partition changes cents. |
| alma/operating_cost_inventory.py | 198 | MEASURED whenever complete | BLOCKER | Estimated economics mislabeled. |
| alma/operating_learning_exceptions.py | 238 | min(sales_date) as pooled maturity date | BLOCKER | Immature deliveries dilute mature rates. |
| alma/operating_marts.py | 158 | Consumer key names differ from producer | BLOCKER | Silent loss of three normalized cash layers. |
| alma/operating_marts.py | 180 | Registry set equality with emitted rows | BLOCKER | Zero-event domain blocks unrelated results. |
| tests/test_operating_marts_learning.py | 17 | Scalar maturity helper only | WARNING | Passing test does not exercise actual multi-cohort projector. |

### Disconfirmation Pass

- **Partially met requirement:** MET-07 validates all selected normalized definitions, but it does not cover every published decision measure.
- **Misleading passing test:** The scalar mature_return_rate test proves a single cohort's date comparison. It cannot prove project_learning's pooled date and denominator are correct. Similarly, the 101-cent allocator test does not prove COGS remains additive after window/channel filtering.
- **Uncovered input/error path:** A valid reconciled inflow without a payable payment_id passes Phase 1 and fails Phase 2. The existing cash test only supplies a settled payable outflow.

### Human Verification Required

None for this synthetic analytical phase, consistent with `02-VALIDATION.md`. Owner policy approval, fiscal treatment, real-cut correctness and adoption remain EXT-01..03; they neither excuse these implementation failures nor become new Phase 2 approval gates.

### Deferred-Item Review

The full milestone roadmap was checked. Phase 3 owns interpretation/review/decision carry-forward, Phase 4 owns portal/workbooks, and Phase 5 owns acceptance/release. None explicitly defers exact COGS, cohort maturity, cash input support, truthful source coverage or metric registry completeness. All five groups remain current Phase 2 gaps.

### Gaps Summary

Close the five frontmatter gap groups before advancing the phase. Existing test success is useful regression evidence, but it does not falsify the reproduced counterexamples. After repair, rerun affected projector/bundle tests with these concrete inputs, then the full required acceptance gates. No overrides were applied or proposed: these are implementation defects, not intentional equivalent designs.

---

_Verified: 2026-09-23T05:31:00Z_  
_Verifier: independent gsd-verifier; report only, no commit_
