> Historical v0.1 reference. Current implementation and acceptance: [v0.2 PRD](../specs/PRD.md), [runbook](RUNBOOK-v2.md), and [release evidence](RELEASE.md).

# Portfolio case — from scattered business questions to reproducible decisions

## Problem

Alma de Lujo is an early-stage sportswear brand. There is no sufficient historical business dataset to support an actual performance analysis. The user identified multicolor Pilates socks as a possible hero product. The project asks how to structure the information and decisions needed to validate that belief without manufacturing evidence.

## Delivered capability

An offline Python/SQLite analytical pipeline produces canonical synthetic data, reconciliations, exportable reports and graphs, and versioned decision packets. The work covers market context, merchandise, buying, inventory, orders, returns, customers, management finance and growth experiments. The output is an analytical repository; there is no web application, CRM, ERP or production business integration.

The dataset deliberately keeps order intention, shipment, delivery, payment settlement, revenue credit, physical return and cash refund separate. Missing costs and traffic stay unknown. A zero means an explicitly covered empty value, not an absent source. Exact cents and stock movements drive every numeric result.

## Demonstration to discuss in an interview

1. Run `python -m alma demo`. Inspect the synthetic flag, date, seed, tables and receipt.
2. Follow the revenue-to-cash bridge in `build/demo/report.md`. Explain why an operating surplus can coexist with negative cash movement when purchases and unpaid accruals occur on different clocks.
3. Show 30-day cohort eligibility beside whole-window repeat. Explain why those percentages answer different questions.
4. Run a missing-cost or missing-payment scenario. Show the specific UNKNOWN/FAIL checks, withheld values and blocked decisions; do not describe a red run as a data-source outage or real incident.
5. Inspect one experiment: hypothesis, primary metric, guardrail, population, window, closure and evidence. Explain why a synthetic dataset cannot prove market demand or causal lift.
6. Run `python -m alma verify`, inspect unit/integration/adversarial tests, agent evals and deterministic receipts. Trace a reported value back to canonical data and its contract.

## Contribution and attribution

Erick supplied the business context, product hypothesis, project requirements, publication target and corrections to scope. Codex performed implementation and documentation with explicit native Sol/Luna/Terra/Astra assignments; the parent integrated, reviewed and reran checks. This is an AI-assisted project directed by Erick, not a claim that every line was manually authored. [ORCHESTRATION.md](ORCHESTRATION.md) records actual routing and correction cycles.

This demonstrates analytical modeling, evidence-aware metrics, integration tests, local automation, decision contracts, research discipline and delivery. It does not establish real business adoption, demand, revenue improvement, paid marketing ROI, production reliability, autonomous business execution or fiscal accounting correctness. No private employer code/data or customer PII was reused.

## Useful next boundary

The next step is approved owner discovery and real source reconciliation, not an unsolicited app. Confirm catalog/costs/policies, document source coverage and provenance, minimize customer identity, implement a bounded export adapter, and validate against real authoritative totals under a separate authorization. The completed synthetic MVP gives that future work an executable contract.
