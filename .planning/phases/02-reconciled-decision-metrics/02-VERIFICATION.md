---
phase: 02-reconciled-decision-metrics
verified: 2026-09-23T07:06:57Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/10
  gaps_closed:
    - "MISSING cash movements with retained observed balances now publish null UNKNOWN dependent measures and preserve unrelated families."
    - "Forecast-derived cash daily closes and minima retain ESTIMATED status beside the separately MEASURED reconciled close."
    - "Future COMMITTED, EXPECTED and SCENARIO events traverse canonical intake and the 56/91-day horizons; future RECONCILED events remain rejected."
  gaps_remaining: []
  regressions: []
---

# Phase 2: Reconciled Decision Metrics Verification

**Phase Goal:** Analysts and owners can inspect one exact, coverage-aware account of costs, units, cash, demand learning, and actionable exceptions for a cut.

**Verified:** 2026-09-23T07:06:57Z

**Status:** passed

**Score:** 10/10 must-haves verified

**Re-verification:** Yes — after Plan 02-05, including hardening commit `9caf192`.

**Inspected HEAD:** `955ba74454e902df91c13622d4c63a7df8b54a84`

All three remaining cash counterexamples now pass through real synthetic source-pack intake and final artifact serialization. The focused suite and independently executed full acceptance gate pass. No override was applied. This verification covers the deterministic synthetic analytical contract; it does not assert real-client adoption, real policy approval or native analytical-agent execution.

## Re-verification Evidence

The verifier inspected actual implementation changes, the Phase 2 roadmap contract, prior verification, Plan 02-05 and its summary. Previously passing behavior received regression checks; each remaining gap received full implementation, wiring and execution checks. Summary claims were not used as execution evidence.

The verification progression is 2/10 initially, 7/10 after Plan 02-04, and 10/10 after Plan 02-05. The original COGS/cohort counterexamples were independently replayed in the preceding verification; their code remains intact and their regression tests passed again in this run.

| Gap | Actual correction and independent result | Status |
|---|---|---|
| Missing movements with retained balances abort the bundle | `project_cash` explicitly withholds movement-dependent values under MISSING/ERROR while retaining observed scenario/evidence. Real intake with MISSING cash events and equal retained OBSERVED balances yields 27 null UNKNOWN cash measures; unrelated inventory and other families publish. | CLOSED |
| Forecast daily/minimum values become MEASURED | `_semantic_status` distinguishes reconciled observations from projected measures and respects coverage. Final rows retain reconciled close 1100000 MEASURED and projected daily close/minimum 1099987 ESTIMATED. | CLOSED |
| Intake rejects genuine future cash forecasts | Row-aware validation allows future dates only for typed COMMITTED/EXPECTED/SCENARIO cash rows. Real future events at offsets 55/56/90/91 reach the horizons with correct half-open boundaries; future RECONCILED still fails `value.after_cutoff`. | CLOSED |

## Goal Achievement

### Observable Truths

The original ten truths and denominator are preserved. Roadmap success criteria and additional plan truths remain covered; gap-closure plans do not reduce the contract.

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | An owner can compare known cost, complete cost, markup, gross margin, and contribution by effective cost version; allocations reconcile to the cent and incomplete costs remain unknown. | VERIFIED | Effective-version selection, canonical pre-filter sales ordinals and missing component/coverage controls in `operating_cost_inventory.py`. Prior independent 101-cent replay produced daily [34,34,33]; current partition/residual and publication regressions pass. |
| 2 | An analyst can reconcile ordered, received, inspected, accepted, rejected, non-sellable, loaned, reserved, and available units once, with no duplicate receipt or return event inflating stock. | VERIFIED | Purchase/custody/count-variance and receipt/return conservation controls remain substantive and their focused/full regression cases pass. |
| 3 | An owner can view outstanding obligations and applied payments alongside separate reconciled, committed, expected, undated, and scenario cash in eight- and thirteen-week windows; budget and drop/channel financial states reconcile without double counting. | VERIFIED | Canonical obligations/applications, all five serialized cash layers and distinct budget states pass. Independent real future intake proves both horizons; projected statuses and scenario exclusion from baseline are correct. |
| 4 | An owner can inspect launch sell-through, variant mix, mature return/quality rates, stock exposure, and recorded unmet demand with explicit denominators, windows, and coverage; an exposed stockout does not become a weak-preference claim. | VERIFIED | Selected-cohort SQL and per-cohort latest-delivery maturity retain excluded evidence. Prior independent mixed-cohort replay produced 1/10, recent 90-unit cohort UNKNOWN; current cohort, exposure and unmet-demand tests pass. |
| 5 | Sales-facing readiness and quality/loan exceptions show an owner, action, date, and closure state without internal cost disclosure; every metric exposes its formula, unit, grain, sources, unknown rule, guardrail, owner, and decision use. | VERIFIED | Exception projection uses explicit public field/category/value controls. Semantic registry defines existing family measures with required metadata; normalized rows and public allowlist regressions pass. |
| 6 | Missing Phase 1 input or incomplete source coverage blocks only dependent complete metrics and never converts unknown into zero. | VERIFIED | ZERO/MISSING domain matrix and retained-independent-balance counterexample pass. Missing cash produces null UNKNOWN consistently in family and normalized output while unrelated families remain available. |
| 7 | Documented and estimated complete costs remain distinguishable in dependent economics. | VERIFIED | Selected estimated cost quality propagates through COGS, contribution, markup and margins; final JSON/CSV publication regressions pass. |
| 8 | One obligation balance retains recorded unpaid under partial application coverage while withholding authoritative outstanding. | VERIFIED | Obligation/application coverage tests preserve recorded exposure and withhold authoritative outstanding/headroom for incomplete payment evidence. |
| 9 | Unavailable variants, immature/unlinked return cohorts and absent unmet-demand logging cannot produce false preference or zero-demand claims. | VERIFIED | Cohort eligibility, unlinked/outside evidence, exposure and empty-demand cases pass without fabricated demand channel/event rows. |
| 10 | All Phase 2 metric definitions and results validate together; missing/stale policy, unsafe paths or failed reconciliation publish no derived bundle. | VERIFIED | Explicit semantic catalog independently checks actual family paths, definitions and normalized counterparts. Invalid catalog/policy/hash/path/reconciliation cases fail before accepted output; repaired cash statuses pass final-artifact assertions. |

**Score:** 10/10 truths VERIFIED. No FAILED or UNCERTAIN must-have remains.

### Required Artifacts

| Artifact | Substance and runtime evidence | Status |
|---|---|---|
| `alma/operating_cost_inventory.py` and cost/inventory SQL | Exact cost versions, cent allocation, inventory and purchase reconciliations feed the builder; regression cases execute those paths. | VERIFIED |
| `alma/operating_finance_marts.py` and finance SQL | Canonical balances, five cash layers, half-open horizons, coverage withholding and budget/drop/channel states execute from canonical facts. | VERIFIED |
| `alma/operating_learning_exceptions.py` and learning SQL | Selected-cohort numerators/denominators, exposure, demand and governed exceptions produce final family rows. | VERIFIED |
| `alma/operating_mart_contracts.py` and policy artifacts | Metric row metadata/status invariants, coverage and explicit policy authority are consumed during publication. | VERIFIED |
| `alma/operating_marts.py` | Finite semantic catalog, definitions, normalized rows, private public-view projection and atomic output are substantive and exercised. | VERIFIED |
| `alma/operating_interchange.py` | Future-date exception is evaluated after row typing and level validation; observed cutoff controls remain. | VERIFIED |
| Intake and four operating-mart test modules | Source-pack-to-bundle, final JSON/CSV, exact arithmetic, missing domains and negative publication checks execute successfully. | VERIFIED |

The GSD artifact query against `02-05-PLAN.md` passed all six declared artifacts. Manual inspection and runtime tests establish substance and wiring beyond that structural result. The policy schema remains documentation paired with manual runtime validation; required runtime rules are tested.

### Key Link Verification

| From | To | Connection and evidence | Status |
|---|---|---|---|
| Typed source-pack rows | Canonical workspace | `_coerce_value` and row-aware cash date validation preserve event dates, identities and cutoff. Real future-layer positive and observed-date negative fixtures traverse this path. | WIRED |
| Canonical sales, costs and stock facts | Cost/inventory families | SQL and exact Python arithmetic read actual accepted facts; no static output substitutes for them. | WIRED |
| Canonical obligations/applications/cash | Finance families | `project_cash` and balance/state builders read accepted records, retain coverage/evidence and exclude scenario flows from baseline. | WIRED |
| Finance family values/status/evidence | Semantic registry and metric rows | `_semantic_publication` emits the corresponding values and metric-specific status; cash lineage is restricted to relevant horizon/layer/week dependencies. | WIRED |
| Selected delivery cohorts | Learning rates | SQL filters eligible cohort facts and aggregate calculation preserves maturity and exclusions. | WIRED |
| Exception facts | Sales-facing readiness | Explicit field/value allowlists remove internal cost content while retaining owner/action/date/closure. | WIRED |
| Registry and result validation | Private atomic publication | Invalid definitions, policy, paths, hashes and reconciliation stop accepted output; successful bundles expose final JSON/CSV. | WIRED |

### Data-Flow Trace

| Output | Actual source and transformation | Status |
|---|---|---|
| Cost, COGS and margins | Verified cost components and canonical sales; version/ordinal allocations | FLOWING |
| Learning and cohort rates | Selected delivery cohorts and linked quality evidence; eligibility-aware aggregation | FLOWING |
| Cash actuals and independent reconciled close | Accepted reconciled events plus retained observed balance evidence | FLOWING |
| Forecast layers, daily closes and minima | Accepted committed/expected/scenario events within each horizon; scenario isolated, projected outputs ESTIMATED | FLOWING |
| Missing cash domain | MISSING movement coverage and retained balance evidence; dependent measures null UNKNOWN, other families still published | FLOWING |
| Catalog and normalized measures | Explicit family paths and runtime values checked against definitions before serialization | FLOWING |
| Public readiness | Governed exception facts projected through allowlists | FLOWING |

This phase has CLI, relational data and serialized reports, not a UI. Level 4 checks followed actual accepted source data through generated artifacts.

## Commands and Results

| Check | Command or independently constructed fixture | Result |
|---|---|---|
| Focused operating-mart suite | `.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_operating_marts_*.py' -v` | PASS: 37 tests in 13.276s |
| Full suite and acceptance scenarios | `.venv/Scripts/python.exe scripts/verify_v2.py --output build/verification-v2-phase2-final-independent` | PASS: 189 tests, zero errors/failures; test time 69.028s, complete receipt elapsed 116.41s |
| Artifact checks | `node C:/Users/erick/.codex/get-shit-done/bin/gsd-tools.cjs query verify.artifacts .planning/phases/02-reconciled-decision-metrics/02-05-PLAN.md` | PASS: 6/6 artifacts |
| Missing movement counterexample | Python stdin; copied synthetic pack, real intake, real builder and final JSON readback | PASS: 27 null UNKNOWN cash measures; unrelated families publish |
| Projection/observation counterexample | Python stdin; complete cash coverage plus cutoff-day EXPECTED OUTFLOW 13 | PASS: observed 1100000 MEASURED; projected daily close and both horizon minima 1099987 ESTIMATED |
| Genuine future horizon boundaries | Python stdin; each future forecast layer at offsets 55/56/90/91 | PASS: each layer -11 in 56 days and -41 in 91 days; baseline minima 1099978 and 1099918 exclude SCENARIO |
| Future observed event negative control | Python stdin; RECONCILED OUTFLOW 13 one day after cut | PASS: intake rejects `value.after_cutoff at cash_events.csv:4:event_date` |
| Debt/stub marker scan | `rg -n 'TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER' alma models tests -g '*operating*'` (alternation pattern) | No matches |

The independent bounded counterexample script completed in under two seconds. Full acceptance was the requested broader gate and included the entire suite, so no duplicate standalone full run was needed. Runtime was Python 3.12.14 / SQLite 3.53.1.

Fresh local receipts are `build/verification-v2-phase2-final-independent/verification.json` and `tests.log`. All six scenario expectations passed: normal, stock_pressure, promotion_illusion and cash_squeeze produce PASS; missing_cost correctly produces REVIEW; broken_link correctly produces BLOCKED without publishing its database. All three mechanism checks and replay/integrity checks passed. These are deterministic acceptance results, not proof of native analytical-agent execution.

### Exact Counterexample Inputs and Readback

1. **Missing movements with independent balances retained:** Copy the synthetic source pack into a temporary directory. Retain only the header in `cash_events.csv`, set coverage MISSING with null window bounds, and set the existing OBSERVED balance closing equal to opening 2000000. Leave other domains unchanged. Real intake succeeds; builder preserves `synthetic:scenario-observed` and evidence, withholds actual/reconciled/horizon dependent measures and publishes 27 null UNKNOWN cash rows. Inventory and other families remain available. Integration tests also cover complete independent balance coverage.

2. **Projected versus measured close:** Set cash-events and balance coverage COMPLETE. Append a unique EXPECTED/OUTFLOW event dated 2026-09-21 for 13 cents with synthetic source reference and empty obligation/payment/supersedes fields. Retain measured close 1100000. Read final `metric_rows.json`: `cash.reconciled_close_cents` is 1100000 MEASURED; `cash.horizons.56.daily_closes_cents.2026-09-21`, its daily minimum and the 91-day minimum are 1099987 ESTIMATED. This tests serialization, not only a finance helper.

3. **Future forecast boundaries and negative control:** From cutoff 2026-09-21, append unique COMMITTED, EXPECTED and SCENARIO OUTFLOW events at offsets 55, 56, 90 and 91, amounts 11, 13, 17 and 19 respectively. Link committed events to the existing open expense obligation; retain separate event/economic/source IDs. Actual intake and publication produce -11 per layer for [0,56), and -41 per layer for [0,91). The baseline minima are 1100000 - 2*11 = 1099978 and 1100000 - 2*41 = 1099918; scenario remains separate. Actual movements remain -900000 and cutoff remains `2026-09-21T23:59:59-07:00`. A separate future RECONCILED event fails intake with `value.after_cutoff`.

## Requirements Coverage

| Requirement | Source plans | Status | Evidence |
|---|---|---|---|
| MET-01 | 02-01, 02-04 | SATISFIED | Effective costs, deterministic cents, known/complete distinctions and estimated economics verified |
| MET-02 | 02-01, 02-04 | SATISFIED | Unit conservation, custody and variance regressions pass |
| MET-03 | 02-02, 02-04, 02-05 | SATISFIED | Canonical balances, five cash layers, genuine future horizons and missing-coverage semantics verified |
| MET-04 | 02-03, 02-04 | SATISFIED | Cohort eligibility, denominators, exposure and recorded unmet demand verified |
| MET-05 | 02-02, 02-04 | SATISFIED | Source-grain approved/committed/incurred/paid/outstanding/unallocated states and non-additivity controls pass |
| MET-06 | 02-03, 02-04 | SATISFIED | Governed exception queue and sales-facing confidentiality controls pass |
| MET-07 | 02-01 through 02-05 | SATISFIED | Required definition metadata, complete semantic catalog, normalized values, statuses and evidence validated |

All seven Phase 2 requirements are claimed by plans and supported by implementation evidence. No orphaned requirement was found. These statuses concern the defined synthetic canonical contract.

## Anti-Patterns and Disconfirmation

No blocking stub, unreferenced debt marker, disconnected data source or new regression was found in the inspected phase implementation. Empty values are intentional coverage withholding or empty-domain results, and their downstream meaning is tested.

The previous test blind spots are now covered: retained balances when movements are missing, final serialized projection status, and actual future forecast dates through intake. Negative controls continue to reject future observed facts, invalid layer/origin combinations, missing definitions, injected unclassified measures and invalid publication inputs. Green helper tests alone were not accepted as proof of these repaired boundaries.

## Probe Execution

No explicit or conventional `probe-*.sh` is declared for this phase. The Python acceptance driver was independently executed; its current result and evidence paths are recorded above.

## Human Verification Required

None for the synthetic Phase 2 contract. EXT-01..03 still govern real owner approval, fiscal policy and real-client adoption outside this phase. No visual, external integration or real-business outcome is claimed by this verification.

## Deferred Items and Remaining Gaps

None. No failed truth required deferral to a later phase. Phase 3 may consume the reconciled metrics under the existing synthetic-policy and coverage constraints.

---
_Verifier: independent gsd-verifier. Only this report updated; no commit._
