# v0.2 executable process catalog

Status: **normative process contract**
Catalog version: `2.0.0`
Execution boundary: local synthetic events, deterministic transitions and controls, native-agent request/response evidence, no external business execution

## Exact persisted contracts

The lifecycle definition, submitted event, current instance, applied event, and attempt receipt are separate contracts. Fields from one contract are not required in another.

### Business definition

Each file under `processes/business/*.json` has exactly seven top-level fields. `alma.lifecycle.definitions()` rejects a different top-level field set, an empty transition list, duplicate or filename-mismatched IDs, and any set other than the six release process IDs.

| Field | Current rule |
|---|---|
| `id` | One of `procure-to-stock`, `lead-to-delivery`, `return-to-refund`, `finance-close`, `weekly-growth-review`, `market-to-experiment`; equals the filename stem. |
| `contract_id` | `PTS-01`, `LTD-01`, `RTR-01`, `FCL-01`, `WGR-01`, or `MTE-01`. |
| `version` | `2.0.0` in this release. This versions the definition and its accepted payload semantics. |
| `owner` | Functional accountable role. |
| `initial_state` | State used when no materialized instance exists. |
| `terminal_states` | Declared terminal-state list. |
| `transitions` | Nonempty list whose current records carry `event`, `from`, `to`, and `gate`. Gates are deterministic functions in `alma.lifecycle`; these JSON files do not contain payload schemas. |

### Submitted event boundary

`apply_event()` accepts named arguments `process_id`, `instance_id`, `event_id`, `event_type`, `payload`, `idempotency_key`, `occurred_at_utc`, `source_refs`, `scenario_id`, `run_id`, `synthetic`, and optional `recorded_at_utc`, plus the database path. Process and identity strings are bounded and nonempty; timestamps are UTC; `synthetic` must be true; every source ref must be a bounded `synthetic://` reference; and the event type must be legal from the current state. The definition version comes from the loaded definition rather than the caller.

The payload is an extensible JSON object governed by the definition version and the selected deterministic gate. Gates validate the fields they consume and derive observed evidence from prior events. Unknown payload fields are retained in the payload hash and applied event; the runtime does **not** claim a universal allow-list or universal rejection of extra payload keys. Recursive action denial still rejects unsafe `execute`, `executed`, `external_action`, or non-`PROHIBITED` execution values.

### Current instance row

`lifecycle_instances` persists exactly: `process_id`, `process_contract_id`, `instance_id`, `definition_version`, `owner_role`, `scenario_id`, `run_id`, `current_state`, nullable `blocked_reason`, `last_event_hash`, `updated_at_utc`, and `synthetic=1`. Its key is `(process_id, instance_id)`.

### Applied event row

`lifecycle_events` persists exactly the process/instance key, positive `sequence`, `event_id`, `event_type`, `from_state`, `to_state`, UTC occurrence/recording times, canonical `payload_json`, `payload_hash`, canonical `source_refs_json`, `idempotency_key`, `previous_hash`, `event_hash`, and `synthetic=1`. Applied events are append-only and form the per-instance hash chain.

### Attempt receipt and derived instance context

Every attempt produces an immutable receipt with identity, process/instance, idempotency key, `status`, nullable `exception_code`, before/after state, nullable applied-event hash, recorded time, synthetic/action-denial markers, and `details`. Gate name and observed gate values live in `details`; rejected attempts do not become applied events.

Input refs, output refs, gate results, exception codes, the latest idempotency key, and full event/receipt history are normalized across `lifecycle_instances`, `lifecycle_events`, and `lifecycle_receipts`. The canonical one-row-per-instance reconstruction is `models/lifecycle/instance_context.sql`; its verified release output is `evidence/v0.2/lifecycle-instance-context.json`. This derived context does not claim that those values are physical columns on `lifecycle_instances`.

### Universal transition behavior

1. The runner starts a database transaction and looks up `(process_id, idempotency_key)`.
2. Existing key plus an identical canonical request hash returns receipt status `NO_OP_REPLAY`; no business event, state, output, or downstream counter changes.
3. Existing key plus a different request hash returns receipt status `CONFLICT` with `exception_code=CTR_DUPLICATE_EVENT_CONFLICT`, marks an existing instance `BLOCKED`, and preserves prior business events.
4. The runner validates the exact submitted-event envelope, current state, requested transition, versioned gate requirements, source refs, and action-denial boundary.
5. A failed gate records the attempt and declared exception but does not apply the transition's business effect.
6. A valid transition appends the process event and business facts atomically, then derives current state.
7. Agent responses are submitted through the request/response bridge. Their hash and cited evidence are validated before they can become a decision artifact. They cannot bypass any gate.

The portable idempotency-key form is:

```text
<process-id>:<instance-id>:synthetic:<event-type>:<source-sequence>:<definition-version>
```

The demo uses only the `synthetic` source token. A retry reuses the exact key and request. A correction must use a new event ID and idempotency key; reusing a key with changed request content produces `CONFLICT`.

### Decision packet versions

`contracts/decision-packet.schema.json` is the preserved legacy v1 demo/report schema. Terminal native-analysis packets emitted by `alma.process_engine._packet()` use `contracts/decision-packet-v2.schema.json`: exact v2 top-level fields, `REVIEW` or `READY_FOR_OWNER`, validated analyst facts/unknowns/hypotheses/recommendations, an independent `evidence_reviewer` response, two accepted-agent receipts, and `external_execution=PROHIBITED`.

## `PTS-01` — procure-to-stock

Purpose: turn an approved purchasing intent into accepted stock while keeping order, dispatch, receipt, supplier payment, inventory, and exceptions distinct.

| Contract item | Definition |
|---|---|
| Accountable owner | Operations owner; founder approves supplier commitment; finance reviewer owns supplier-payment evidence. |
| Inputs | Supplier and variant dimensions; PO and line events; approval record; dispatch evidence when observed; `purchase_receipts`; acceptance/rejection result; `supplier_payments`; currency/cost version. |
| Outputs | PO/line current state; receipt and rejection facts; `PURCHASE_RECEIPT` inventory movements for accepted units; open/in-transit quantities; procurement mart rows; exceptions; purchase-review proposal. |
| Decision product | Supply review containing open units, expected/observed lead time, receipt variance, accepted value, unknowns, and approval-required next action. |
| Explicit separation | PO is commitment intent; dispatch is transit evidence; receipt is physical acceptance; invoice/obligation is finance evidence; payment is cash evidence; only accepted receipt increases on hand. |

### States and legal transitions

| From | Event | To | Required gate(s) |
|---|---|---|---|
| `NEW` | `po_drafted` | `DRAFT` | `PTS-G01` valid supplier/variant/positive line quantity/currency. |
| `DRAFT` | `po_submitted` | `WAITING_APPROVAL` | `PTS-G02` known expected unit cost or explicit `REVIEW`; totals reconcile. |
| `WAITING_APPROVAL` | `po_approved` | `APPROVED` | `PTS-G03` human approval record names approver, scope, time, and PO hash. |
| `WAITING_APPROVAL` | `po_rejected` | `CANCELLED` | Rejection reason present. |
| `APPROVED` | `supplier_dispatched` | `IN_TRANSIT` | `PTS-G04` dispatched units do not exceed unresolved approved units. |
| `APPROVED` or `IN_TRANSIT` | `goods_partially_received` | `PARTIALLY_RECEIVED` | `PTS-G05` receipt references PO line/location; accepted+rejected <= open units. |
| `APPROVED`, `IN_TRANSIT`, or `PARTIALLY_RECEIVED` | `goods_fully_received` | `RECEIVED` | `PTS-G05`; cumulative accepted+rejected/cancelled resolves ordered units. |
| `APPROVED`, `IN_TRANSIT`, or `PARTIALLY_RECEIVED` | `po_remainder_cancelled` | `RECEIVED` or `CANCELLED` | Owner-approved reason; already accepted units preserved. |
| `RECEIVED` | `po_reconciled` | `CLOSED` | `PTS-G06` receipt/stock bridge passes; supplier payment may remain separately open. |
| Any nonterminal state | declared failure | `BLOCKED` | Blocking exception recorded. |

### Gates, exceptions, idempotency

| Gate / code | Deterministic rule and behavior |
|---|---|
| `PTS-G01` / `CTR_BROKEN_REFERENCE` | All keys resolve; quantities positive; sample/idea variants cannot be stocked for sale without approved lifecycle transition. |
| `PTS-G02` / `FIN_UNKNOWN_COST` | Unknown cost may keep draft under review but cannot produce known inventory value or margin. It is never zero. |
| `PTS-G03` / `APPROVAL_MISSING` | No purchase commitment without a matching approval record. Agent recommendation is not approval. |
| `PTS-G04` / `PROC_OVER_DISPATCH` | Cumulative dispatch cannot exceed open approved units. |
| `PTS-G05` / `PROC_OVER_RECEIPT` | Cumulative accepted+rejected cannot exceed resolvable ordered units; failed receipt posts no stock. |
| `PTS-G06` / `INV_LEDGER_RECEIPT_MISMATCH` | Accepted units equal posted inventory receipt units by PO line and location. |
| `PROC_DUPLICATE_RECEIPT` | Duplicate identical source receipt is no-op; changed duplicate is contradictory and blocks. |
| `PROC_LATE_RECEIPT` | Valid nonblocking exception; preserves actual date and exposes SLA variance. |

Instance key is the PO ID. Receipt idempotency uses the receipt source ID, not `(PO, date, quantity)`, so two legitimate partial receipts remain distinct.

## `LTD-01` — lead-to-delivery

Purpose: trace market/channel contact through commercial intent and physical delivery without conflating lead, order, payment, reservation, shipment, delivery, revenue, or cash.

| Contract item | Definition |
|---|---|
| Accountable owner | Growth owner through qualified lead; operations owner from accepted order through delivery; finance reviewer for settlement evidence. |
| Inputs | `sessions`, `leads`, campaign/content refs, order and line events, payment events, reservations, `shipments`, inventory movements, delivery evidence. |
| Outputs | Lead conversion state, order lifecycle, settlement lifecycle, reservation and fulfilment facts, stock movements, sales/channel/funnel mart rows, exception record, customer-service proposal. |
| Decision product | Funnel and fulfilment review with coverage, drop-offs, order/settlement/fulfilment states, blocked claims, and owner. |
| Explicit separation | Channel association is descriptive; payment settlement is not bank availability; shipment is not delivery; order date is not recognition/cash date. |

### States and legal transitions

| From | Event | To | Required gate(s) |
|---|---|---|---|
| `NEW` | `lead_captured` | `LEAD_OPEN` | `LTD-G01` traceable synthetic session/channel or declared offline source. |
| `LEAD_OPEN` | `lead_qualified` | `LEAD_QUALIFIED` | Intent/status evidence; missing identity linkage stays unknown. |
| `LEAD_OPEN` or `LEAD_QUALIFIED` | `lead_lost` | `LOST` | Reason recorded; no fabricated order. |
| `LEAD_OPEN` or `LEAD_QUALIFIED` | `order_placed` | `ORDER_PLACED` | `LTD-G02` valid lines, agreed price/currency, lifecycle-eligible variants. |
| `ORDER_PLACED` | `order_accepted` | `WAITING_SETTLEMENT` | `LTD-G03` order policy and stock eligibility pass. |
| `WAITING_SETTLEMENT` | `payment_settled` | `READY_TO_RESERVE` | `LTD-G04` eligible settled amount under the declared method. |
| `WAITING_SETTLEMENT` | `payment_failed` | `WAITING_SETTLEMENT` | Attempt retained; retry is a new payment event. |
| `READY_TO_RESERVE` | `inventory_reserved` | `RESERVED` | `LTD-G05` available units cover reservation. |
| `RESERVED` | `fulfilment_started` | `FULFILMENT_READY` | Pick quantities <= active reservation. |
| `FULFILMENT_READY` | `shipment_posted` | `PARTIALLY_SHIPPED` or `SHIPPED` | `LTD-G06` shipment and stock movement reconcile. |
| `PARTIALLY_SHIPPED` | `shipment_posted` | `SHIPPED` | Remaining eligible line quantities only. |
| `PARTIALLY_SHIPPED` or `SHIPPED` | `delivery_confirmed` | `PARTIALLY_DELIVERED` or `DELIVERED` | `LTD-G07` delivery refers to prior shipment and valid time. |
| Any pre-shipment state | `order_cancelled` | `CANCELLED` | Releases reservation; payment/refund process remains distinct. |
| Any nonterminal state | declared failure | `BLOCKED` | Blocking exception recorded. |

### Gates and exceptions

| Gate / code | Deterministic rule and behavior |
|---|---|
| `LTD-G01` / `SOURCE_NOT_OBSERVED` | Missing session/traffic preserves unknown denominator; a lead may still exist under declared offline source. |
| `LTD-G02` / `ORDER_INVALID_LINE` | Positive quantity, effective price, currency, valid product lifecycle; sample/idea cannot sell. |
| `LTD-G03` / `ORDER_POLICY_REVIEW` | Acceptance rules versioned; no silent acceptance from order creation. |
| `LTD-G04` / `PAYMENT_RECONCILIATION` | Settlement amounts, retries, reversals, and method terms stay event-level. |
| `LTD-G05` / `INV_NEGATIVE_AVAILABLE` | Reservation may not make available stock negative. |
| `LTD-G06` / `SHIPMENT_RESERVATION_MISMATCH` | Shipment consumes eligible reservation and posts equal negative inventory movement. |
| `LTD-G07` / `STATE_INVALID_TRANSITION` | Delivery cannot precede shipment; dates are monotonic per line. |
| `LTD_SPLIT_FULFILMENT` | Valid edge; process stays partial until all eligible line quantities terminate. |

Instance key is the lead ID plus resulting order ID once linked. Lead and order source events keep independent idempotency keys.

## `RTR-01` — return-to-refund

Purpose: manage post-delivery merchandise and monetary resolution while keeping request, authorization, physical receipt, inspection, restock, credit, and refund distinct.

| Contract item | Definition |
|---|---|
| Accountable owner | Operations owner for merchandise/inspection; founder or delegated approver for policy exception; finance reviewer for refund evidence. |
| Inputs | Delivered order/line evidence; return request and authorization; carrier/receipt; inspection/disposition; credit note; refund attempt/settlement; replacement order link. |
| Outputs | Return state, disposition, optional inventory movement, refund state, return/refund mart row, customer-resolution proposal, exceptions. |
| Decision product | Return case summary with item eligibility, condition, restock/write-off, requested/settled amounts, timing, and approval status. |
| Explicit separation | A request does not increase inventory; receipt does not imply restock; return does not imply refund; goodwill refund may exist without return; exchange is a return plus linked new/replacement order. |

### States and legal transitions

| From | Event | To | Required gate(s) |
|---|---|---|---|
| `NEW` | `return_requested` | `REQUESTED` | `RTR-G01` delivered eligible quantity and policy context. |
| `REQUESTED` | `return_authorized` | `AUTHORIZED` | `RTR-G02` approver/policy and authorized quantity/amount. |
| `REQUESTED` | `return_rejected` | `REJECTED` | Reason and policy version recorded. |
| `AUTHORIZED` | `return_in_transit` | `IN_TRANSIT` | Tracking optional but absence explicit. |
| `AUTHORIZED` or `IN_TRANSIT` | `return_received` | `RECEIVED` | `RTR-G03` received quantity <= authorized and previously unreceived quantity. |
| `RECEIVED` | `return_inspected` | `INSPECTED` | `RTR-G04` disposition is `RESTOCK`, `DAMAGED`, `REPAIR`, or `DISCARD`. |
| `INSPECTED` | `refund_requested` | `REFUND_PENDING` | `RTR-G05` eligible amount and approval; credit/allowance policy explicit. |
| `REFUND_PENDING` | `refund_settled` | `REFUNDED` | `RTR-G06` settlement evidence; cumulative refund within eligible payment. |
| `INSPECTED` or `REFUNDED` | `case_closed` | `CLOSED` | Stock, credit, refund, and replacement bridges reconcile or remain explicitly not applicable. |
| Any nonterminal state | declared failure | `BLOCKED` | Blocking exception recorded. |

### Gates and exceptions

| Gate / code | Deterministic rule and behavior |
|---|---|
| `RTR-G01` / `RETURN_EXCEEDS_DELIVERED` | Requested cumulative quantity cannot exceed eligible delivered less prior returns. |
| `RTR-G02` / `APPROVAL_MISSING` | Exceptions outside synthetic policy require approval record; agent output cannot authorize. |
| `RTR-G03` / `RETURN_OVER_RECEIPT` | Physical receipt cannot exceed authorized remainder. |
| `RTR-G04` / `RETURN_DISPOSITION_UNKNOWN` | No inventory movement until condition/disposition known. Only `RESTOCK` creates positive movement. |
| `RTR-G05` / `RETURN_CREDIT_MISMATCH` | Credit/allowance basis is explicit and cannot exceed eligible line amount. |
| `RTR-G06` / `FIN_REFUND_EXCEEDS_SETTLED` | Settled refunds cannot exceed eligible settled payments net prior refunds. |
| `RTR_EXCHANGE_LINK_MISSING` | Exchange remains `REVIEW` until replacement order ref resolves. |

Instance key is return case ID. Shipment/receipt, inspection, credit, and refund each use their own source event IDs.

## `FCL-01` — finance-close

Purpose: create a reproducible management close for one period/currency/policy version with reconciled revenue, costs, expenses, contribution proxy, and observed cash.

| Contract item | Definition |
|---|---|
| Accountable owner | Finance reviewer; founder approves management-policy choices and final close. |
| Inputs | Period/currency/policy; eligible order/delivery/credit/cost/expense/payment/refund/supplier-payment facts; coverage and quality results; prior close/reopen reason. |
| Outputs | Finance and cash marts, bridge lines, unknown/exception list, close packet, approval record, immutable close receipt. |
| Decision product | Management finance packet separating performance, working-capital timing, and observed cash; it states that it is not formal accounting or tax output. |
| Explicit separation | Ordered amount, payment settlement, delivered revenue candidate, COGS, expense obligation, supplier payment, refund, and cash event remain separate facts and dates. |

### States and legal transitions

| From | Event | To | Required gate(s) |
|---|---|---|---|
| `NEW` | `period_opened` | `OPEN` | Period/currency/policy version valid. |
| `OPEN` | `cutoff_applied` | `DATA_CUTOFF` | `FCL-G01` as-of/freshness/coverage recorded. |
| `DATA_CUTOFF` | `controls_started` | `VALIDATING` | Required source control totals captured. |
| `VALIDATING` | `controls_passed` | `RECONCILING` | `FCL-G02` structural and lifecycle controls pass. |
| `VALIDATING` | `controls_failed` | `BLOCKED` | Exact quality codes and affected metrics recorded. |
| `RECONCILING` | `bridges_reconciled` | `REVIEW_READY` | `FCL-G03` source-to-SQL-to-packet bridges pass. |
| `RECONCILING` | `bridge_failed` | `BLOCKED` | `FIN_BRIDGE_MISMATCH`; close withheld. |
| `REVIEW_READY` | `close_approved` | `CLOSED` | `FCL-G04` human approval names period, policy, packet hash. |
| `CLOSED` | `period_reopened` | `REOPENED` | New approval plus reason; original close remains immutable. |
| `REOPENED` | `cutoff_applied` | `DATA_CUTOFF` | New close version/run ID. |

### Gates and exceptions

| Gate / code | Deterministic rule and behavior |
|---|---|
| `FCL-G01` / `SOURCE_NOT_OBSERVED` | Coverage and cutoff gaps remain unknown; no missing cash/account inferred as zero. |
| `FCL-G02` / `FIN_UNKNOWN_COST` | Affected COGS/profit/margin remain unknown while independently known revenue may publish with limitation. |
| `FCL-G02` / `MONEY_CURRENCY_MIXED` | No aggregation across currencies without valid rate/date/source. |
| `FCL-G03` / `FIN_BRIDGE_MISMATCH` | SQL source totals, mart totals, and packet totals match by component and period. |
| `FCL-G04` / `APPROVAL_MISSING` | Deterministic pass and agent review do not close a period. |
| `FCL_LATE_EVENT` | Post-close event triggers proposed reopen; never silently rewrites the closed receipt. |

Instance key is `<period-start>:<period-end>:<currency>:<policy-version>:<close-version>`.

## `WGR-01` — weekly-growth-review

Purpose: convert a verified weekly analytical snapshot into a small, evidence-ranked set of owner decisions without claiming unsupported causality or impact.

| Contract item | Definition |
|---|---|
| Accountable owner | Growth owner prepares; founder decides; analytics owner validates evidence. |
| Inputs | Warehouse/mart hashes; process health; channel/funnel/cohort/inventory/finance/experiment results; previous decisions; native-agent request and validated response. |
| Outputs | Weekly decision packet, at most five proposals, deferred/blocked items, owner decisions, next evidence dates, agent run receipt. |
| Decision product | Weekly Growth review with facts, unknowns, hypotheses, proposals, primary metric, guardrail, population/window, risk, approver, and closure rule. |
| Explicit separation | Descriptive channel association is not attribution; synthetic experiment is method demonstration, not Alma impact; recommendation is not authorization. |

### States and legal transitions

| From | Event | To | Required gate(s) |
|---|---|---|---|
| `NEW` | `review_opened` | `DRAFT` | Week/cutoff/owners valid. |
| `DRAFT` | `data_bound` | `DATA_READY` | `WGR-G01` immutable dataset/mart/quality hashes bound. |
| `DRAFT` or `DATA_READY` | `critical_quality_failed` | `QUALITY_BLOCKED` | Affected decisions withheld; unaffected facts may remain visible. |
| `DATA_READY` | `agent_task_emitted` | `ANALYSIS_REQUESTED` | `WGR-G02` schema-valid allow-listed request; no live execution claim. |
| `ANALYSIS_REQUESTED` | `agent_response_submitted` | `ANALYZED` | `WGR-G03` response hash/schema/citations/safety pass. |
| `ANALYZED` | `review_packet_built` | `REVIEW_READY` | `WGR-G04` <=5 proposals and ranking inputs known. |
| `REVIEW_READY` | `owner_decision_recorded` | `DECIDED` or `DEFERRED` | Human record per proposal: approve for later manual action, reject, defer, or request evidence. |
| `DECIDED` or `DEFERRED` | `review_archived` | `ARCHIVED` | Packet/decision hashes and next review date present. |
| Any nonterminal state | declared failure | `BLOCKED` | Blocking exception recorded. |

### Gates and exceptions

| Gate / code | Deterministic rule and behavior |
|---|---|
| `WGR-G01` / `DATA_QUALITY_BLOCK` | Critical quality/status prevents affected proposal; unknowns remain explicit. |
| `WGR-G02` / `AGENT_REQUEST_INVALID` | Request lists permitted evidence and forbidden actions and binds exact input hash. |
| `WGR-G03` / `AGENT_EVIDENCE_UNRESOLVED` | Every factual claim resolves; source instructions are data, not commands; unsupported claim rejected/downgraded. |
| `WGR-G04` / `RANKING_INPUT_UNKNOWN` | A proposal needing an unknown score cannot be ranked as known; packet explains deferral. |
| `WGR_CAUSAL_OVERCLAIM` | Any lift/ROI/impact claim without valid design and result is rejected. |
| `WGR_TOO_MANY_ACTIONS` | More than five proposals fails packet validation. |

Instance key is ISO week plus snapshot hash. An agent retry uses a new task attempt ID linked to the same request, and only one reviewed response may be selected for the packet.

## `MTE-01` — market-to-experiment

Purpose: turn dated public market context into a falsifiable Alma hypothesis and governed experiment design, preserving the boundary between external signal and business evidence.

| Contract item | Definition |
|---|---|
| Accountable owner | Market/Growth researcher; Growth owner designs; founder approves launch; analytics owner validates evidence/design. |
| Inputs | Research question; source authority, URL/citation, observed/access date, geography, period, license, method, coverage and limitations; native-agent evidence synthesis; experiment contract and assignment plan. |
| Outputs | Source ledger, observations, unknowns, hypothesis, experiment design, approval state, assignment/outcome marts after synthetic execution, close recommendation. |
| Decision product | Evidence brief plus experiment contract with primary metric, guardrail, population, assignment, window, MDE/sample criterion, estimator, stop/close rule, and prohibited inference. |
| Explicit separation | Search/social/market context is not Alma demand; hypothesis is not fact; assignment is not outcome; observed association is not causal lift. |

### States and legal transitions

| From | Event | To | Required gate(s) |
|---|---|---|---|
| `NEW` | `question_opened` | `QUESTION_OPEN` | Decision relevance and owner present. |
| `QUESTION_OPEN` | `research_started` | `RESEARCHING` | Source plan and access/license boundary recorded. |
| `RESEARCHING` | `evidence_submitted` | `EVIDENCE_REVIEW` | `MTE-G01` provenance complete for every observation. |
| `EVIDENCE_REVIEW` | `evidence_accepted` | `HYPOTHESIS_DRAFT` | `MTE-G02` limitations and unknowns retained; stale/context-only evidence labeled. |
| `HYPOTHESIS_DRAFT` | `experiment_designed` | `APPROVAL_PENDING` | `MTE-G03` full experiment contract and feasibility checks. |
| `APPROVAL_PENDING` | `experiment_approved` | `APPROVED` | `MTE-G04` human approval bound to exact design hash. |
| `APPROVAL_PENDING` | `experiment_rejected` | `REJECTED` | Reason recorded. |
| `APPROVED` | `assignment_started` | `RUNNING` | `MTE-G05` prospective eligibility/assignment before outcomes. |
| `RUNNING` | `window_ended` | `ANALYZING` | Window/stop rule satisfied; no favorable early stop. |
| `ANALYZING` | `analysis_completed` | `CLOSED`, `INCONCLUSIVE`, or `BLOCKED` | `MTE-G06` assignment, sample, estimator, guardrails and result quality evaluated. |

### Gates and exceptions

| Gate / code | Deterministic rule and behavior |
|---|---|
| `MTE-G01` / `MARKET_PROVENANCE_MISSING` | Missing authority/date/scope/license/method/limitation prevents an observation from supporting a hypothesis. |
| `MTE-G02` / `SOURCE_STALE` | Stale evidence may remain context but cannot support an approval recommendation without review. |
| `MTE-G02` / `MARKET_TO_DEMAND_OVERCLAIM` | Claim that context proves Alma demand/sales is rejected. |
| `MTE-G03` / `EXPERIMENT_CONTRACT_INCOMPLETE` | Missing metric/guardrail/population/assignment/window/sample/estimator/close rule blocks approval. |
| `MTE-G04` / `APPROVAL_MISSING` | Agent-generated design is never self-approved. |
| `MTE-G05` / `EXP_ASSIGNMENT_INVALID` | Missing, contradictory, or outcome-late assignment blocks causal analysis. |
| `MTE-G06` / `EXP_EVIDENCE_INSUFFICIENT` | Insufficient sample/window/coverage ends `INCONCLUSIVE`, not zero effect. |
| `EXP_GUARDRAIL_FAILED` | Guardrail breach is explicit in close decision even if primary metric favors treatment. |

Instance key is research question ID until an experiment ID is assigned; the experiment becomes the linked child identity. Source fetch/observation, hypothesis, design, approval, assignment, and outcome have distinct idempotency keys.

## Cross-process joins and order of operations

| Producer | Consumer | Required contract |
|---|---|---|
| `PTS-01` | `LTD-01` | Only accepted receipt movements affect sellable on-hand stock. Open PO or dispatch never does. |
| `LTD-01` | `RTR-01` | Return eligibility derives from delivered line quantity net prior returns. |
| `LTD-01`, `RTR-01`, `PTS-01` | `FCL-01` | Finance close consumes immutable event/bridge facts under a named policy; it does not rewrite operational state. |
| All operational processes | `WGR-01` | Weekly review binds exact mart/process hashes and respects quality/unknown statuses. |
| `MTE-01` | `WGR-01` | Only reviewed hypotheses/designs/results enter weekly review; context remains context. |
| `WGR-01` | Any process | A decision is an approval record only when a human record explicitly references the exact proposed action/design hash; agent recommendations alone have no transition authority. |

## Native-agent request/response contract by process

No process requires an unattended local model executor. The deterministic runner emits a request artifact; an authorized native Codex agent completes the bounded analysis in the development environment; the response is submitted, validated, hashed, and recorded.

| Task ID | Process | Cognitive work | Required evidence | Model routing target |
|---|---|---|---|---|
| `AGT-SUPPLY-01` | `PTS-01` | Explain supply/stock exceptions and rank review questions without calculating stock truth. | Procurement, inventory position/aging, process exceptions, quality. | Terra or Sol. |
| `AGT-FINANCE-01` | `FCL-01` | Explain revenue/cost/cash timing and material unknowns without altering reconciled totals. | Finance, cash, reconciliation, quality, policy. | Sol; Astra on unresolved methodology risk. |
| `AGT-GROWTH-01` | `WGR-01` | Propose <=5 evidence-grounded weekly actions with metric/guardrail/owner. | Channel, funnel, cohort, experiment, inventory, finance, process health. | Sol or Terra. |
| `AGT-MARKET-01` | `MTE-01` | Synthesize public context into falsifiable hypotheses and a governed experiment design. | Source ledger, limitations, existing experiment contract, product hypothesis. | Sol; Astra for adversarial claim review. |
| `AGT-ADVERSARY-01` | All | Challenge architecture, lifecycle integrity, finance/inventory semantics, action safety, evidence, and public claims. | Full acceptance candidate and prior task receipts. | Astra high. |

The response schema must require `facts[]`, `unknowns[]`, `hypotheses[]`, `recommendations[]`, and `challenges[]`. Each fact has evidence refs. Each recommendation carries evidence refs, primary metric, guardrail, window, population, closure rule, `approval_required: true`, and `execution: PROHIBITED`; it cannot embed an approved or executed state.

## Process acceptance queries

The verification runner must execute equivalent checks and store results under the corresponding `ACC-PROC-*` ID:

1. Count catalog definitions and compare exact process IDs and version hashes.
2. For every normal instance, reconstruct current state solely from ordered transition events and compare with stored current state.
3. Attempt every forbidden transition pair and verify no applied business effect.
4. Replay all normal events and compare business row counts, mart totals, and process states before/after.
5. Inject one changed-payload duplicate per process and verify `CTR_DUPLICATE_EVENT_CONFLICT` plus preserved prior facts.
6. Remove each required approval/input in turn and verify the documented waiting/blocked state and unknown propagation.
7. Verify every output/evidence reference resolves and every event-chain hash recomputes.
8. Verify all proposed actions remain nonexecuted and no code path exposes an external write tool.

These checks, plus the scenario expectations in `SCOPE-MATRIX.md`, are the minimum evidence that a process is executable rather than documented only.
