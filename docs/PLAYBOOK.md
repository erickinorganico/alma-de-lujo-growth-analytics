# Growth and operating playbook

All examples are proposed workflows. No external action runs from this repository.

## Weekly review

1. Validate source coverage, freshness/snapshot dates, duplicates, ledger links and money. If BLOCKED, fix/reconcile evidence before using an affected metric. Keep unresolved values unknown.
2. Review the delivered-revenue bridge and observed cash separately. Confirm how much cash funded purchasing versus expenses; a cash outflow is not automatically a loss.
3. Review launched/clearance variants only for possible replenishment. On-hand minus active reservations is available; incoming POs are separate. Verify real lead time, budget, MOQ and historical stockout exposure before any purchase approval.
4. Compare color requests with availability and exposure. Keep sold units, physical returns, credit notes and settled refunds distinct. Do not turn prototypes into replenishment targets.
5. Read channel denominators and 30-day mature cohorts. Keep missing DM traffic unknown. Do not claim campaign ROI or use a partially mature cohort as comparable retention.
6. Review one experiment's predefined closure criteria. Record status as inconclusive when data is insufficient. A recommendation includes an accountable owner and a human approval before execution.

## Approval record template

Record locally: proposal ID/version, evidence receipt hash, exact intended action, SKU/channel, quantity or price where applicable, budget/constraints, authorized human, decision timestamp, validity window, observed outcome and rollback/cancellation path. An approval record documents human authority; the software has no execution tool even if a field says approved.

## Content draft briefs (not published)

| Draft | Research purpose | Required confirmation | Measurement and closure |
|---|---|---|---|
| Color comparison of Pilates socks | Explore stated preference across equal visual exposure | Actual colors/SKUs and permission to use owner-supplied photos; no invented technical/material claim | Valid choices by color plus missing/no preference, 14-day exploratory window, 30-response minimum; otherwise inconclusive |
| Outfit and sock pairing | Test interest in a bundle | Stock, landed cost, discount and return treatment | Predeclare contribution per eligible visitor and return guardrail, 28-day window, baseline/MDE/sample size before launch |
| Studio-use product explanation | Identify information barriers | Owner confirms actual construction, material and intended use; do not claim safety or health benefits | Track attributable product questions and answered/unanswered coverage; descriptive review at day 14, no sales-impact claim |

No marketing message, post or outreach is sent as part of this release. Prices, images, functional claims and purchase decisions remain owner-controlled. Experiment designs are in the generated report and `alma/decisions.py`; outcomes need real approved evidence.

## Data operations and recovery

Each demo is a snapshot, not a transaction-entry application. Inputs live in canonical tables; SQLite is inspectable raw staging. A green build preserves data/report/quality/decision hashes. Intentional red routes use their own output folders. Malformed references or dates withhold unsafe reports; coverage gaps retain nulls and BLOCKED. Use a fresh output path to preserve prior runs. Never mutate a source CSV in place during an audit.

Change management: edit contracts before changing metrics, add a specific regression, run `python -m alma verify`, regenerate the demonstration evidence, inspect report graphs, review release scan, and commit the tested scope. Changing real-data adapters or fiscal policy requires new owner input beyond this synthetic MVP.
