# Scenario comparison

**All commercial values are synthetic; cents MXN. Fixed-seed what-if mechanisms are assumptions, not causal estimates.**

| scenario | units_ordered | net_revenue_cents | contribution_after_variable_cents | cash_movement_cents | low_cover_variants | unknown_cogs_months |
| --- | --- | --- | --- | --- | --- | --- |
| normal | 3620 | 37087457 | 22380131 | 44207671 | 0 | 0 |
| stock_pressure | 3607 | 36794267 | 22236341 | 46329249 | 2 | 0 |
| promotion_illusion | 5068 | 38789806 | 17972364 | 47469633 | 0 | 0 |
| cash_squeeze | 3659 | 37652211 | 22699785 | 43301823 | 0 | 0 |
| missing_cost | 3620 | 37087457 | None | 44207671 | 0 | 13 |
| broken_link | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED | BLOCKED |

Mechanism checks: {"stock_pressure_changes_inventory": true, "promotion_volume_rises_contribution_falls": true, "cash_squeeze_increases_supplier_cash_out": true}

Same seed, changed seed, duplicate delivery and broken-batch preservation: {"same_seed_source_replay": true, "second_seed_valid_and_different": true, "same_batch_noop": true, "bad_batch_rejected_prior_marts_preserved": true, "source_tables": 30, "sql_marts": 11}
