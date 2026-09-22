# ADR 001 — Offline deterministic analytical pipeline

Status: accepted for the synthetic MVP, 2026-09-22.

Python 3.11+ standard library, SQLite raw staging, Markdown/HTML report documents and generated SVG visualizations are the chosen analytical format. No pip packages, Node runtime, database service, model weights, credentials or network are required to generate the demo. The available bundled Python 3.12.14 is used on this machine because the global pyenv shim has no version configured. No global Python configuration was changed.

All financial truth is integer MXN cents calculated in Python. SQLite persists the input, including deliberately invalid events in red scenarios, and roundtrips it in read-only mode before publication. It is raw staging, not a database write API or a constrained ERP. `validation.py` enforces relationships and invariants explicitly, with references and results preserved. Introducing dbt/DuckDB would add installation and operational scope without measurable value for this dataset; revisit when real volume or SQL transformations warrant it.

The report is a deterministic materialized analytical document. Python calculates all values before exporting Markdown, HTML and static SVG files. There is no frontend, backend, server, navigable application or external action executor. HTML may be opened as a file or printed; it is a report, not a user interface. External approval is a human workflow outside this repository, not a boolean that enables writes.

The analysis policies are deterministic read-only agents. They expose structured facts, source references, unknowns, hypotheses and proposals and have local evaluations. They do not call an LLM, imitate autonomous reasoning or claim generated synthetic observations as actual business impact.

## Deliberate financial simplifications

Revenue is recognized at delivery, customer credit notes reduce revenue on their event date, and settled refunds affect cash separately. Gross COGS uses standard cost locked on each order item; returned restock reverses that cost. Damaged/non-restocked goods keep their COGS. Variant standard cost values ending physical stock. Cost changes, weighted-average/FIFO, taxes, settlement fees, invoice issuance and foreign currency require new explicit contracts before real use.

Cash is observed net movement within the fixture window, not bank balance, cash runway or cash profit. Purchase-order and expense paid amounts are assumed paid on their row date; partial payment histories and beginning cash are absent. Opening inventory has no invented cash outflow. Shipped inventory that is not delivered is not yet revenue/COGS: valuation of goods in delivery is an identified accounting bridge, not a missing sale.

Funnel event totals have separate source coverage; they are descriptive exposure ratios, not individual-level attributed conversion or causal estimates. Cohort repeat uses first delivered order, a fixed 30-day window and eligible customers who completed that window. Reorder <10 units and slow >=30 days/no shipment are demonstration thresholds, not endorsed purchase rules.

## Future boundary

The CSV interchange is intentionally synthetic-only and rejects extra columns. A production adapter must change provenance policy, implement consent/minimization, invoices/tax treatment, payment dates, cost policy, completeness and idempotency under a separately approved design. Renaming a real export as synthetic is not a supported migration.
