# Independent adversarial review — Alma de Lujo v0.2

Review date: 2026-09-22. Reviewer: native Astra task `/root/astra_v2_review`.
Scope: `alma/warehouse.py`, authoritative `models/schema.sql` and `models/marts/*.sql`, native request bridge, process engine, workspace evidence and experimental diagnostics. All probes use `.venv/Scripts/python.exe`, disposable temporary directories and synthetic fixtures. No external actions, paid APIs or code changes were performed by this reviewer.

Final disposition after repairs: **PASS for the reviewed scope**. All six material finding groups were fixed by the implementation owners and independently rechecked with the same adversarial mutations. The initial findings are preserved below as evidence of what failed and why the repairs were necessary. Known parallel lifecycle/Windows lock repairs are outside this review's independent assurance. Machine-readable results and reviewed-file hashes are in `docs/review-summary-v2.json`.

## Findings

### ADV2-01 — P1: requests and mutable checkpoints are not anchored to the recorded run

Initial locations: `alma/process_engine.py:111`–`145`, especially request load at line 120 and accepted-response comparison at line 140. `alma/native_agents.py:49` validates self-consistency but does not establish provenance.

Repro uses the disposable `ProcessTests` fixture in `tests/test_process_engine.py`:

1. Start `finance-close` with workspace `counts.orders = 12`.
2. Read the analyst request, change evidence `counts.orders` to `999999`, and call `make_request` with the same role/process/run to compute a valid replacement request.
3. Replace only the task request. Submit schema-valid disposable analyst and different-reviewer responses with exact observation `999999` and matching disposable dispatch receipts.
4. The process reaches `READY_FOR_OWNER`; the packet claims `999999` orders despite the workspace containing `12`. The original event request ID differs from the accepted request ID.

A separate probe accepts an edited analyst summary after updating the unanchored checkpoint's `responses.finance_analyst.sha256`. Changing `state.input_hash` to `arbitrary` and `state.run_id` to `replacement` also reaches `READY_FOR_OWNER`. The accepted analyst prose need not equal the analysis embedded in the reviewer request.

A third probe changes the terminal packet's `external_execution` to `EXECUTE`; both `resume` and `status` continue reporting `READY_FOR_OWNER`. This does not itself execute an external action, but consumers can receive a corrupted packet presented as a verified completed run.

Required fix: reconstruct expected request/evidence from the bound workspace and current versioned definition; verify exact role/process/run/request IDs against the corresponding journal event. Anchor all checkpoint fields, accepted response and dispatch hashes. Revalidate analyst/reviewer evidence equality and distinct identities. On terminal resume/status verify the decision packet against its journal hash and authority policy. Integrity checks should reject inconsistent persisted artifacts; this is not a request for cryptographic provider signatures.

### ADV2-02 — P2: campaigns with spend but no deliveries disappear

Initial locations: `models/marts/channel_performance.sql:17`; `models/marts/funnel_conversion.sql:2`.

Repro: call `simulation.generate()`; copy the campaign for the maximum-spend funnel row with ID `camp-no-orders`; reassign that funnel row to the copied campaign. This preserves total marketing expense and all source reconciliation rules. Build a fresh warehouse.

Observed: source marketing spend is **147526 cents**, while each mart totals **133599 cents**. The **13927 cents** attached to the zero-order campaign vanish. All five warehouse reconciliation controls still pass. `channel_performance` starts from delivered orders; the funnel spine excludes funnel-only keys.

Required fix: use a complete campaign/channel spine including spend-only keys, left join sales, preserve known zero counts where source coverage is complete, and add independent source-to-mart marketing-spend reconciliation. Unknown order coverage must not be turned into zero delivery counts.

### ADV2-03 — P2: valid leads without sessions are silently excluded

Initial location: `models/marts/funnel_conversion.sql:4`.

Repro: normal seed 42 has 2830 leads. Set the first lead's permitted nullable `session_id` to `None`, leaving its valid customer/campaign/order links unchanged, then build a fresh warehouse.

Observed: source still has **2830 leads**, but mart `leads` sums to **2829** and each `funnel_coverage_known` is **1**. The filter `WHERE session_id IS NOT NULL` also removes valid linked orders for these leads. Additionally, `session_linked_leads` counts distinct session IDs, not lead IDs, so its name conceals a distinct-session grain when a session has multiple leads.

Required fix: count all leads separately from leads with sessions and distinct sessions producing leads. Preserve unlinked-lead counts and calculate each conversion rate with its explicitly named, compatible denominator. Cover a duplicate-session lead and a nullable-session lead in regression checks.

### ADV2-04 — P2: same-day repeat orders are excluded from 30-day repurchase

Initial location: `models/marts/customer_cohorts.sql:6`.

Repro: independently group seed-42 delivered orders by customer; choose a deterministic first delivered order by `(delivered_date, id)` and count other distinct order IDs within the inclusive 30-day window for mature customers.

Observed: **15 mature customers** with repeat orders are missed by the mart's strict `delivered_date > first_delivered_date` comparison. Example: `cust-0027` has delivered orders `ord-00027` and `ord-00835` on `2026-07-08`; the customer is counted as a non-repeater.

Required fix: exclude the first order by identity rather than excluding every order on its date. Alternatively, if the business truly wants separate-day repurchase, explicitly rename and document that metric and report same-day additional orders separately. The existing definition promises repeat orders, not separate-day purchases.

### ADV2-05 — P2: dependent metrics still return numeric values under unknown source coverage

Initial locations: `models/marts/experiment_results.sql:1`–`7`; `models/marts/channel_performance.sql:9`.

Repro A: set `metadata.coverage.experiment_assignments = False` in a normal snapshot, retain rows, and build. The experiment mart reports assigned counts 37/40 and conversion rates **0.4054054054 / 0.375**, despite `outcome_coverage_known = 0`. The independent Python experiment analysis correctly makes these rates unknown.

Repro B: set `metadata.coverage.orders = False`. The DM channel still reports `delivered_orders = 139`, `customers = 112`, while its revenue is correctly unknown. These fields do not identify themselves as partial observed counts.

Required fix: guard metrics using every source dependency and per-assignment outcome completeness. Unknown populations must not produce known conversion rates or complete-population counts. If observed partial counts are intentionally retained, expose them separately with explicit names and coverage semantics. Align SQL and Python experiment outputs.

### ADV2-06 — P2: completed experiments include outcomes beyond the declared fixed window

Initial locations: `alma/experimentation.py:43`; `alma/warehouse.py:349`–`351`; `models/marts/experiment_results.sql:9`.

Repro: seed-42 experiment `exp-socks-01` ends `2025-11-17`. Change its first outcome date from `2025-09-23` to snapshot date `2026-09-21`. Build a warehouse and call `analyze_experiments`.

Observed: import succeeds; diagnostics return `issues: []`; that outcome remains in the completed experiment's aggregate and conversion rate. Validation checks assignment-to-snapshot chronology but not the experiment's closure window.

Required fix: define the outcome window explicitly. If `end_date` is the fixed analysis closure, reject/exclude later outcomes and record the violation. If post-enrollment follow-up is intended, add a separate follow-up boundary and maturity rule rather than accepting any outcome before the snapshot.

## Positive checks and limits

- Fresh normal seed-42 warehouse: 30 source tables, 22864 rows, 1200 orders. Five independent controls pass: sales net revenue 37087457 cents, cash in 49622444 cents, cash out 5414773 cents, purchase receipts 663 units, supplier payments 4158000 cents.
- Authoritative sales SQL recognizes both revenue and COGS at delivery, credits at credit date, and restock COGS reversal at return date. Non-restocked returns do not reverse COGS.
- Monthly SQL carries daily unknown-cost flags through the monthly aggregate rather than publishing a partial cost sum as complete profit.
- Current inventory-count SQL chooses deterministic same-date counts and compares against ledger events through the count date.
- The public report labels the data synthetic, distinguishes cash from recognized revenue and states that pending agent requests are not executed analysis. Inventory aging explicitly disclaims exact lot age. No unsupported claim of real business impact was found in the inspected report writer.
- Source DDL uses STRICT tables, PK/FK constraints and row checks, while Python performs additional cross-table validation. This review does not claim that row-level SQL constraints alone enforce the full business contract.
- A passing normal fixture does not establish the absent-row, missing-coverage or tamper invariants above. These negative controls remain necessary after fixes.

## Recheck

### ADV2-01: resolved in independent replay

After the parent repair, the same disposable probes produced:

| Probe | Observed result |
| --- | --- |
| Coherently rebuilt replacement request with 999999 orders | Rejected: `Task request differs from immutable process evidence` |
| Edited accepted analyst and rewritten checkpoint response hash/input hash/run ID | Rejected: `Full process checkpoint differs from journal anchor` |
| Terminal packet authority changed to EXECUTE, followed by resume | Rejected: `Terminal decision packet was modified` |
| Same terminal packet change, followed by status | Rejected: `Terminal decision packet was modified` |
| Unchanged legitimate analyst plus a different reviewer | `READY_FOR_OWNER`; repeated terminal resume and status succeed |

The replacement-request probe does not need to reach the review stage anymore: it fails on analyst submission. The original demonstrated bypasses are closed. This conclusion covers persisted-artifact integrity and deterministic policy validation, not independent provider attestation of arbitrary prose.

Existing warehouse regression suite also passed **7/7** before the subsequent SQL repairs. The final SQL repairs were then evaluated with independent probes rather than treating that earlier green suite as sufficient.

### ADV2-02 through ADV2-06: resolved in independent replay

| Finding/probe | Final observed result |
| --- | --- |
| Spend-only campaign | Both marts retain all 147526 cents of source spend; the added campaign retains 13927 cents and known zero deliveries. New independent marketing-spend control passes. |
| Nullable session plus duplicate-session lead | Source and mart agree: 2831 all leads, 2830 linked leads, 1 unlinked lead and 2829 distinct linked sessions. The legacy `session_linked_leads` field is the distinct-session count; new `linked_leads` counts actual lead IDs. |
| Independent 30-day cohort oracle | All 13 cohort months agree for cohort size, mature denominator and repeat customers, including same-day repeat orders. Total mature repeat customers: 114. |
| Unknown order and experiment-assignment coverage | All four channel rows return unknown delivered/customer counts. Both experiment arms return unknown assignment counts, rates and monetary outcomes. |
| Outcome after experiment closure | Warehouse rejects the snapshot with `experiment outcome is outside assignment/experiment window`; independent diagnostics return `BLOCKED` and `OUTCOME_TIME_INVALID`. |
| Unmodified final generator | Fresh normal warehouse succeeds: 30 source tables, 22844 rows and 1200 orders. All six reconciliation controls pass. The final source row count differs from the initial baseline because experiment enrollment now closes before the fixed outcome window. |

An additional independent Python event oracle recomputed monthly recognized revenue, delivery COGS, restock reversals, accrued expenses and net cash directly from source records. It matched all **13 months** for both `normal` and `missing_cost`, with **zero discrepancies**. All 13 `missing_cost` months correctly retain unknown COGS instead of a partial sum. Source-event dates, not order or purchase creation dates, drive the cash comparison.

No unresolved material finding remains in the reviewed scope. This does not assert that synthetic business outcomes establish real demand or profitability, nor that arbitrary native-agent prose is semantically correct merely because the bridge validation passes.
