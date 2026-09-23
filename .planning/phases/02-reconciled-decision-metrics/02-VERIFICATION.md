---
phase: 02-reconciled-decision-metrics
verified: 2026-09-23T06:31:09Z
status: gaps_found
score: 7/10 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 2/10
  gaps_closed:
    - "Canonical COGS now preserves cents across daily/channel partitions and estimated economics remains ESTIMATED."
    - "Mature returns and defects now use selected eligible delivery cohorts."
    - "Valid observed inflows are accepted and all five cash layers have normalized rows."
    - "Every existing family decision-measure path now has a semantic definition and normalized counterpart."
  gaps_remaining:
    - "Missing cash with retained independent balance evidence still blocks publication of unrelated families."
  regressions:
    - "New semantic daily cash forecasts and minimum projections are labeled MEASURED."
gaps:
  - truth: "Missing source coverage blocks only dependent complete metrics and preserves unrelated families."
    status: failed
    reason: "A valid MISSING cash_events domain with retained observed opening/closing evidence fails publication with 'unknown metric has a value'. The current empty-cash test removes the independent balance domain too, hiding this case."
    artifacts:
      - path: alma/operating_finance_marts.py
        issue: "project_cash retains actual_movements_cents=0 and horizon zero sums when missing events still have an observed scenario."
      - path: alma/operating_marts.py
        issue: "_semantic_status marks numeric cash values UNKNOWN, then _semantic_publication passes those numbers to MetricRow; further raw-zero versus normalized-null cash-layer mismatches also require consistent handling."
    missing:
      - "Keep recorded source facts distinct from authoritative missing-domain measures; emit null UNKNOWN cash measures consistently in families and normalized rows."
      - "Preserve independent balance evidence and publish unrelated families when cash movements are MISSING."
      - "Add a real intake-to-bundle case with cash_events MISSING/null windows and cash_balance_evidence retained with equal opening/closing."
  - truth: "Expected/scenario-derived cash projections retain forecast status in every normalized semantic measure."
    status: failed
    reason: "A complete-coverage EXPECTED outflow of 13 cents is ESTIMATED in its layer, but its derived daily close and daily minimum of 1099987 cents are MEASURED."
    artifacts:
      - path: alma/operating_marts.py
        issue: "_semantic_status falls back to MEASURED for cash when source coverage is complete; daily_closes_cents and daily_minimum_cents do not inherit forecast semantics."
    missing:
      - "Assign metric-specific status from the meaning and dependencies of each cash measure; complete source coverage does not turn a forecast into an observation."
      - "Mark forecast daily closes/minima and weekly EXPECTED/SCENARIO aggregates consistently, preserving PARTIAL/UNKNOWN when coverage requires it."
      - "Read final metric_rows.json in a regression test and verify projected values remain ESTIMATED beside a separately MEASURED reconciled close."
  - truth: "The canonical intake can supply dated expected/committed/scenario events for genuine future 56-day and 91-day cash views."
    status: failed
    reason: "With cutoff 2026-09-21, a correctly shaped EXPECTED event dated 2026-09-22 is rejected by Phase 1 as value.after_cutoff at cash_events.csv:4:event_date. The input contract currently prevents future forecast facts from reaching the implemented horizons."
    artifacts:
      - path: alma/operating_interchange.py
        issue: "Line 104 exempts promised_date, due_date and period_end only; cash forecast event_date is subject to the observed-event cutoff."
      - path: tests/test_operating_marts_publication.py
        issue: "The all-layers publication fixture dates every forecast on the cutoff day, so it does not exercise future input dates."
    missing:
      - "Reconcile the Phase 1/Phase 2 temporal contract explicitly: allow future dates only for eligible forecast cash layers while preserving the cutoff guard for reconciled/observed facts."
      - "Build a genuine source pack with nonzero future committed/expected/scenario cash and verify day 55/56/90/91 boundaries through intake, bundle, and normalized rows."
---

# Phase 2: Reconciled Decision Metrics Re-verification

**Phase Goal:** Analysts and owners can inspect one exact, coverage-aware account of costs, units, cash, demand learning, and actionable exceptions for a cut.

**Status:** gaps_found

**Score:** 7/10 must-haves verified

**Re-verification:** Yes — after Plan 02-04 gap closure.

**Inspected HEAD:** `06e84c850fe320188ca5fda589d636833fd1019d`

The original arithmetic, cohort, observed-inflow and semantic-catalog failures were repaired. A remaining missing-domain case, a forecast-status regression and an input-boundary failure still prevent the complete goal. No overrides exist. Only this report was edited; synthetic tests used disposable directories or in-memory SQLite.

## Re-verification Evidence

The verification read Plan 02-04 and its summary, compared actual changes from the original inspected commit, reran the focused tests and historical acceptance driver, repeated the original arithmetic/cohort counterexamples independently, and added bounded checks at the repaired cash/publication boundaries. Summary pass claims were not used as evidence.

| Previous blocker | New evidence | Disposition |
|---|---|---|
| Partition-dependent COGS | `realized_economics` orders canonical SKU sales before reporting filters and tracks ordinals per version. Independent replay returns combined 101 and daily [34,34,33], sum 101. | CLOSED |
| Estimated economics promoted to MEASURED | Estimated quality is accumulated from selected cost versions and returned as ESTIMATED; real intake-to-bundle serialization tests assert COGS, contribution and ratios. | CLOSED |
| Pooled immature cohort | Quality SQL restricts to selected delivery cohorts; per-cohort latest delivery controls maturity. Independent original replay returns 1/10 = 0.1, while the 90-unit recent cohort stays UNKNOWN. | CLOSED |
| Observed inflow rejected / cash layers omitted | Cash permits independent observed source evidence; serializer consumes nested layers_cents. Real bundle test proves 100, -11, -13, -7, -5 for RECONCILED/COMMITTED/EXPECTED/UNDATED/SCENARIO in both horizons. | CLOSED for original cases; further cash gaps below |
| Valid zero-event domain blocked | ZERO and MISSING unmet demand now publish without fabricated demand rows. Sales/budget/payment/cash empty fixtures pass. | PARTIALLY CLOSED: MISSING cash with retained balance evidence fails |
| Incomplete semantic registry | Explicit family-path formulas, metric/fact catalog, generated definitions and normalized rows are independently compared before publication. Missing definition+row and unclassified-field negatives fail before output. | CLOSED structurally; forecast measure status regression remains |

## Goal Achievement

### Observable Truths

The original ten truths and denominator are preserved for comparison. Plan 02-04 adds specificity to those same obligations rather than a reduced scope.

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | An owner can compare known cost, complete cost, markup, gross margin, and contribution by effective cost version; allocations reconcile to the cent and incomplete costs remain unknown. | VERIFIED | Canonical pre-filter ordinals, cost version selection, missing component/coverage controls, full semantic cost/economics definitions; independent 101-cent replay passes. |
| 2 | An analyst can reconcile ordered, received, inspected, accepted, rejected, non-sellable, loaned, reserved, and available units once, with no duplicate receipt or return event inflating stock. | VERIFIED | Existing purchase/custody/count-variance controls remain unchanged and all focused regression cases pass. |
| 3 | An owner can view outstanding obligations and applied payments alongside separate reconciled, committed, expected, undated, and scenario cash in eight- and thirteen-week windows; budget and drop/channel financial states reconcile without double counting. | FAILED — BLOCKER | Original layers now flow, but future forecast facts are rejected at intake and forecast daily/minimum measures are mislabeled MEASURED. |
| 4 | An owner can inspect launch sell-through, variant mix, mature return/quality rates, stock exposure, and recorded unmet demand with explicit denominators, windows, and coverage; an exposed stockout does not become a weak-preference claim. | VERIFIED | Independent mixed-cohort replay returns 1/10; tests cover outside-cohort exclusions, defect denominator, stock exposure and recorded-demand lower bounds. |
| 5 | Sales-facing readiness and quality/loan exceptions show an owner, action, date, and closure state without internal cost disclosure; every metric exposes its formula, unit, grain, sources, unknown rule, guardrail, owner, and decision use. | VERIFIED | Public category/field/value controls remain; semantic registry now declares all existing family measures and compares actual family paths with normalized counterparts. Runtime status accuracy is separately failed under truths 3/10. |
| 6 | Missing Phase 1 input or incomplete source coverage blocks only dependent complete metrics and never converts unknown into zero. | FAILED — BLOCKER | Real Phase 1-valid MISSING cash plus retained observed balances aborts the entire mart bundle. |
| 7 | Documented and estimated complete costs remain distinguishable in dependent economics. | VERIFIED | Corrected estimate propagation and final bundle tests preserve ESTIMATED for COGS, contribution, markup and margins. |
| 8 | One obligation balance retains recorded unpaid under partial application coverage while withholding authoritative outstanding. | VERIFIED | Original balance tests pass; missing payments retain recorded exposure while authoritative outstanding/headroom is withheld. |
| 9 | Unavailable variants, immature/unlinked return cohorts and absent unmet-demand logging cannot produce false preference or zero-demand claims. | VERIFIED | Mature and recent cohorts are separated; unlinked/outside evidence retained; empty demand has no fabricated channel/event rows. |
| 10 | All Phase 2 metric definitions and results validate together; missing/stale policy, unsafe paths or failed reconciliation publish no derived bundle. | FAILED — BLOCKER | Completeness, path/hash/atomic controls work, but the semantic status fallback publishes EXPECTED-derived daily cash as MEASURED. |

**Score:** 7/10 verified. Three failed truths require repair; no truth is merely uncertain.

### Required Artifacts and Wiring

| Artifact / link | Existence and substance | Wiring / result |
|---|---|---|
| `alma/operating_cost_inventory.py` → canonical sales/cost SQL | Substantive | VERIFIED: ordinals allocated before date/channel selection; estimates preserved |
| `alma/operating_learning_exceptions.py` → `models/operating_learning_exceptions.sql` | Substantive | VERIFIED: selected-cohort SQL and per-cohort eligibility feed aggregate and cohort metric rows |
| `alma/operating_finance_marts.py` → shared contracts/finance SQL | Substantive | PARTIAL: ordinary obligations/finance work; retained-balance missing-cash branch incomplete |
| `alma/operating_marts.py` → five cash layers | Substantive | WIRED: all five normalized layer rows now produced for both horizons |
| `alma/operating_marts.py` → semantic catalog/registry | Substantive | WIRED with BLOCKER: definitions/values linked, cash projection status inference incorrect |
| `alma/operating_mart_contracts.py` → coverage | Substantive | VERIFIED for tested MISSING null-window rule; downstream numeric handling remains defective |
| `alma/operating_interchange.py` → future cash forecast input | Existing Phase 1 implementation | NOT WIRED for future forecasts: generic date guard prevents forecast events after cutoff |
| Policy JSON, cost/finance SQL, original three test modules | Present, substantive | Previous passing controls regress successfully |
| `tests/test_operating_marts_publication.py` | New substantive integration tests | Seven tests pass; remaining cases identify gaps in its empty-cash and forecast fixtures |
| Builder → private atomic directory | Substantive | VERIFIED: unsafe/missing/tampered inputs and semantic mismatch leave no accepted output |

The policy schema remains documentation paired with manual runtime validation, as noted previously. This informational implementation choice did not cause the three reproduced failures and is not treated as an additional human approval gate.

### Data-Flow Trace

| Output | Upstream data | Result |
|---|---|---|
| Cost/COGS/margins | Actual verified cost components and canonical sales | FLOWING; original cent/estimate defects fixed |
| Cohort and eligible aggregate rates | Selected delivery cohorts and SQL-linked quality events | FLOWING at correct grain |
| Five cash-layer rows | Actual horizon.layers_cents plus undated/scenario fields | FLOWING |
| Daily projected close/minimum | Reconciled starting balance plus commitments/expectations | FLOWING, but status wrongly MEASURED |
| Missing cash with independent balances | Empty MISSING cash domain plus observed equal opening/closing | BLOCKED in semantic publication |
| Future forecast horizon | Source cash event dated after cut | BLOCKED before workspace: value.after_cutoff |
| Catalog and normalized measures | Explicit finite family paths traversed against actual families | FLOWING; same meaning/status requires the remaining correction |
| Public sales readiness | Allowlisted canonical exception evidence | FLOWING; no new internal-cost fields |

## Commands and Results

| Check | Command / fixture | Result |
|---|---|---|
| Focused suite | `.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_operating_marts_*.py' -v` | PASS: 33 tests in 7.828s |
| Full regression and historical scenarios | `.venv/Scripts/python.exe scripts/verify_v2.py --output build/verification-v2-phase2-reverification` | PASS: 183 tests, zero failures/errors; all six expected scenario outcomes pass; receipt elapsed 80.18s |
| Original exact COGS counterexample | Python stdin, in-memory STRICT schema; one 101-cent/3-unit cost and one-unit sales Sep15/16/17; combined and daily calls | PASS: 101 versus [34,34,33] = 101 |
| Original exact cohort counterexample | Python stdin, in-memory schema; 10 deliveries Sep15, 90 Oct20, one physical return linked to Sep15, as_of Oct21 | PASS: numerator 1 / denominator 10 = 0.1; recent cohort UNKNOWN |
| Original observed cash, empty unmet and estimated serialization | Focused real intake-to-bundle tests with validated disposable packs | PASS |
| Remaining missing-cash case | Clear only cash_events; set MISSING/null windows; retain observed cash_balance_evidence and set closing equal opening; real intake then builder | FAIL: intake succeeds; bundle raises `ValueError: unknown metric has a value` |
| Forecast semantic status | Complete cash coverage; add 13-cent EXPECTED outflow dated cutoff; real intake/bundle; read final metric_rows.json | FAIL: layer -13 ESTIMATED; daily close and daily minimum 1099987 MEASURED |
| Genuine future expected event | Cutoff Sep21, append correctly shaped EXPECTED event Sep22 with unique IDs/source ref and no obligation/payment | FAIL at intake: `value.after_cutoff at cash_events.csv:4:event_date` |
| Anti-pattern scan | `rg -n 'TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER' alma models tests -g '*operating*'` | No matching debt/stub markers |

The bounded stdin checks each finished below three seconds; full acceptance is a separate requested gate. The acceptance driver itself reran the entire 183-test suite, so a duplicate standalone full run was unnecessary. Fresh receipts are in `build/verification-v2-phase2-reverification/verification.json` and `tests.log`; these are current local execution evidence, not claims from the summary.

### Exact Remaining Reproduction Inputs

1. **Retained independent balances with missing movements:** Copy the synthetic pack into a temporary directory. Write only the original header to `cash_events.csv`; set its coverage to `{"status":"MISSING","window_start":null,"window_end":null}`. In `cash_balance_evidence.csv`, set closing_balance_cents equal to its existing opening_balance_cents (2000000), retaining OBSERVED evidence and dates. Leave other domains unchanged. `build_operating_workspace` succeeds. `build_operating_marts` fails with the error above.
2. **Forecast promoted to observation:** Copy the synthetic pack. Set cash_events and cash_balance_evidence coverage COMPLETE. Append a unique EXPECTED/OUTFLOW event for 2026-09-21, amount 13, empty obligation/payment/supersedes fields, and a synthetic source reference. Keep the independent close 1100000. Publication succeeds, but `cash.horizons.56.daily_closes_cents.2026-09-21` and `cash.horizons.56.daily_minimum_cents` normalize 1099987 as MEASURED. The underlying EXPECTED layer is correctly ESTIMATED.
3. **Future forecast blocked:** Use the same well-formed EXPECTED event with event_date 2026-09-22 and cutoff 2026-09-21. The generic date coercion checks event_date against cutoff without a cash-layer exception. This is an input-contract failure, not missing real client data.

## Requirements Coverage

| Requirement | Plans | Status | Evidence |
|---|---|---|---|
| MET-01 | 02-01, 02-04 | SATISFIED | Original arithmetic and estimate failures repaired and independently rechecked |
| MET-02 | 02-01, 02-04 | SATISFIED | Unit/custody/variance regressions pass |
| MET-03 | 02-02, 02-04 | BLOCKED | Missing-cash publication, forecast status and future-event intake gaps |
| MET-04 | 02-03, 02-04 | SATISFIED | Cohort-specific maturity and numerator/denominator restrictions verified |
| MET-05 | 02-02, 02-04 | SATISFIED for tested canonical contract | Source-grain states, payment non-additivity and residual allocations preserved |
| MET-06 | 02-03, 02-04 | SATISFIED | Governed exception and public projection tests remain green |
| MET-07 | All plans | Definitions satisfied; semantic result validation BLOCKED | Complete catalog exists, but projected cash gets the wrong measurement status |

All seven requirements remain claimed by plans; no orphaned Phase 2 requirement was found.

## Anti-Patterns and Disconfirmation

No stubs or unreferenced debt markers were found. The remaining defects are boundary and semantic failures.

- **Partially met requirement:** MET-03 can calculate horizons but cannot import a nonzero forecast dated after the cutoff.
- **Passing test with limited scope:** The all-layer bundle test dates committed/expected/scenario events on the cutoff itself. Its passing result does not prove future 56/91-day data can traverse intake.
- **Uncovered error path:** The empty cash matrix clears both cash events and independent balances. It bypasses the branch reached when balances remain and only movements are missing.
- **Status regression:** Generic complete-coverage handling labels derived daily/minimum projections MEASURED even when their only change from the observed close is an EXPECTED flow.

## Probe Execution

No explicit or conventional `probe-*.sh` is declared for this phase. The Python acceptance driver was independently executed and its fresh result recorded above.

## Human Verification Required

None for the synthetic Phase 2 contract. EXT-01..03 still govern real owner approval, fiscal policy and real-client adoption. These are outside this phase and do not explain the reproduced software failures.

## Deferred-Item Review

No later phase explicitly owns these three corrections. Phase 3 consumes the metrics, Phase 4 packages the experience, and Phase 5 verifies/releases it. The future-event restriction originates in Phase 1, but the Phase 2 plan explicitly requires reconciling missing source semantics before dependent metrics are declared complete. It therefore remains a Phase 2 dependency gap, not an accepted deferral.

## Conclusion

The repair substantially improves the phase: seven of ten observable truths now pass and the original high-impact arithmetic/cohort failures are closed. Keep the phase blocked until the three structured gaps above are corrected and their real intake-to-bundle counterexamples pass.

---
_Verifier: independent gsd-verifier. Report updated only; no commit._
