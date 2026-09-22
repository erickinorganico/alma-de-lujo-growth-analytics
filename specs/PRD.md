# Alma de Lujo Growth & Business Analytics v0.2 — product requirements

Status: **implementation contract**
Release target: **v0.2**
Applies to: local, offline, synthetic analytical system; no frontend, backend service, paid API, customer account, or external business action

## 1. Product outcome

v0.2 must demonstrate a working analytical operating system for an early-stage Mexican sportswear brand. A clean run must create a constrained relational warehouse, execute six business processes against reproducible synthetic events, materialize SQL marts, run deterministic controls, and produce evidence-grounded decision packets. At least one bounded analytical task per required business function must be completed by an actual native Codex agent and recorded as an agent run. Calculations, state transitions, and safety gates remain deterministic.

The product is successful when a reviewer can run one command, inspect the warehouse and process histories, trace every published number and recommendation to source events, replay normal and failure scenarios, and verify which outputs came from SQL, deterministic policy, or native-agent cognition.

## 2. v0.1 gap audit

The current release is a valid bounded demo, not the requested system. These gaps are acceptance inputs for v0.2.

| Gap ID | Verified v0.1 evidence | Why v0.1 does not satisfy v0.2 | Required closure |
|---|---|---|---|
| `GAP-DATA-01` | `alma/fixtures.py` defines 16 flat table dictionaries and eight orders; `alma/storage.py` copies them to CSV and SQLite. | SQLite columns have basic `INTEGER`/`TEXT` types but no primary keys, foreign keys, unique constraints, check constraints, typed timestamps, or normalized event/state history. | A relational DDL contract with enforced keys/checks and a load that fails atomically on invalid facts. |
| `GAP-DATA-02` | `alma/analytics.py` computes metrics in Python over in-memory dictionaries. | No versioned SQL staging/intermediate/mart layer exists, so a reviewer cannot inspect query grain, lineage, or bridge logic in SQL. | Versioned SQL models, lineage manifest, tests, and materialized marts. |
| `GAP-PROC-01` | `docs/DOMAIN.md` and `docs/PLAYBOOK.md` describe events and review steps. | The process descriptions are prose; there is no executable process instance, transition ledger, gate result, exception route, or replay behavior. | One durable runner and six process definitions with explicit states, transitions, gates, exceptions, owners, inputs, outputs, and idempotency. |
| `GAP-AGENT-01` | `alma/decisions.py` clones one deterministic packet into inventory, finance, and Growth variants; `alma/evaluation.py` labels deterministic replay as agent evaluation. | These are deterministic policies. There is no native model task contract, actual model-produced artifact, provenance, semantic rubric, or reviewer receipt. | Keep deterministic policies under the policy label and add schema-bound native-agent task/run evidence with model, effort, hashes, citations, and review result. |
| `GAP-SCEN-01` | Normal fixture has eight orders; red paths are four single-fault mutations. | The data is too small and sparse to exercise multi-period stock, partial receipts, split fulfilment, exchanges, cohort maturity, experiment assignment, close/reopen, or concurrent failures. | A larger seeded scenario pack with multiple sizes/colors/channels/periods and explicit expected outcomes. |
| `GAP-LIFE-01` | Current tables store latest statuses such as `orders.status` and aggregate PO receipt/payment fields. | Collapsed state loses transition history and allows order, settlement, fulfilment, return, refund, inventory, and cash lifecycles to be conflated. | Append-only events plus current-state views derived from legal transitions. |
| `GAP-EVID-01` | `receipt.json` hashes files and `quality.json` reports checks. | There is no cross-layer lineage from event to process to warehouse row to mart metric to decision claim. | Stable evidence references and a machine-readable lineage/acceptance manifest. |
| `GAP-OPS-01` | `python -m alma demo` builds a report; no process command exists. | A report build cannot pause at a gate, record human input, resume safely, or prove duplicate delivery is a no-op. | CLI process start/resume/replay commands with idempotent receipts and blocked-action behavior. |

v0.1 remains useful as a regression baseline. Its current green tests do not count as evidence that any gap above is closed.

## 3. Users and decisions

| User / owner | Decisions supported | Authority boundary |
|---|---|---|
| Founder | Assortment, purchase review, price review, experiment approval, weekly priorities | Must explicitly approve purchases, prices, publications, messages, payments, refunds, and external connections. |
| Operations owner | PO follow-up, receipt discrepancies, reservation/fulfilment, return inspection, stock reconciliation | May record synthetic process facts; cannot fabricate approval or cash evidence. |
| Growth owner | Funnel diagnosis, content hypotheses, experiment design/close recommendation | May propose tests; cannot claim causal impact without valid assignment and closure evidence. |
| Finance reviewer | Period close, revenue/cost/cash bridge review, exception disposition | Management analytics only; no tax, legal, invoicing, or formal-accounting assertion. |
| Analytics/data owner | Contracts, loads, transformations, quality, lineage, receipts | Owns evidence computation; cannot approve business actions. |
| Portfolio reviewer | Reproduce, inspect, query, and challenge the system | Receives synthetic artifacts and code only. |

## 4. Hard product boundaries

1. Every business datum in v0.2 is synthetic and marked `is_synthetic = true` at source and run level.
2. No Instagram/Meta/customer account connection, message, purchase, payment, refund, price change, inventory adjustment, or publication is executed.
3. No customer PII, credential, employer IP, paid API, trial requiring a card, frontend, backend service, CRM, ERP, or SaaS is introduced.
4. All money is signed integer minor units plus ISO currency. Cross-currency aggregation is blocked without a versioned rate record.
5. Unknown, not observed, not applicable, stale, contradictory, and zero are distinct values or statuses.
6. Synthetic performance may illustrate analysis but never proves demand, product-market fit, adoption, impact, or incremental ROI.

## 5. Functional requirements

### 5.1 Executable business processes

| Acceptance ID | Requirement |
|---|---|
| `ACC-PROC-001` | The runner implements exactly the six v0.2 process keys in `PROCESS-CATALOG.md`: `procure-to-stock` (`PTS-01`), `lead-to-delivery` (`LTD-01`), `return-to-refund` (`RTR-01`), `finance-close` (`FCL-01`), `weekly-growth-review` (`WGR-01`), and `market-to-experiment` (`MTE-01`). |
| `ACC-PROC-002` | Every process instance persists its identity, definition version, state, owner role, scenario/run IDs, update timestamp, and last event hash in `lifecycle_instances`. The canonical `models/lifecycle/instance_context.sql` query joins immutable events and receipts to expose input refs, output refs, gate results, exception codes, latest idempotency key, and the complete per-instance event/receipt history. |
| `ACC-PROC-003` | Legal transitions are allow-listed. An invalid transition is rejected, emits a failed receipt, and leaves prior state unchanged. |
| `ACC-PROC-004` | Replaying the same event with the same idempotency key and request hash returns `NO_OP_REPLAY`. Reusing that key with a changed request returns `CONFLICT` with `exception_code=CTR_DUPLICATE_EVENT_CONFLICT`, blocks an existing instance, and preserves the prior business-event count. |
| `ACC-PROC-005` | A process may stop at `WAITING_APPROVAL`, `REVIEW`, `BLOCKED`, or `INCONCLUSIVE` without coercing missing owner input to approval or zero. |
| `ACC-PROC-006` | No process transition executes an external business action. Native recommendations carry evidence, metric, guardrail, population, window, closure rule, `approval_required=true`, and `execution=PROHIBITED`; no packet records an approval decision or performs the action. |

### 5.2 Relational warehouse and SQL marts

| Acceptance ID | Requirement |
|---|---|
| `ACC-DATA-001` | The generated warehouse is a real relational database with declared primary keys, foreign keys, non-null constraints, unique/idempotency constraints, and domain checks; foreign-key enforcement is enabled and tested. |
| `ACC-DATA-002` | The 30 canonical source tables, warehouse control tables, 11 materialized mart relations, and separate lifecycle event database expose machine-readable schema/type/key/relationship metadata and declared grains. |
| `ACC-DATA-003` | The loaded typed SQLite warehouse is the query source for SQL marts. `data.json` and `tables/*.csv` are reproducible source/interchange evidence; mart JSON/CSV are exports of named warehouse queries, not alternative calculations. |
| `ACC-DATA-004` | SQL, not Python list arithmetic, materializes the fixed v0.2 marts: `sales_daily`, `inventory_position`, `inventory_aging`, `procurement`, `cash_daily`, `finance_monthly`, `channel_performance`, `customer_cohorts`, `experiment_results`, `funnel_conversion`, and `reconciliation`. Process state and evidence lineage remain queryable relations and may also be exported as operational marts. |
| `ACC-DATA-005` | `lineage.json` records inspected warehouse schema plus the exact path, SHA-256, and text of every versioned SQL model; workspace metadata provides scenario/run/as-of/synthetic identity and exported mart rows reconcile to the named materialized relation. |
| `ACC-DATA-006` | Loading an invalid batch is atomic: no partial warehouse or green receipt is produced. The prior verified artifact remains usable. |
| `ACC-DATA-007` | SQL tests cover key uniqueness, referential integrity, accepted values, nonnegative/bridge invariants, relationship cardinality, and source-to-mart reconciliation. |

### 5.3 Synthetic scenario system

| Acceptance ID | Requirement |
|---|---|
| `ACC-SCEN-001` | A fixed seed generates a 365-day calendar, at least 36 variants and 1,200 orders with multiple-item baskets, multiple suppliers/channels/campaigns, leads/sessions, 12 months of expenses, and randomized experiment assignments/outcomes, without hard-coding expected KPI totals into transformations. |
| `ACC-SCEN-002` | The normal scenario includes multiple sizes/colors, product lifecycle stages, multiple-item baskets, split payments and receipts, discounts, cancellations, restocked and written-off returns, refunds/credits, inventory counts, mature and immature cohorts, and assigned experiment observations. |
| `ACC-SCEN-003` | The dataset pack executes the six fixed v0.2 scenarios: `normal`, `stock_pressure`, `promotion_illusion`, `cash_squeeze`, `missing_cost`, and `broken_link`. The process acceptance suite separately injects illegal transitions, duplicate conflicts, missing approvals, over-receipts, excessive refunds, late experiment assignment, and agent prompt-injection cases. |
| `ACC-SCEN-004` | Verification records every scenario's seed-bound source hash, declared mechanism, expected status, quality issues, source counts, mart hashes, known/unknown summary metrics, and limits on interpretation. |
| `ACC-SCEN-005` | The same seed/config yields identical canonical source hashes, mart hashes, process terminal states, and deterministic control results. Different seeds preserve invariants while changing data. |

### 5.4 Deterministic controls and native cognition

| Acceptance ID | Requirement |
|---|---|
| `ACC-AGENT-001` | Code labels exact state machines, equations, thresholds, schema validation, reconciliation, and action denial as deterministic controls or policies. These artifacts must not be called agents. |
| `ACC-AGENT-002` | Native-agent tasks use versioned role contracts under `agents/`, schema-bound responses, immutable evidence/request hashes, and dispatch receipts containing native model, effort, timing, retries, authority, and parent validation. |
| `ACC-AGENT-003` | The release contains actual native Codex run evidence for inventory/supply, finance, Growth, and market/experiment analysis. At least two distinct native models are represented, and final adversarial review uses Astra. |
| `ACC-AGENT-004` | Each agent output separates evidence-backed facts, unknowns, hypotheses, recommendations, and challenges/risks. Every factual claim resolves to an immutable evidence reference; every recommendation carries an approval requirement and prohibited execution state. |
| `ACC-AGENT-005` | The request, response, dispatch receipt, and release run index together record the task/request identity and version, input/evidence hash, native model and task ID, effort, started/completed times, response hash, retries, parent validation, process, response path, and trace path. The validator supplies the schema and citation-resolution result. Prompts or private chain-of-thought are not published. |
| `ACC-AGENT-006` | Agent evals test unsupported claims, missing evidence, contradictory inputs, synthetic-to-real leakage, causal overclaim, approval bypass, prompt injection in source text, and malformed output. A schema-valid answer alone cannot pass. |
| `ACC-AGENT-007` | Agent recommendations never write source facts, alter process state, or execute an action. Deterministic validation may reject or downgrade an agent packet. |

### 5.5 Decision products and release evidence

| Acceptance ID | Requirement |
|---|---|
| `ACC-OUT-001` | Each process produces an inspectable instance summary and event ledger; each mart is queryable in the warehouse and exported for review. |
| `ACC-OUT-002` | The weekly Growth packet separates evidence-backed facts, data limitations, hypotheses, and at most five recommendations; every recommendation states primary metric, guardrail, population, window, closure rule, approval requirement, and prohibited execution. |
| `ACC-OUT-003` | The finance-close packet reconciles net revenue, COGS, gross profit, enumerated operating expenses, contribution proxy, and observed cash movement, while preserving their distinct timing and meaning. |
| `ACC-OUT-004` | The market-to-experiment packet records source authority/date/scope/license/limitations and treats market observations as context for a falsifiable hypothesis, never as Alma demand or sales. |
| `ACC-REL-001` | `python scripts/check_scope_v2.py --workspace evidence/v0.2/workspace --verification evidence/v0.2/verification.json --output evidence/v0.2/acceptance.json` creates one result for every `ACC-*` ID in this PRD and no unknown acceptance ID. |
| `ACC-REL-002` | A clean offline run builds the warehouse, all six process histories, marts, deterministic controls, reports, scenario evidence, agent request artifacts, and submitted agent-response validation without network or credentials. Actual native-agent outputs may be checked-in immutable evidence generated during authorized development; the release must not claim that an unattended local model executor exists. |
| `ACC-REL-003` | The release audit checks secrets, PII-like fields, licenses, synthetic labels, hashes, unresolved evidence refs, Git cleanliness of generated release inputs, and public-safe paths. |

## 6. Required output contract

The implementation may add files, but these paths are stable acceptance surfaces:

```text
<workspace>/data.json
<workspace>/quality.json
<workspace>/research.json
<workspace>/tables/<canonical-table>.csv
<workspace>/warehouse.sqlite3
<workspace>/warehouse-load.json
<workspace>/marts/<mart-name>.json
<workspace>/marts/<mart-name>.csv
<workspace>/lineage.json
<workspace>/workspace.json
<workspace>/processes/<process-id>/state.json
<workspace>/processes/<process-id>/events.json
<workspace>/processes/<process-id>/tasks/<role>.request.json
<workspace>/processes/<process-id>/tasks/<role>.response.json
<workspace>/processes/<process-id>/tasks/<role>.dispatch.json
<workspace>/processes/<process-id>/decision-packet.json
<workspace>/lifecycle/lifecycle.sqlite3
<workspace>/lifecycle/exports/{definitions,instances,events,receipts}.json
<workspace>/lifecycle/summary.json
models/lifecycle/instance_context.sql
evidence/v0.2/lifecycle-instance-context.json
contracts/decision-packet-v2.schema.json
evidence/v0.2/acceptance.json
evidence/v0.2/verification.json
evidence/v0.2/clean-install.json
evidence/v0.2/release-audit.json
evidence/v0.2/scenarios/index.json
evidence/v0.2/agents/task-runs.json
evidence/v0.2/orchestration.json
```

`lineage.json` must enumerate inspected warehouse types/keys/relationships and exact SQL model hashes/text. `workspace.json` hashes the non-database workspace artifacts and declares the database rebuild command. The lifecycle summary must remain portable and refer to relative artifact names, not temporary absolute paths.

`contracts/decision-packet.schema.json` remains the legacy v1 demo/report contract. Native process packets emitted under `<workspace>/processes/*/decision-packet.json` use the exact v2 contract in `contracts/decision-packet-v2.schema.json`.

The release workspace alias is `evidence/v0.2/workspace`; disposable builds may use another empty `<workspace>` path without changing the contract.

## 7. Release acceptance algorithm

The release is accepted only if all steps complete in a clean copy:

1. Generate and load the normal scenario into a fresh warehouse.
2. Query database metadata and compare it with the inspected schema in `lineage.json`; verify foreign keys and constraints are active.
3. Execute the six process definitions, then replay their source events and confirm no duplicated business effect.
4. Materialize every required SQL mart and reconcile it to source-event control totals.
5. Run every scenario manifest and compare actual terminal states, quality codes, known/unknown fields, and prohibited claims with expected results.
6. Validate every checked-in native-agent run receipt and resolve every factual claim to hashed evidence.
7. Run the full test suite, deterministic replay, public-safety audit, and file-hash verification.
8. Emit `evidence/v0.2/acceptance.json`; any failed, blocked, or missing `ACC-*` result prevents release `PASS`.

## 8. Definition of done

v0.2 is done when `ACC-REL-001` reports all acceptance IDs as `PASS`, the normal run is reproducible, every red scenario fails in the specified controlled way, all native-agent claims resolve to evidence, Astra's final adversarial findings are either fixed or explicitly release-blocking, and the public repository contains no private or real customer data.

Passing v0.1 tests, generating CSVs, adding more prose, renaming deterministic policies as agents, or storing flat rows in a file named `.sqlite3` does not satisfy this contract.
