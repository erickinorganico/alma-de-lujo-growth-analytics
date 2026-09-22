# Project efficiency — Alma de Lujo v0.2

Reviewed 2026-09-22 using the local `laya-local` skill after adding real native-agent analysis and durable processes. Decision: **no validated bounded Laya replacement in this scope**. This conclusion is specific to observed code and role contracts; it is not an installation claim or an excuse to omit useful cognition.

| Actual surface | Repeated decision | Implementation / reason |
| --- | --- | --- |
| `alma/warehouse.py`, `models/marts/*.sql` | Cents, joins, coverage, cohorts, stock and temporal reconciliation | Exact deterministic SQL/Python; model substitution would add uncertainty |
| `alma/lifecycle.py` | Legal state transition, approval gate, replay or conflict | Deterministic event/state rules; never infer authority |
| `alma/native_agents.py` | Response schema, exact source values, hashes and external-action boundary | Deterministic validation; semantic critique is a separate native reviewer |
| `agents/*.json` | Inventory, finance, growth, commerce and market interpretation | Bounded native Codex task with multiple evidence tables and open-form counterfactual reasoning; not a compact closed-label classifier |
| Expense categories and product classes | Already explicit source fields | No free-text inference is needed; unrecognized input is rejected rather than guessed |

The native cognitive work is retained and its actual dispatches are recorded with model, task, effort, timestamps, evidence/output hashes and validation. Python's task bridge does not claim model inference. There is no API key client, separately billed provider, Jev, Beacon capture, speculative model checkpoint load or claimed cost/latency benefit.

A future repeated uncertain task such as multilingual return-reason classification could qualify after a real source and labeled baseline exist. Before use: read the runtime reference, define labels and REVIEW, compare against deterministic rules, include missing/ambiguous/injection/length cases, measure cold and warm latency plus supervision, and promote only after quality and total-work evidence. Do not route arithmetic, business authorization, causal conclusions or accounting through a compact classifier.
