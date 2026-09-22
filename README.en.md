# Alma de Lujo · Growth & Business Analytics v0.2

A working analytical system with **30 typed relational tables, 11 SQL marts, six business lifecycles, six analytical processes, and seven native Codex agent roles**. All commercial records are synthetic. The 365-day case includes 1,200 orders, 46 variants and 22,844 source rows.

[Spanish documentation](README.md) · [Decision book](evidence/v0.2/DECISION-BOOK.md) · [Analytical dossier](evidence/v0.2/workspace/DOSSIER.md) · [Scope acceptance](evidence/v0.2/acceptance.json)

## Run

Python 3.11+ and modern SQLite; standard library only.

```powershell
python -m alma workspace --output build/cycle-001
python -m alma query --workspace build/cycle-001 --mart finance_monthly
python -m alma process status --workspace build/cycle-001
python scripts/verify_v2.py --output build/verification-v2
```

A new workspace creates reproducible JSON/CSV, constrained SQLite, SQL marts, lineage, scenario controls, Markdown/HTML/SVG documents, business-process histories and native-agent requests. It waits for native cognition at `WAITING_AGENT`. [Runbook](docs/RUNBOOK-v2.md).

## Actual native analysis

The delivered snapshot includes model-produced responses, registered query traces, parent runtime dispatch receipts, and separate Astra reviews. The [native cycle procedure](agents/RUN-NATIVE-CYCLE.md) explains how to run a new cycle inside Codex. Terminal-only replay validates recorded outputs without pretending to call a model. No separately billed inference API is installed.

The [decision book](evidence/v0.2/DECISION-BOOK.md) preserves observations, hypotheses, bounded proposals, explicit unknowns and reviewer objections. A REVIEW outcome completes the analytical workflow while leaving business approval unresolved. External purchases, payments, campaigns and refunds remain prohibited.

## Inspect

- [Specifications and acceptance criteria](specs/PRD.md)
- [Process states, gates and ownership](specs/PROCESS-CATALOG.md)
- [Database dictionary](specs/DATA-DICTIONARY.md) and [executable SQL](models/marts)
- [Source tables](evidence/v0.2/workspace/tables) and [SQLite snapshot](evidence/v0.2/workspace/warehouse.sqlite3)
- [Six scenario comparisons](evidence/v0.2/SCENARIO-COMPARISON.md)
- [Independent adversarial review](docs/ADVERSARIAL-REVIEW-v2.md)
- [Release evidence](docs/RELEASE.md)

Sportswear and multicolor Pilates socks are user-confirmed directions. Demand, actual products, inventory, prices, sales and profitability are not verified business facts. Public research is attributed with population/date limitations; Instagram's latest catalog was inaccessible. No real customer data is included.

Code and synthetic fixtures: [MIT](LICENSE). Public repository access is isolated to `erickinorganico`. The smaller v0.1 baseline remains under tag `v0.1.0` and `python -m alma demo`; its rule-based policies are not native model runs.
