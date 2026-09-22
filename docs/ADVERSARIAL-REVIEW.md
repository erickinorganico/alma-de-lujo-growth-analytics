# Adversarial review — findings and correction checks

Review date: 2026-09-22. Scope: local synthetic analytics, validation, storage, decision policies, and the then-present report viewer/server. Implementation changed concurrently. This records the findings and their final bounded regression disposition below.

## Blocking findings reported to implementation owner

1. **Invalid references or delivery evidence crash analytics.** Starting with `generate()`, setting `tables.order_items[0].order_id = 'MISSING'` and calling `analyze()` produced `KeyError: 'MISSING'`. Setting a delivered order's `delivered_date = None` produced `TypeError: 'NoneType' object is not subscriptable`. Validation records failures, but analytics continued through unsafe joins/date slicing. The CLI build already guarded foreign-key failures, so the first failure affects the direct analytics API; the missing delivery date also affected the build path. Required disposition: stop with a deliberate `ContractError` before unsafe calculations, with regression tests for both paths.

2. **Missing coverage retains apparently known dependent inventory values.** Starting with `generate()`, setting `metadata.coverage.variants = False` and calling `analyze()` produced report `BLOCKED`, but `inventory_value_cents = 4143900` and the first inventory row remained `SLOW`. The global block prevents a clean decision packet, but an unknown source still appears as a precise valuation and operational classification. Required disposition: propagate unknown coverage through dependent values and status; check the dependency matrix beyond this one table.

3. **The former viewer had raw status attribute interpolation.** `web/app.js` used an unescaped input inside `class="status ${...}"`. Product lifecycle and purchase status were unrestricted strings in the import contract, giving imported text a path to inject markup/attributes. The built-in server CSP limited script execution but did not make raw HTML interpolation safe. This was a source-level finding, not a demonstrated browser exploit. The parent is removing the web/server surface to comply with the corrected handoff, which removes this finding's affected surface; confirm removal before closure.

The first two findings were exercised with adversarial synthetic inputs using the bundled Python runtime. No real records, external services, or business actions were used.

## Inspected controls and bounded limitations

- Integer-cent revenue, discount, credit, standard COGS, expense, and cash arithmetic were inspected. Revenue uses delivered orders; credits reduce revenue on their own date; settled refunds affect cash separately. Restock returns reverse the historical order-line standard cost. No additional arithmetic defect was established in this bounded pass.
- The trend assigns supplier and expense paid amounts to the only date available on each record. Separate payment-event dates are absent from this compact schema. Treat this as a provisional synthetic model limitation, not verified real cash timing.
- Standard-cost inventory uses current variant cost; recognized COGS uses the cost locked on each order line. This is a planning valuation, not an actual-cost inventory reconciliation or formal accounting.
- `execute_action()` always raises `PermissionError`; generated decision actions require approval and have execution `BLOCKED`. Decision evidence references are checked for resolvability. No external execution capability was found in inspected policy code.
- CSV import checks fixed schemas, integer types, metadata currency, explicit synthetic declaration, and per-table file-size limits. The synthetic flag is a declared trust boundary; it cannot prove that a user-supplied file contains no real data. SQLite writes use fixed identifiers and parameterized values; reads open SQLite in read-only mode.
- The former local server bound to loopback and allowlisted four assets; data tables, database files, and directory listings were not exposed by its handler. This is superseded by the planned server removal.
- The corrected project scope is a reproducible analytical repository, not a web application. Browser-specific findings must not justify retaining a surface excluded by the handoff.

## Correction checks and newly exposed issues

A second bounded pass examined the analytics-only implementation and exercised `tests/test_adversarial.py` against concurrent local changes.

- **Original reference/date crashes corrected:** both exact invalid inputs now raise deliberate `ContractError` before calculation.
- **Original inventory valuation gap corrected:** with either variants or movements coverage false, snapshot and per-SKU valuation, on-hand quantity, and sell-through are unknown. All decision packets are blocked. `PRELAUNCH` can remain as a product lifecycle label; it does not authorize replenishment.
- **Former web injection surface removed:** the active `web` directory is absent and the CLI contains no server command or implementation. Static report escaping was examined separately.
- **Financial bridges passed:** for the normal synthetic input, monthly net revenue, COGS, OPEX, and net cash sum to their snapshot KPIs; channel recognized revenue sums to the same revenue KPI.
- **New P2 reporting blocker:** missing purchase coverage rendered `Compras: 0`; missing products coverage rendered `productos: 0`; missing orders coverage rendered `Cohortes con madurez de 30 días: 0 de 0`; missing movement coverage rendered zero SKUs requiring review. These are unknown-to-zero conversions in the derived narrative despite the global `BLOCKED` state. Four regression subcases reproduce them.
- **New P2 report presentation blocker:** generated tables were escaped as text in Markdown and escaped again in HTML, so both artifacts displayed serialized table markup instead of usable tables. Escaping source values must remain in place while trusted generated table structure renders normally.
- **New P2 API error handling gap:** `analyze({})` raises `KeyError` because it reads `tables` before contract validation. Validate the outer shape first, then raise `ContractError` for invalid input. This affects direct callers; it does not bypass the fixed CSV import contract.

The first second-pass test run comprised five tests: three passed, one produced four failing coverage subcases, and one errored on malformed input. These failures were promptly sent to the implementation owner. This run is a red regression baseline, not final verification.

## Closure state

The next correction pass verified deliberate `ContractError` for malformed input, all four original narrative coverage cases, and explicit trusted HTML tables with source text escaped. A table-shaped payload, `<table><img src=x onerror=alert(1)></table>`, stays escaped while generated `<table>` and `<th>Canal</th>` remain real report structure. The five adversarial tests and four reporting tests initially passed.

Source inspection then found the inventory narrative's completeness predicate still depended only on movement coverage. Two additional subcases, variants coverage false and reservations coverage false, reproduced the same false-zero SKU count. They were added to the existing regression test and failed; the remainder passed. The final implementation checks all six source dependencies (variants, products, movements, order items, orders, reservations) and requires known available quantities and costs before reporting a complete SKU-classification count. Markdown now uses generated pipe tables with escaped cell separators; HTML retains separately generated trusted tables and escapes source values.

**PASS for the bounded synthetic MVP review: no unresolved blocking finding from this audit.** On the final source, the reviewer directly reran `python -m unittest discover -s tests -p test_adversarial.py -v` and `python -m unittest discover -s tests -p test_reporting.py -v` with the bundled runtime. All five adversarial tests (including expanded coverage subcases) and all four reporting tests passed. The latter verifies table-shaped injection remains escaped, generated HTML tables remain structural, signed/zero chart semantics, and missing evidence display. This disposition does not establish real-data accuracy, accounting-policy approval, actual demand, publication safety, or production readiness. Full-suite, clean-install, preview, and publication checks are owned by the parent workflow. No implementation edits or external actions were performed by this reviewer.
