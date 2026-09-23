---
phase: 02
slug: reconciled-decision-metrics
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-22
---

# Phase 2 — Validation Strategy

Phase 2 is complete only when all seven `MET` requirements have exact synthetic hand oracles, source/cent/unit conservation, truthful coverage and policy status, private publication controls, and current v0.2/v0.3 regressions. Tests use Phase 1 synthetic source packs, temporary SQLite workspaces and disposable private roots. No real client cut is a test fixture.

## Test Infrastructure and Latency

| Property | Value |
| --- | --- |
| Runner | Python 3.11+ standard-library `unittest`, real SQLite and temporary directories |
| Wave 0 | Existing test infrastructure is sufficient; create the three assigned test files in each plan's first red stage, before production code |
| Cost/inventory focused | `C:\Users\erick\.pyenv\pyenv-win\versions\3.11.7\python.exe -m unittest discover -s tests -p test_operating_marts_cost_inventory.py -v` |
| Finance focused | `C:\Users\erick\.pyenv\pyenv-win\versions\3.11.7\python.exe -m unittest discover -s tests -p test_operating_marts_finance.py -v` |
| Learning/publication focused | `C:\Users\erick\.pyenv\pyenv-win\versions\3.11.7\python.exe -m unittest discover -s tests -p test_operating_marts_learning.py -v` |
| All Phase 2 focused | `C:\Users\erick\.pyenv\pyenv-win\versions\3.11.7\python.exe -m unittest discover -s tests -p test_operating_marts_*.py -v` |
| Full regression | `C:\Users\erick\.pyenv\pyenv-win\versions\3.11.7\python.exe -m unittest discover -s tests -v` |
| v0.2 acceptance | `C:\Users\erick\.pyenv\pyenv-win\versions\3.11.7\python.exe scripts/verify_v2.py --output build/verification-v2-phase2` |
| Latency target | Each focused feedback command should finish within 60 seconds; measure and record actual duration at execution. Full suite and `verify_v2.py` may exceed a minute and remain mandatory. No unmeasured runtime is asserted. |

Use the explicit interpreter after checking it exists and reports Python 3.11+ and SQLite 3.37+; if the path differs, record the selected equivalent interpreter in the execution summary. A task exits only after its focused command is green. The final 02-03 task runs all Phase 2 focused tests, the full suite, and `verify_v2.py` as automated checks on the final code state.

## Nyquist Sampling and Feedback Cadence

1. **Wave 0 and each task's red stage:** Create or extend the owned test module first. Run the focused command and confirm the new behavior fails for the expected reason. No separate test framework or scaffold package is needed.
2. **After each task:** Run its focused command; preserve a hand-computed expected cent/unit/ratio oracle and a negative control, including no artifact after a blocked publication.
3. **After 02-01:** Re-run the cost/inventory module with all 22 `SOURCE_NAMES` and semantic binding checks against the finished Phase 1 registry/schema. Verify the policy schema and synthetic artifact hash/status independently of the cut hash.
4. **After 02-02:** Run cost/inventory and finance focused commands. Check economic identity and supersession, observed opening/closing balance evidence, 56/91-day boundaries, source-to-target cents and unallocated balances.
5. **After 02-03:** Run all three focused modules, full `unittest` discovery, and `scripts/verify_v2.py` in the final task. Failed privacy, path, source/policy hash or reconciliation gates leave no accepted derived bundle.
6. **Before phase verification:** Re-run only checks affected by subsequent edits. Record measured runtimes and final pass evidence for the exact code; do not reuse old historical receipts for a changed implementation.

## Per-Task Verification Map

| Task | Wave | Requirements | Test and hand oracle | Automated gate | Status |
| --- | --- | --- | --- | --- | --- |
| 02-01 Task 1 | 1 | MET-07; input basis for MET-01..06 | Literal 22 Phase 1 `SOURCE_NAMES`, table/column semantic keys/dates/units/coverage, source hash, missing relation, separate policy schema/hash/status; missing/stale/unapproved/synthetic policy | Cost/inventory focused | Planned red/green |
| 02-01 Task 2 | 1 | MET-01, MET-07 | One SKU/cost version: 101 cents across three unit ordinals = 34+34+33; missing component, estimate, historical version, zero denominator | Cost/inventory focused | Planned red/green |
| 02-01 Task 3 | 1 | MET-02, MET-07 | 20 ordered/18 received/2 inspection/16 accepted; duplicate receipt; return report without restock; reservation/loan and non-sellable count variance | Cost/inventory focused | Planned red/green |
| 02-02 Task 1 | 2 | MET-03, MET-07 | 180000 obligation/100000 applied/80000 recorded unpaid; duplicate/over-applied payment, partial application coverage, undated due | Finance focused | Planned red/green |
| 02-02 Task 2 | 2 | MET-03, MET-07 | One active economic event after supersession; reconciled balance only with observed opening/closing evidence; missing opening and 56/91-day boundaries | Finance focused | Planned red/green |
| 02-02 Task 3 | 2 | MET-05, MET-07 | Budget origin with two targets and two payment rows; allocated plus unallocated exact; paid not added to incurred; missing/stale policy blocks headroom | Finance focused | Planned red/green |
| 02-03 Task 1 | 3 | MET-04, MET-07 | Stockout exposure minutes, zero denominator, immature/unlinked return cohort, recorded unmet units as lower bound, absent channel observation never zero | Learning/publication focused | Planned red/green |
| 02-03 Task 2 | 3 | MET-06, MET-07 | Readiness/quality/loan exception closure; sales row-category and field allowlists; injected cost, supplier, bank, recipient and PII-like value rejection | Learning/publication focused | Planned red/green |
| 02-03 Task 3 | 3 | MET-01..07 | Registry completeness, two synthetic cuts, source/policy/artifact hashes, missing/stale policy, traversal/symlink/outside-root rejection, no partial publish | All Phase 2 focused + full regression + v0.2 acceptance | Planned red/green |

## Requirement and Negative-Control Coverage

| Requirement | Positive evidence | Negative/unknown evidence | Final gate |
| --- | --- | --- | --- |
| MET-01 | Known sum, complete documented/estimated cost, version-effective realized margin/markup/contribution and exact cent allocation | Missing required component, overlapping approved version, 101-cent unit-ordinal residual, zero denominator, unapproved policy | 02-01 focused + final full gate |
| MET-02 | Ordered/received/disposition and stock/custody/reservation equations reconcile by event | Replayed receipt/restock, returned-only report, impossible negative available, unresolved count/non-sellable variance, partial movement coverage | 02-01 focused + final full gate |
| MET-03 | One canonical obligation balance; reconciled actual and separate committed/expected/undated/scenario 56/91-day cash | Duplicate payment, overapplication, forecast+actual duplicate, missing observed balance evidence, stale policy, undated misbucket | 02-02 focused + final full gate |
| MET-04 | Eligible launch sell-through, descriptive variant mix, linked mature rates, observed exposure and recorded unmet demand | Stockout interpreted as weak preference, immature/unlinked cohort, absent channel row interpreted as zero, missing denominator | 02-03 focused + final full gate |
| MET-05 | Approved/open/incurred/paid/outstanding/unallocated remain distinct and source-to-target cents reconcile | Two-target/two-payment join multiplication, payment added to incurred, lost unallocated amount, stale budget policy | 02-02 focused + final full gate |
| MET-06 | Stable owner/action/date/closure exception rows and safe sales readiness | Missing closure proof, internal category, unexpected field or sensitive value in an allowed field, recipient leakage | 02-03 focused + final full gate |
| MET-07 | Every result has one complete definition plus cut/source/policy hashes, status and reconciliation | Missing definition, invalid status, wrong 22-source binding, unsafe private-root path, failed atomic publication | All focused + final full gate |

## Trust and Compatibility Gates

- **Privacy:** The builder resolves paths under a configured ignored `.local/operating-marts` root; traversal, symlink/junction and outside-root paths fail before staging. Tests use disposable private-root equivalents. Sales output filters both row categories and fields, then validates values of allowed string fields. Private filled cuts are never committed or added to public evidence.
- **Policy:** `contracts/operating-metrics-policy-v1.schema.json` and a synthetic example artifact are separate from Phase 1 source facts. The builder accepts `policy_path`, verifies its canonical SHA-256, version, effective interval and status. Missing/stale inputs block dependent calculations; unapproved real cuts remain `REVIEW`; synthetic policy never approves real data.
- **Conservation:** All source cents and physical units reconcile by native ID before dimension joins. Receipt disposition uses Phase 1's three fields; non-sellable is derived from explicit observations rather than an invented source state. An economic event's superseded forecast is not also settled actual.
- **Compatibility:** Final full `unittest` and `scripts/verify_v2.py` gates protect historical v0.2/v0.3 behavior. No old evidence or released source bytes are rewritten to produce a pass.

## Manual-Only Verifications

None for synthetic Phase 2. Actual owner policy approval, fiscal treatment and real client correctness are external gates and cannot be inferred from test fixtures.

## Validation Sign-Off

- [x] Every task has an automated focused command.
- [x] A red/green test is created in each family's first task; no test infrastructure gap remains.
- [x] MET-01..07 have positive and negative controls, with final full regressions planned.
- [ ] Focused tests green on implemented code.
- [ ] Full `unittest` and `verify_v2.py` green on final Phase 2 code.

**Approval:** Pending execution evidence.
