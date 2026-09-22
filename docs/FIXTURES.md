> Historical v0.1 reference. Current implementation and acceptance: [v0.2 PRD](../specs/PRD.md), [runbook](RUNBOOK-v2.md), and [release evidence](RELEASE.md).

# Synthetic fixture guide

`alma.fixtures.generate(seed=42, scenario="normal")` returns a deterministic
90-day dataset ending on `2026-09-21`. Every value is synthetic, dates are ISO
formatted, and money is integer MXN cents. The default seed is 42 so examples,
screenshots, and validation runs can refer to stable IDs and values.

## Scenarios

| Scenario ID | Deliberate condition | Expected use |
| --- | --- | --- |
| `normal` | Complete, reconciled demo data with non-negative stock | Baseline analytics and UI demos |
| `missing_cost` | One Pilates sock variant and its order item have a null cost | Verify unknown cost handling and blocked COGS calculations |
| `negative_stock` | Adds a large negative adjustment to `var-sock-lilac` | Verify inventory integrity failure detection |
| `missing_payment` | Removes settled payment `pay-003` for delivered order `ord-003` | Verify payment completeness checks |
| `duplicate_event` | Duplicates the first opening movement ID | Verify duplicate movement/event detection |

Failure scenarios are intentionally invalid inputs. They preserve the same
catalog and dates as the normal fixture so a validator can isolate the changed
condition.

## Seed behavior

The generator accepts any integer seed and records it in `metadata.seed`.
Seed 42 is the canonical fixture used by the demo. IDs and the current
relationships are stable for a given seed and scenario; callers should pass an
explicit seed when creating a saved evidence packet. The current catalog is
defined as deterministic reference data, so changing the seed does not imply
real-world sampling or a claim about product demand.

## Lifecycle and domain notes

The catalog represents a sportswear brand selling Pilates socks and apparel:
five sock color variants are included alongside leggings, tops, and shorts.
Products carry `idea`, `sample`, `launched`, or `clearance` lifecycle values in
the contract; this fixture uses all four states. The idea-stage recovery wrap
has no sales, and the sample-stage top also has no sales in the current
snapshot. The Pilates sock collection is a product hypothesis represented in
the dataset, not a proven winning product.

Orders cover delivered, shipped, paid, pending, and cancelled states. Costs
are locked on order items. Restock returns create separate positive return
movements; non-restock returns remain customer-service evidence without adding
stock. Credit notes reduce recognized revenue, while refunds are separate cash
events. Partial and in-transit purchase orders, DM traffic with null visits,
expenses with accrual/cash differences, marketing spend matched to funnel
spend, a zero-stock idea SKU, and unmet demand are included so consumers can
distinguish unknown values from zero. The Lilac unmet-demand row is explicitly
historical and hypothetical; the concept-wrap row represents a request for a
SKU with no opening stock.
