# v0.2 operating runbook

Use Python 3.11+ with SQLite STRICT support. The core uses the standard library only. No server, API key, installation of a paid service or new account connection is required.

```powershell
python -m alma workspace --output build/cycle-001
python -m alma process status --workspace build/cycle-001
python -m alma query --workspace build/cycle-001 --mart finance_monthly
python -m alma query --workspace build/cycle-001 --mart inventory_position
python -m alma verify --output build/verification
```

The first command builds the rich 30-table snapshot and eleven SQL marts, exports CSV/JSON and a static dossier, and starts six analytical processes. `WAITING_AGENT` is an honest pending request. To complete cognition, follow [the native cycle procedure](../agents/RUN-NATIVE-CYCLE.md) inside Codex; no unauthenticated terminal model call is silently attempted.

## Files to inspect

| Path inside a generated workspace | Purpose |
| --- | --- |
| `DOSSIER.html`, `DOSSIER.md`, `charts/` | Exportable analytical report and graphics |
| `data.json`, `tables/*.csv`, `tables/metadata.json` | All source records and explicit coverage |
| `warehouse.sqlite3` | Typed relational source snapshot and materialized SQL marts |
| `warehouse-load.json`, `quality.json`, `lineage.json` | Loader controls, core validation and actual SQL lineage |
| `marts/*.csv`, `marts/*.json` | Complete query results at declared grains |
| `experiment-analysis.json` | Wilson intervals, missing outcomes, assignment imbalance and design assumptions |
| `research.json` | Public source dates, populations, observed values, licenses and limitations |
| `processes/PROCESS/state.json`, `events.json` | Durable analytical state and transition chain |
| `processes/PROCESS/tasks/*.request.json` | Evidence-bound native role task |
| `processes/PROCESS/tasks/*.response.json`, `*.dispatch.json` | Accepted native output and actual execution attestation |
| `processes/PROCESS/decision-packet.json` | Reviewed proposal when analyst and reviewer have completed |

## Import and scenarios

Import only explicitly synthetic data using the exact v2 columns. No implicit mapping or real business adapter is enabled.

```powershell
python -m alma workspace --input build/cycle-001/tables --output build/imported-cycle
python -m alma workspace --scenario stock_pressure --output build/stock-pressure
python -m alma workspace --scenario promotion_illusion --output build/promotion-illusion
python -m alma workspace --scenario cash_squeeze --output build/cash-squeeze
python -m alma workspace --scenario missing_cost --output build/missing-cost
python -m alma workspace --scenario broken_link --output build/broken-link
```

Existing nonempty output folders are preserved; choose a new cycle name for new inputs. `process resume` is idempotent while awaiting a response. A conflicting batch is quarantined and does not replace accepted business facts. Inspect exact failed checks instead of deleting evidence and rerunning until green.

## Interpretation and maintenance

All business records are simulated, including the randomized experiment. Public market context is attributed separately. A color with higher simulated sales is not a verified winning product. Cohorts require equal windows; discounts can raise units while reducing contribution; positive accrual profit can coexist with negative cash movement.

Amounts remain MXN cents in machine tables. Divide by 100 only when formatting money. A count based on partial coverage is not known zero. Inventory policies and management definitions are provisional and versioned; no owner identity or operating threshold is silently asserted as confirmed.

Native outputs are advisory. `READY_FOR_OWNER` means evidence is prepared for a human decision; it is not permission to buy, refund, message, publish, connect accounts or modify live operations. The project contains no external business executor.
