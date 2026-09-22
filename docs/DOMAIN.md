# Alma de Lujo Growth OS — provisional domain contract

Status: **v0 provisional; owner discovery required**
Applies to: synthetic local MVP only
Contract principle: observed facts, inferred hypotheses, and authorized actions are separate records

## Confirmed discovery record

As of 2026-09-22, the owner has confirmed:

- Alma de Lujo is a **sportswear** brand.
- **Multicolor Pilates socks** are a potential hero product.
- The hero-product statement is a **hypothesis**, not a measured result: there are no observed Alma sales yet that establish demand, conversion, sell-through, margin, repeat purchase, or product-market fit.

The synthetic fixtures may include Pilates socks across color variants to demonstrate size/color/SKU analysis. Every generated report must label all results synthetic, and no generated sales pattern may be cited as evidence that socks will be the real hero product.

## Contract conventions

- Every record has a stable local ID, `source_type`, `source_record_id` when applicable, `observed_at_utc`, `ingested_at_utc`, `run_id`, and `is_synthetic`.
- Events are append-only. Corrections use a superseding event/reference; source events are not silently edited.
- Timestamps are ISO-8601 UTC. Local reporting dates include the IANA timezone used to derive them. The provisional timezone is `America/Tijuana` until the owner confirms the operating location and cutoff.
- Money uses signed integer cents and a required ISO-4217 currency. The MVP uses MXN and blocks aggregation across currencies without an explicit rate, rate date, and source.
- Quantities are integer units for the apparel MVP. Fractional quantities are invalid unless a later contract version introduces a unit of measure.
- Enumerations contain `UNKNOWN` when the source cannot establish a value. `NOT_APPLICABLE`, `NOT_COLLECTED`, `NOT_OBSERVED`, `REDACTED`, and `FAILED_TO_LOAD` are distinct reasons, not aliases for null or zero.
- Derived records carry contract version, source evidence references, calculation timestamp, status, and freshness. The calculation engine must not turn an invalid or absent denominator into `0%`.
- Facts can be `VALID`, `PARTIAL`, `STALE`, `CONTRADICTORY`, `UNKNOWN`, `REVIEW`, `BLOCKED`, or `FAILED`. Only `VALID` facts feed unrestricted green-path metrics.
- A business action is never implied by a recommendation. Purchases, price changes, inventory adjustments, refunds, publications, messages, payments, and external connections require explicit human approval.

## Provisional glossary

| Term | Provisional definition | Discovery issue |
|---|---|---|
| Product | A sellable design/style independent of size and color. | Confirm whether bundles or made-to-order designs exist. |
| Variant / SKU | A specific product-size-color combination tracked for price, cost, and stock. | Confirm SKU naming and whether barcode is needed. |
| Hero-product hypothesis | A product proposed for focused validation because it may anchor assortment, content, or acquisition. It is not a bestseller claim. | Multicolor Pilates socks are the current candidate; define test evidence and rejection criteria. |
| Collection | A merchandising grouping with lifecycle dates and intent. | Confirm overlapping collections and evergreen products. |
| Standard cost | Owner-approved planning cost per unit in cents, versioned by effective date. | Confirm inclusions: garment, decoration, packaging, inbound freight, duties. |
| Landed cost | Observed allocated acquisition cost for a received unit. | Allocation method is unknown; do not use until approved. |
| Supplier | Entity providing goods or production services. Synthetic only in MVP. | Confirm consignment, deposits, lead time, and minimum order rules. |
| Purchase order (PO) | Intent to buy specified units at expected cost; not inventory or cash by itself. | Confirm approval and cancellation states. |
| Receipt | Physical acceptance of units from a supplier, increasing on-hand inventory. | Confirm inspection/rejection workflow. |
| Inventory movement | Immutable signed effect on stock, typed and linked to its business cause. | Confirm location granularity and adjustment authority. |
| On hand | Physical accepted units derived from posted stock movements at an as-of time. | Confirm whether damaged/quarantine units are separate condition/location. |
| Reserved | On-hand units temporarily committed to an open order and not yet shipped/released. | Confirm reservation timing and expiry. |
| Available | `on_hand - reserved`; excludes inbound stock. | Confirm whether safety stock should be shown separately. |
| In transit | Open PO quantity dispatched/expected but not received; never on hand. | Confirm whether supplier-dispatched evidence exists. |
| Order | Customer purchase intent with priced lines and lifecycle state. An order is not payment, revenue, shipment, or cash. | Confirm sales channels and order acceptance point. |
| Gross merchandise amount | Sum of line list/regular prices times quantity before discounts. | Confirm whether displayed price is tax-inclusive. |
| Discount | Explicit reduction from gross merchandise amount, allocated to lines where possible. | Confirm coupon, manual, bundle, loyalty, and shipping discounts. |
| Payment | Attempt/settlement associated with an order. Successful payment is distinct from bank cash availability. | Confirm cash, transfer, gateway, COD, and fee treatment. |
| Shipment / fulfilment | Transfer of units to customer delivery flow, reducing on-hand stock. | Confirm pickup and split shipment behavior. |
| Return | Physical/customer decision flow for merchandise coming back. It affects product/stock only when received and inspected. | Confirm return window and condition outcomes. |
| Refund | Monetary settlement returned/owed to a customer. It does not imply a physical return. | Confirm partial refund, store credit, fee, and timing policies. |
| Cancellation | Order/line termination before the remaining obligation is fulfilled. | Confirm whether post-shipment reversal is ever called cancellation. |
| Net revenue | Provisional management measure under a declared recognition policy; not formal accounting revenue. | Owner/accountant must approve recognition date, taxes, shipping, returns, and refunds treatment. |
| COGS | Cost basis of units whose sale is recognized under the selected policy. | Confirm standard versus actual/landed cost and cost revisions. |
| Gross profit | `net_revenue - COGS` when both are valid and same currency/period. | Management metric only until accounting review. |
| Operating expense | Non-inventory expenditure categorized by purpose and event/payment date. | Confirm chart of categories, accruals, owner contributions, and taxes. |
| Contribution proxy | Net revenue less COGS and explicitly included variable expenses. | Included expense categories must be named; never call it net profit. |
| Customer | Stable privacy-safe party identity used to connect orders where justified. | Real-data identity resolution and consent are out of MVP. |
| Lead | Person/party expressing traceable purchase interest before an order. | Confirm DM/manual lead capture and retention. |
| Visit/session | Channel interaction with source attribution under a declared identity/session rule. | Web tracking does not yet exist. |
| Campaign | Coordinated set of content/spend/audience records with an objective and dates. | Confirm channel taxonomy and spend source. |
| Assisted order | Order with a qualifying prior touch under a declared window/rule. Association only. | Define identity, lookback, and attribution model. |
| Cohort | Population grouped by a declared first qualifying event and period. | Confirm whether acquisition means lead, first order, or first paid order. |
| Experiment | Versioned hypothesis, population, assignment, metric, guardrail, window, and close decision. | Observational campaigns must not be mislabeled experiments. |
| Market signal | Dated observation from a named external/public source with scope and limitations. | Source access/licensing and relevance require review. |
| Decision packet | Versioned read-only bundle of facts, evidence, unknowns, hypotheses, and proposed actions. | Confirm decision cadence and approvers. |

## Domain boundaries and canonical grains

### Market intelligence

- `market_source`: one source/version with authority, URL or citation, access date, geography, period, licensing note, and limitation.
- `market_observation`: one metric/topic/geography/time-window observation from one source.
- `market_hypothesis`: one falsifiable interpretation linked to observations, never promoted to fact.
- `market_research_question`: one open question with owner and review status.

Search interest, social engagement, and survey context are signals. They do not equal demand, sales, market size, or forecasted orders.

### Product and merchandising

- `product`: one design/style.
- `variant`: one product × size × color configuration.
- `collection` and `collection_variant`: versioned merchandising membership.
- `price_version`: one variant/channel/currency/effective interval price.
- `cost_version`: one variant/cost-type/currency/effective interval amount.
- `product_lifecycle_event`: one transition such as `IDEA`, `SAMPLE`, `APPROVED`, `LAUNCHED`, `PAUSED`, `MARKDOWN`, `RETIRED`.

Price and cost histories are effective-dated. Updating the current price/cost does not rewrite prior order lines or shipment cost basis.

For v1 fixtures, sportswear is the business category and multicolor Pilates socks should appear as a product with distinct color variants. Synthetic performance must not be engineered or narrated as proof of actual demand. A future hero-product decision needs observed evidence and a predeclared evaluation window, including conversion, unit contribution, sell-through, return/refund rate, stockout exposure, and repeat/attach behavior where available.

### Suppliers and purchasing

- `supplier`: one supplier identity.
- `purchase_order`: one commercial intent with approval and lifecycle state.
- `purchase_order_line`: one PO × variant line.
- `supplier_dispatch`: one dispatched quantity for a PO line, if observed.
- `goods_receipt`: one receipt transaction at a location.
- `goods_receipt_line`: one receipt × PO line × accepted/rejected condition.
- `supplier_return`: one outbound return transaction to a supplier.
- `purchase_payment`: one supplier-related cash settlement, separate from receipt and cost recognition.

Expected, ordered, dispatched, received, accepted, invoiced, and paid quantities/amounts must remain separate.

### Inventory

- `inventory_movement`: one immutable quantity effect for one variant, location, event time, type, and business reference.
- `inventory_reservation_event`: one reserve/release/consume effect tied to an order line.
- `inventory_count`: one observed physical count for a variant/location/time.
- `inventory_snapshot`: one derived balance for a variant/location/as-of time/run.

Allowed physical movement types and sign:

| Type | On-hand sign | Required reference |
|---|---:|---|
| `OPENING_BALANCE` | + | approved opening event |
| `PURCHASE_RECEIPT` | + | accepted goods receipt line |
| `CUSTOMER_RETURN_RECEIPT` | + | inspected return line with restock disposition |
| `SHIPMENT` | - | fulfilled order line |
| `SUPPLIER_RETURN` | - | supplier return line |
| `ADJUSTMENT_IN` | + | approved adjustment reason |
| `ADJUSTMENT_OUT` | - | approved adjustment reason |
| `TRANSFER_OUT` / `TRANSFER_IN` | - / + | paired transfer ID |

Reservations do not change on hand. Shipment consumes the reservation and reduces on hand. A customer return request does not add inventory; only a received, inspected, restockable return movement does.

### Commerce and customers

- `customer`: one synthetic customer identity in MVP.
- `lead`: one captured interest identity/channel/time.
- `visit`: one synthetic session/channel/start time.
- `touchpoint`: one customer/lead/visit interaction with campaign/content evidence.
- `order`: one customer/channel order.
- `order_line`: one order × variant × agreed unit price/cost context.
- `discount_allocation`: one promotion/discount allocation to an order or line.
- `payment_event`: one payment attempt, authorization, settlement, failure, or reversal.
- `fulfilment` and `fulfilment_line`: one shipment/pickup and its line quantities.
- `return` and `return_line`: one return workflow and line quantities/reasons/dispositions.
- `refund_event`: one refund attempt/settlement/failure tied to order/payment and optionally return.

Order lifecycle and settlement lifecycle are independent state machines. A valid scenario may include:

- paid order with no shipment yet;
- shipped order with payment pending under an approved method;
- refund without return (goodwill or shipping correction);
- return without refund yet (inspection pending);
- partial return and partial refund;
- exchange represented as returned units plus a new/replacement order flow.

### Management finance

- `expense`: one categorized obligation/expenditure with event date, amount, currency, evidence, and status.
- `cash_event`: one observed inflow/outflow at a declared account/cash location; synthetic in MVP.
- `fee_event`: one payment/channel fee linked to a settlement where possible.
- `finance_period`: one reporting period/currency/policy version.
- `finance_bridge_line`: one auditable contribution from source record to a derived measure.

Formal accounting, tax, invoicing, depreciation, owner equity, accruals, and bank reconciliation remain outside v0 unless a qualified owner approves explicit contracts.

### Growth, Product, and experiments

- `channel`, `campaign`, and `content_asset`: one taxonomy item/versioned activity.
- `campaign_spend`: one spend event with currency and evidence.
- `funnel_event`: one actor/session/order stage observation.
- `experiment`: one hypothesis and governance record.
- `experiment_assignment`: one eligible unit assignment; missing assignment blocks causal interpretation.
- `experiment_observation`: one outcome/guardrail observation for an assigned unit.

Every recommendation must include a primary metric, guardrail, population, observation window, minimum evidence criterion, closing rule, owner, and approval requirement. Without prospective assignment or a defensible quasi-experimental design, results are descriptive associations.

### Decisions and agents

- `evidence_ref`: one immutable artifact/table-row/query-result reference with hash where practical.
- `decision_packet`: one versioned decision context.
- `claim`: one factual statement supported by evidence refs and status.
- `unknown`: one unanswered material fact with reason and resolution owner.
- `hypothesis`: one proposed explanation with test path.
- `proposed_action`: one bounded action, expected effect, risk, approver, and `approval_status`.

Agents are read-only analysts in the MVP. Deterministic pipelines calculate metrics; agents may summarize validated artifacts but cannot create facts or execute actions.

## Event catalog and state transitions

| Event | Trigger | Required links | Principal effect | Invalid examples |
|---|---|---|---|---|
| `product_lifecycle_changed` | Approved product decision | product, from/to state | Changes lifecycle state | Launch from unknown product; transition without actor/time. |
| `price_effective` | Approved price version | variant, channel, currency | Defines future selling price | Overlapping active intervals for same key. |
| `purchase_order_approved` | Human approval | PO, approver | Allows supplier commitment | Approval missing owner or negative quantity. |
| `supplier_dispatched` | Dispatch evidence | PO line | Increases observed in-transit quantity | Quantity exceeds unresolved ordered quantity. |
| `goods_received` | Physical receipt | PO line, location | Posts accepted inventory receipt | Receipt before PO, duplicate receipt ID. |
| `inventory_reserved` | Order allocation | order line, variant/location | Increases reserved quantity | Reservation exceeds eligible available stock. |
| `inventory_reservation_released` | Cancel/expiry/reallocation | prior reservation | Reduces reserved quantity | Release exceeds remaining reservation. |
| `order_placed` | Customer intent captured | order and lines | Creates commercial intent | Missing price/currency or zero lines. |
| `payment_status_changed` | Payment evidence | payment, order | Updates settlement state | Refunded amount exceeds settled amount. |
| `fulfilment_shipped` | Units leave stock | fulfilment/order lines | Posts shipment movement | Quantity exceeds unfulfilled ordered quantity. |
| `return_requested` | Return intent | order line | Opens return workflow only | Quantity exceeds eligible fulfilled quantity. |
| `return_received` | Physical return inspected | return line, location/disposition | May post restock movement | Restock before received/inspection. |
| `refund_status_changed` | Monetary refund evidence | refund, order/payment | Updates customer settlement | Refund treated as stock movement. |
| `expense_recorded` | Evidence captured | category, amount/currency | Adds management expense | Missing date/evidence status. |
| `cash_observed` | Cash/bank evidence | account, amount/currency | Adds observed cash movement | Inferred from order without cash evidence. |
| `touchpoint_observed` | Channel interaction evidence | actor/session, channel | Adds funnel/attribution input | Fabricated identity linkage. |
| `experiment_assigned` | Eligibility and assignment | experiment, unit, variant | Establishes analysis population | Assignment recorded after outcome. |
| `decision_packet_created` | Valid analytics run | run, evidence refs | Creates review artifact | Claim without evidence or action pre-approved. |

Events carry `event_id`, `event_type`, `occurred_at_utc`, `recorded_at_utc`, actor/source, entity links, payload version, prior-event/supersession link where relevant, and idempotency key. Duplicate idempotency keys with different payloads are `CONTRADICTORY` and block publication.

## Inventory equations and invariants

At variant × location × as-of timestamp:

```text
on_hand_units = sum(posted inventory movement signed quantities)
reserved_units = sum(active reserve) - sum(release or consume)
available_units = on_hand_units - reserved_units
in_transit_units = dispatched_not_received_units (when dispatch evidence exists)
open_po_units = approved_ordered_units - cancelled_units - accepted_units - supplier_returned_before_acceptance_units
```

Key invariants:

1. `on_hand_units`, `reserved_units`, and `available_units` are never sourced from manually overwritten current-state fields.
2. Every non-opening movement references one business event; transfers are balanced pairs.
3. Posted shipment units cannot exceed eligible fulfilment quantity; received-return units cannot exceed eligible returned quantity.
4. Negative on-hand or available stock is a blocking exception unless an explicit, owner-approved backorder contract later allows it.
5. Inventory value is `sum(on_hand units by cost layer × valid unit cost cents)`. Any material unit with unknown cost makes the affected value and margin `UNKNOWN/REVIEW`; unknown cost is never zero.
6. A physical count is evidence for reconciliation. Its difference creates a proposed adjustment; only an approved adjustment event changes the ledger.

## Commerce and finance equations

All equations operate in one currency and policy version.

```text
gross_merchandise_cents = sum(order_line_quantity × agreed_list_unit_price_cents)
merchandise_discount_cents = sum(valid line/order discount allocations)
ordered_merchandise_cents = gross_merchandise_cents - merchandise_discount_cents
settled_payment_cents = sum(successfully settled payment events) - payment reversals
settled_refund_cents = sum(successfully settled refund events)
observed_net_customer_settlement_cents = settled_payment_cents - settled_refund_cents
```

The exact v1 demo policy in `docs/INTERFACES.md` is provisional: recognize revenue on delivery; credit notes reduce revenue on their event date; refunds reduce cash only; and restocked returns reverse standard COGS separately. Order-item costs are locked for the demo. Synthetic prepaid shipped/delivered orders must settle no later than their posted shipment movement. Synthetic expenses categorized as marketing reconcile to funnel spend. These rules enable deterministic fixtures and do not represent approved accounting or operating treatment. A future policy change must be named/versioned and must not silently rewrite prior outputs.

```text
recognized_gross_sales_cents = eligible fulfilled quantity × allocated pre-discount unit amount
recognized_discount_cents = discounts allocated to eligible fulfilled quantity
recognized_return_allowance_cents = amount reversed under the selected return/refund policy
net_revenue_cents = recognized_gross_sales - recognized_discount - recognized_return_allowance
cogs_cents = sum(eligible fulfilled quantity × valid cost basis per unit), reversed per approved return disposition/policy
gross_profit_cents = net_revenue_cents - cogs_cents
gross_margin_rate = gross_profit_cents / net_revenue_cents
contribution_proxy_cents = gross_profit_cents - explicitly enumerated variable expense cents
observed_net_cash_cents = observed cash inflows - observed cash outflows
```

If `net_revenue_cents = 0`, gross margin rate is `NOT_APPLICABLE`, not zero. If revenue or COGS is invalid/unknown, profit and margin inherit `UNKNOWN/REVIEW`. Taxes, shipping revenue/cost, gateway fees, and return handling are separate bridge lines until the owner and accountant approve their classification.

## Provisional metric contracts

Each metric output must include: `metric_id`, definition version, value and unit, entity grain, population, period start/end, as-of time, timezone, currency where relevant, numerator/denominator, source refs, exclusions, freshness, synthetic flag, quality status, and limitation.

| Metric | Grain / time basis | Provisional formula | Unknown and failure behavior | Decision use |
|---|---|---|---|---|
| On-hand units | variant × location × as-of | Sum signed posted stock movements | Block if duplicate/conflicting movement or broken transfer | Count/reconciliation |
| Available units | variant × location × as-of | On hand minus active reserved | Block if reservation ledger invalid | Fulfilment/replenishment review |
| In-transit units | variant × PO/location × as-of | Evidence-backed dispatched minus accepted received | `UNKNOWN` when dispatch is not observed; do not substitute open PO | Supply visibility |
| Inventory value at cost | variant/location × as-of | Valid on-hand cost layers in cents | Withhold affected value when cost missing | Working-capital view |
| Sell-through rate | variant/collection × window | Gross posted shipment units less restocked customer-return units / (opening units + purchase receipts) | `NOT_APPLICABLE` if denominator zero; `UNKNOWN` when movements or variant coverage is absent | Assortment review |
| Stockout exposure | variant × day/window | Days or sessions with valid demand opportunity while available = 0 | `UNKNOWN` without demand/availability observation coverage | Lost-demand hypothesis |
| Slow-stock candidate | variant × as-of | Rule using age, available units, and valid recent fulfilled demand | Recommendation only; thresholds owner-approved | Markdown/reallocation review |
| Reorder candidate | variant × as-of | Demand-rate scenario versus available + evidence-backed inbound and lead-time scenario | Never an automatic PO; `REVIEW` if lead time/demand sparse | Purchase review |
| Gross merchandise amount | order/period by order date | List amount before discounts | Block invalid line amounts/currency | Pricing/volume context |
| Net revenue candidate | period by named recognition policy | Recognized gross less discounts and recognized return allowance | Withhold when policy/source bridge invalid | Management performance |
| Gross profit | period/variant/collection | Net revenue minus COGS | Withhold if either component unknown | Merchandising/finance |
| Gross margin rate | same as gross profit | Gross profit / net revenue | N/A at zero; unknown if inputs unknown | Pricing/cost review |
| Observed net cash | period by cash event date | Cash inflows less cash outflows | `UNKNOWN` for missing accounts/coverage, never inferred from orders | Liquidity watch |
| Average order value | eligible order population × period | Declared order value / count of eligible orders | Population must state placed/paid/fulfilled; no mixed status | Commerce review |
| Unit return rate | variant/period with maturation window | Received returned units / eligible fulfilled units | `PARTIAL` until window matures; separate request/receipt | Quality/fit review |
| Refund rate | period | Settled refunded cents / eligible settled payment cents | Independent of return rate; N/A if denominator zero | Settlement/customer experience |
| Repeat customer rate | acquisition cohort × mature window | Customers with qualifying repeat order / eligible acquired customers | Identity and qualifying-order rule required | Retention hypothesis |
| Funnel conversion | declared stage pair × cohort/window | Entities reaching later stage / eligible entities at prior stage | `UNKNOWN` without identity/event coverage | Funnel diagnosis |
| Campaign assisted orders | campaign × attribution window | Orders with qualifying prior touch under named rule | Association only; missing identity reduces coverage | Content/campaign review |
| Customer acquisition cost | campaign/cohort | Eligible acquisition spend / newly acquired customers | Withhold until spend and acquisition coverage valid | Spend efficiency context |
| Experiment primary effect | experiment × variant/window | Predeclared estimator on assigned eligible population | `BLOCKED` without valid assignment, sample/window, and guardrails | Close experiment |

No metric is “final” merely because its query runs. Promotion requires owner-approved meaning, test coverage, reconciliation where applicable, and displayed limitations.

## Controlled-failure catalog

| Code | Condition | Required behavior |
|---|---|---|
| `CTR_DUPLICATE_EVENT_CONFLICT` | Same idempotency key, different payload | Roll back load; failed receipt; retain prior valid build. |
| `CTR_BROKEN_REFERENCE` | Event points to missing entity/source | Reject record or batch per contract; never create placeholder fact silently. |
| `STATE_INVALID_TRANSITION` | Lifecycle transition not allowed | Block affected entity and downstream metrics. |
| `INV_NEGATIVE_AVAILABLE` | Available stock below zero | Block publication of affected inventory/replenishment measures. |
| `INV_LEDGER_SNAPSHOT_MISMATCH` | Derived ledger differs from comparison snapshot/count beyond approved tolerance | Surface delta and proposed investigation; never overwrite ledger automatically. |
| `INV_TRANSFER_UNBALANCED` | Transfer pair absent or unequal | Block location balances. |
| `FIN_UNKNOWN_COST` | Eligible unit lacks valid cost basis | Withhold COGS, profit, and margin for affected population. |
| `FIN_REFUND_EXCEEDS_SETTLED` | Refund exceeds eligible settled payment | Block finance/settlement output. |
| `FIN_BRIDGE_MISMATCH` | Source-to-metric bridge does not reconcile | Block affected metric and publish failure receipt. |
| `MONEY_CURRENCY_MIXED` | Aggregation includes currencies without rates | Block aggregation. |
| `METRIC_ZERO_DENOMINATOR` | Ratio denominator is valid zero | Emit `NOT_APPLICABLE`, no numeric rate. |
| `SOURCE_NOT_OBSERVED` | Expected source/event absent without proof of zero | Emit `UNKNOWN/NOT_OBSERVED`. |
| `SOURCE_STALE` | Source exceeds approved freshness threshold | Mark stale and withhold time-sensitive recommendations. |
| `EXP_ASSIGNMENT_INVALID` | Assignment missing, late, or contradictory | Block causal effect claim. |
| `PUBLISH_ARTIFACT_INVALID` | JSON/schema/hash/reconciliation fails | Do not treat the build as verified; preserve prior owned analytical artifacts. |

## Owner discovery questions

Answers should be recorded as decisions with date, owner, confidence, and contract fields affected.

| ID | Question | Why it changes the contract | Recommended accountable owner |
|---|---|---|---|
| `DISC-01` | Which city/timezone and business-day cutoff govern daily reporting? | Period attribution and freshness | Founder |
| `DISC-02` | Which channels will accept orders first, and what event counts as an accepted order? | Order grain/states and funnel | Founder + Growth |
| `DISC-03` | Which payment methods exist, and when is each considered settled/available cash? | Settlement and cash bridge | Founder + finance reviewer |
| `DISC-04` | Are displayed prices tax-inclusive, and what invoicing/tax obligations apply? | Revenue bridge; requires qualified advice | Founder + accountant |
| `DISC-05` | What costs belong in standard/landed product cost? | Inventory value and COGS | Founder + accountant |
| `DISC-06` | What locations/conditions exist: sellable, damaged, sample, quarantine, consignment? | Inventory grain and availability | Operations |
| `DISC-07` | When are units reserved, when does reservation expire, and are backorders allowed? | Available stock and order state | Operations |
| `DISC-08` | What evidence and approval permit an inventory adjustment? | Ledger governance | Operations + founder |
| `DISC-09` | What are cancellation, return, exchange, refund, and store-credit policies? | Independent state machines and metrics | Founder + operations |
| `DISC-10` | When should management revenue and COGS be recognized for internal decisions? | Finance metric policy | Founder + accountant |
| `DISC-11` | Which expenses are variable for the contribution proxy? | Contribution definition | Founder + accountant |
| `DISC-12` | What decisions are made daily, weekly, monthly, and by whom? | Report and decision-packet scope | Founder |
| `DISC-13` | What evidence justifies reorder, markdown, price, or assortment review, and what would confirm or reject the Pilates-socks hero hypothesis? | Recommendation rules/guardrails; prevents synthetic sales from becoming product evidence | Founder + merchandising |
| `DISC-14` | How will DMs/leads/customers be identified with minimum necessary personal data? | Funnel, cohorts, privacy | Founder + Growth/privacy reviewer |
| `DISC-15` | Which campaign/content taxonomy and attribution window are useful? | Growth metric coverage | Growth |
| `DISC-16` | What constitutes a repeat customer and a mature cohort window? | Retention metrics | Founder + Growth |
| `DISC-17` | Which public market sources may be used under their terms, and for which questions? | Market evidence authority | Research owner |
| `DISC-18` | Who approves purchases, prices, refunds, messages, publication, and real-data connections? | Action gates and separation of duties | Founder |
| `DISC-19` | What files/exports will exist before APIs, and who owns their quality? | Adapter priority and provenance | Operations + data owner |
| `DISC-20` | What retention, deletion, backup, and access policy applies once data becomes real? | Privacy/security and recovery | Founder + privacy reviewer |
| `DISC-21` | Which Pilates-sock attributes matter operationally: grip, material, size system, colorway, pack/bundle, packaging, care, and quality checks? | Product/variant grain, supplier acceptance, returns, and content taxonomy | Founder + merchandising + operations |

## Promotion path from provisional to approved

1. Record the owner answer and affected decision, not just a free-form note.
2. Update the glossary, state/event contract, metric formula, and fixture together.
3. Add or update green, edge, and controlled-failure tests.
4. Replay deterministic fixtures and reconcile inventory/finance bridges.
5. Obtain the named business/finance/privacy approval where applicable.
6. Increment the contract version and publish a receipt describing the change.

Approval of a definition does not prove source availability, report freshness, stakeholder adoption, or business impact. Those remain separate evidence states.
