# v0.2 scope and acceptance matrix

This matrix is the release checklist for `specs/PRD.md`. “Output” means a generated artifact or queryable database object. “Check” means a repeatable automated assertion; a prose statement is not sufficient evidence.

## Scope legend

- **Build**: required in v0.2.
- **Evidence**: immutable development-time proof checked into `evidence/v0.2`.
- **Future**: designed for later integration but excluded from release.
- **Prohibited**: outside authorization.

## Required implementation and evidence

| Acceptance ID | Scope | Implementation surface | Required output | Machine check / pass condition |
|---|---|---|---|---|
| `ACC-PROC-001` | Build | Native-analysis definitions in `processes/*.json`; business lifecycle definitions in `processes/business/*.json` | Six native process definitions plus six business lifecycle definitions | Exact slug-to-contract-ID mapping equals `procure-to-stock`/`PTS-01`, `lead-to-delivery`/`LTD-01`, `return-to-refund`/`RTR-01`, `finance-close`/`FCL-01`, `weekly-growth-review`/`WGR-01`, `market-to-experiment`/`MTE-01`; versions and hashes present. |
| `ACC-PROC-002` | Build | `alma.process_engine`, `alma.lifecycle`, and `models/lifecycle/instance_context.sql` | `processes/<slug>/{state,events}.json`; `lifecycle/lifecycle.sqlite3`; lifecycle exports; `evidence/v0.2/lifecycle-instance-context.json` | Native task journals validate; business instance columns plus joined immutable events/receipts expose identities, states, owners, refs, gates, exceptions, latest idempotency, timestamps, and hash chains. |
| `ACC-PROC-003` | Build | Transition engine | Failed transition receipt | Parameterized test attempts one illegal transition per process; state/event count remains unchanged except failed receipt. |
| `ACC-PROC-004` | Build | Idempotency registry/constraint | Replay results in acceptance evidence | Same key+request hash yields `NO_OP_REPLAY`; same key+changed request yields `CONFLICT` and `CTR_DUPLICATE_EVENT_CONFLICT`; business-event count is unchanged. |
| `ACC-PROC-005` | Build | Gate evaluator and status vocabulary | Paused/blocked scenario summaries | Missing approval/input ends at declared waiting/blocked state and downstream affected metrics are unknown or blocked. |
| `ACC-PROC-006` | Build | Proposed-action schema and deny policy | Decision packets validated against `contracts/decision-packet-v2.schema.json` | Every recommendation carries `approval_required=true` and `execution=PROHIBITED`; packets record no approval decision and adversarial execute attempts are denied. |
| `ACC-DATA-001` | Build | `alma.warehouse` versioned DDL | `<workspace>/warehouse.sqlite3`, `warehouse-load.json` | Metadata query proves typed tables plus PK/FK/UNIQUE/NOT NULL/CHECK constraints; FK enforcement is on; injected violation is rejected. |
| `ACC-DATA-002` | Build | `inspect_schema` and lifecycle DDL | `<workspace>/lineage.json`; lifecycle database exports | Exact 30 canonical tables, control relations, 11 materialized marts, and lifecycle registry expose schema metadata; expected relations have no missing key/relationship contract. |
| `ACC-DATA-003` | Build | Canonical warehouse load and named mart query boundary | `data.json`, `tables/*.csv`, `warehouse.sqlite3`, `marts/*` | Mart exports equal `query_mart` rows from SQLite; no mart reads exported CSV as a calculation input. |
| `ACC-DATA-004` | Build | Versioned SQL under `models/marts/*.sql` | Eleven required materialized relations plus JSON/CSV exports | `lineage.json` maps each mart to SQL path/hash/text and the named query returns expected columns/grain. |
| `ACC-DATA-005` | Build | Workspace lineage and manifest | `lineage.json`, `workspace.json` | Schema inspection and SQL hashes/text are complete; metadata binds scenario/seed/as-of/synthetic state; non-database artifact hashes verify. |
| `ACC-DATA-006` | Build | Transactional loader | Failed-load receipt | Broken FK/check batch rolls back fully; relation counts/hash equal pre-load state; no green build receipt. |
| `ACC-DATA-007` | Build | SQL data-quality suite | `quality.json` | All declared tests run; normal is green; each injected fault raises its exact expected code. |
| `ACC-SCEN-001` | Build | `alma.simulation.generate` seeded scenario generator | Scenario manifest and source counts | Normal covers 365 days, >=36 variants, 1,200 orders, multiple-item baskets and the required campaign/session/lead/experiment/expense structures; exact same seed/config hashes identically. |
| `ACC-SCEN-002` | Build | Normal synthetic storyline | `<workspace>/data.json` and verification record | Coverage assertions find the required multi-item, split-payment/receipt, return/disposition, cohort, inventory-count, and experiment records; every business row belongs to the explicitly synthetic snapshot. |
| `ACC-SCEN-003` | Build | Dataset scenario registry plus process fault matrix | `evidence/v0.2/scenarios/index.json` | Exact dataset scenarios are `normal`, `stock_pressure`, `promotion_illusion`, `cash_squeeze`, `missing_cost`, `broken_link`; declared process/idempotency/approval/agent fault injections also execute. |
| `ACC-SCEN-004` | Build | Scenario verification records | `<verification>` scenario records | Each record carries source hash, mechanism, expected status, quality issues, counts, mart hashes, known/unknown summaries, and synthetic interpretation limits. |
| `ACC-SCEN-005` | Build | Canonical serializer/replay | Replay section in `acceptance.json` | Two same-seed runs match source/mart/process/control hashes; a second seed changes source hash and passes invariant suite. |
| `ACC-AGENT-001` | Build | SQL/quality outputs plus native-agent contracts | `lineage.json`, quality output, task requests, decisions | Arithmetic/state gates originate in SQL/Python deterministic controls; native agent requests ask for analysis and cite evidence rather than calculating source truth. |
| `ACC-AGENT-002` | Build | `agents/*.json`, native bridge, and response schema | Role contracts, `<workspace>/processes/*/tasks/*.request.json`, `contracts/native-agent-response.schema.json` | Role contracts bind objective/tools/authority/completion/fail-closed behavior; request hashes and response schema validate; dispatch receipts supply model/effort/timing/retry/parent review. |
| `ACC-AGENT-003` | Evidence | Authorized native Codex task executions | `<workspace>/processes/*/tasks/*.response.json|*.dispatch.json`; `evidence/v0.2/agents/task-runs.json` | Six analyst plus six reviewer runs validate; each reviewer differs from its process analyst; >=2 native models; an Astra reviewer is present. |
| `ACC-AGENT-004` | Build + Evidence | Agent output validator and `contracts/decision-packet-v2.schema.json` | `<workspace>/processes/*/decision-packet.json` | Exact v2 packet shape validates; facts, unknowns, hypotheses, recommendations and independent review remain separate; every factual evidence ref resolves and hashes match. |
| `ACC-AGENT-005` | Evidence | Native request/response/dispatch bundles plus run index | `<workspace>/processes/*/tasks/*.{request,response,dispatch}.json`; `evidence/v0.2/agents/task-runs.json` | Each validated bundle binds the hashed request/evidence and response to agent/model/effort/times/retry/parent-review fields; the release index adds process, response, and trace paths and its task/model counts reconcile to the 12 accepted dispatches. |
| `ACC-AGENT-006` | Build | Native-contract negative tests plus independent Astra review | `docs/review-summary-v2.json`, `docs/ADVERSARIAL-REVIEW-v2.md`, full verification tests | Adversarial probes and negative controls pass, reviewed source hashes still match, and unresolved material findings are empty. |
| `ACC-AGENT-007` | Build | Read-only boundary | Agent packet validation result | Agent output cannot mutate source/process relations; before/after source/process hashes match; execute attempts fail. |
| `ACC-OUT-001` | Build | Workspace, process, lifecycle, and mart exporters | `marts/*.json|csv`, process state/events, lifecycle exports | Required file set complete; mart exports reconcile to warehouse queries; lifecycle exports reconcile to lifecycle SQLite rows. |
| `ACC-OUT-002` | Build + Evidence | Weekly review packet task | `<workspace>/processes/weekly-growth-review/decision-packet.json` | Facts/unknowns/hypotheses are separate; <=5 recommendations; each recommendation includes evidence, metric, guardrail, population, window, closure, approval and prohibited execution. |
| `ACC-OUT-003` | Build | Finance marts and close packet | `<workspace>/marts/{finance_monthly,cash_daily,reconciliation}.*`, finance-close packet | Revenue/COGS/profit/expense/contribution/cash fields stay distinct and reconciliation controls pass. |
| `ACC-OUT-004` | Build + Evidence | Market source register and experiment packet | `<workspace>/research.json`, market-to-experiment packet | Each used source has publisher/date-or-status/scope or method/license/limitations; the packet preserves unknowns and avoids treating context as Alma demand or sales. |
| `ACC-REL-001` | Build | Acceptance registry/runner | `evidence/v0.2/acceptance.json` | Exact set of all `ACC-*` IDs found in PRD; each has status, command/check, evidence refs, timestamp; release green only if all pass. |
| `ACC-REL-002` | Build | One-command clean demo | `evidence/v0.2/clean-install.json` | Offline clean copy produces all deterministic artifacts; checked-in native-agent outputs validate without live network/model call. |
| `ACC-REL-003` | Build | Public release audit | `evidence/v0.2/release-audit.json` | Secret/PII/license/synthetic/hash/ref/path checks pass; generated evidence contains no prohibited path or real identity. |

## Required relational objects

The warehouse uses the exact 30 canonical source tables in `IMPLEMENTATION-v2.md` and `alma.warehouse.TABLE_COLUMNS`, plus warehouse control relations for coverage/manifests/idempotent ingestion/rejections. It does not need duplicate `src_*`, `dim_*`, or `fact_*` copies merely to satisfy a naming convention. The 11 fixed materialized SQL marts are `sales_daily`, `inventory_position`, `inventory_aging`, `procurement`, `cash_daily`, `finance_monthly`, `channel_performance`, `customer_cohorts`, `experiment_results`, `funnel_conversion`, and `reconciliation`.

The separate lifecycle database contains `lifecycle_instances`, `lifecycle_events`, `lifecycle_idempotency`, and `lifecycle_receipts`. Their grains are one current process instance, one applied transition, one process/idempotency binding, and one attempt/result receipt respectively.

## Scenario coverage matrix

Exact scenario slugs may change only by updating the scenario catalog and this matrix together.

| Scenario | Class | Required injected condition | Expected system behavior |
|---|---|---|---|
| `normal` | Baseline | Complete 365-day, 1,200-order synthetic operating history | Warehouse/marts reconcile; all six processes reach native-analysis/review path; external actions remain prohibited. |
| `stock_pressure` | Valid stress | Low cover, stock pressure, and count discrepancies | Inventory alerts and unknown/review states surface without negative-stock fabrication or automatic PO. |
| `promotion_illusion` | Valid stress | Discounted volume increases while contribution erodes | Revenue/volume and contribution remain separate; no “successful promotion” claim from volume alone. |
| `cash_squeeze` | Valid stress | Supplier prepayments and timing produce cash pressure | Finance/cash marts show timing separation; operating result is not presented as available cash. |
| `missing_cost` | Controlled failure | Delivered unit lacks cost basis | COGS/profit/margin unknown; `FIN_UNKNOWN_COST`; independently known revenue may remain visible. |
| `broken_link` | Controlled failure | Source FK is invalid | Atomic load rejection; prior warehouse preserved; no green receipt. |
| Process fault matrix | Controlled failures | Duplicate conflict, illegal lifecycle transition, missing approval, over-receipt, excessive refund, late assignment, stale market evidence, bridge mismatch, prompt injection | Exact process exception and preserved prior facts; no external action or unsupported claim. |

## Explicitly future

| Item | Status | Contract preserved now |
|---|---|---|
| Real Alma CSV/Sheets adapters | Future | Source adapter interface, provenance fields, quarantine/validation path. |
| Instagram/Meta/commerce/payment integrations | Future; needs new authority | External-source IDs and approval gate only. |
| Owner-approved definitions, thresholds, and accounting policy | Future discovery | All current policies versioned `PROVISIONAL`; decisions can remain waiting/review. |
| Laya shadow evaluation | Future conditional | Trigger only when a repeated uncertain closed-label task exists with a labeled baseline. |
| Local visual interface | Future independent phase | Stable warehouse, marts, and artifact contracts. |
| Formal accounting/tax/invoicing | Future specialist scope | Finance artifacts explicitly remain management analytics. |

## Prohibited in v0.2

Real customer or supplier PII, credentials, account connections, external messages, content publication, purchase/payment/refund execution, automatic price or inventory changes, paid services, employer code/data, and claims of real adoption or impact are prohibited. A test double may record a blocked attempt; it may not call an external system.

## Release evidence rules

1. Every matrix row must map to exactly one result in `evidence/v0.2/acceptance.json`.
2. A result includes `acceptance_id`, `status`, `check_type`, `command_or_query`, `evidence_refs`, `observed`, `expected`, and `checked_at_utc`.
3. Allowed statuses are `PASS`, `FAIL`, and `BLOCKED`. `SKIP`, missing, or manual prose is release-blocking.
4. An `Evidence` item may use immutable checked-in native-agent output; a `Build` item must be reproducible from code and synthetic inputs.
5. A green test runner is necessary but insufficient: required artifacts, database metadata, hashes, and evidence references must also pass.
