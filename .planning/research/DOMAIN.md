# Domain Research: Final Analytical Coverage

## Essential decisions

Alma de Lujo needs weekly decisions about product/variant demand, accepted inventory, replenishment, complete cost, price contribution, supplier obligations, cash timing, quality/fit issues, drop budgets and sales readiness. Pilates socks in several colors are a product hypothesis; only an eligible observed launch window can validate it.

## Required domains

1. Product, collection/drop, variant and price history.
2. Aggregated sales and fulfilment coverage without fabricated customers or orders.
3. Physical, reserved, accepted, non-sellable, loaned and available inventory.
4. Cost versions/components/allocations, purchases, receipts and obligations.
5. Returns, reported/confirmed reasons, quality inspection and resolution.
6. Reconciled cash opening, processor settlements, committed/expected/scenario events.
7. Budget, commitment, incurred expense, payment and drop/channel allocation.
8. Reusable sales-information readiness and conditional creator-loan custody.

## Decision semantics

- Product/variant sell-through must expose launch window, inventory exposure and return maturity.
- Variant mix is descriptive when a size/color was unavailable.
- Recorded unmet demand is not inferred total demand.
- Complete cost depends on all required components; partial known sum remains partial.
- Contribution margin and markup use different denominators and must remain separate.
- Only accepted/prepared receipt units become available.
- A canonical obligation minus applied observed payments yields the outstanding balance.
- Cash layers keep reconciled, committed, expected and scenario values separate.
- Budget, expense, payment and obligation are different financial states, not additive exposure.

## Acceptance scenarios

- Partial source coverage propagates UNKNOWN only to dependent metrics.
- A duplicate receipt cannot increase inventory twice; a conflicting duplicate is quarantined.
- A new cost version does not rewrite the historical delivery snapshot.
- Twenty ordered, eighteen received, two under inspection and sixteen accepted yields sixteen available and two still to receive.
- A return report, physical return, inspection, refund and restock remain distinct events.
- A stockout-exposed size is not interpreted as weak preference.
- Processor funds do not become available cash until settled.
- Budget allocations reconcile exactly once to their source expense.
- Agents may propose a review but cannot execute any external business action.

## Sources

This synthesis uses the repository PRD/domain contracts, the candidate cost/operations handoff, the v0.3 client contract and the GSD domain audit completed on 2026-09-22. No real Alma sales, supplier, bank or tax records were inspected.
