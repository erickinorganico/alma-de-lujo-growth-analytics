# Alma de Lujo · Growth & Business Analytics

A reproducible analytical MVP for an early-stage sportswear brand, using **100% synthetic business data**. It connects market research, merchandise, purchasing, inventory, commerce, customers, management finance and Growth experiments. Multicolor Pilates socks are an owner-provided hero-product hypothesis, not measured demand.

[Español](README.md) · [Example report](evidence/demo/report.md) · [Portfolio case](docs/PORTFOLIO-CASE.md) · [Release evidence](docs/RELEASE.md)

## Run offline

Python 3.11+ standard library only. No package install, credentials, network, Node, Docker, paid API or external account is required.

```powershell
python -m alma demo
python -m alma verify
```

Windows Codex users can also run `./run.ps1` and `./run.ps1 -Command verify`. The launcher selects a project virtual environment, Codex bundled Python, then PATH. It changes no global runtime configuration.

Optional clean environment:

```powershell
python -m venv --without-pip .venv
.\.venv\Scripts\python.exe -m alma demo
.\.venv\Scripts\python.exe -m alma verify
```

If PATH resolves to an unconfigured Python shim, use your actual Python 3.11+ executable or the launcher. Open `build/demo/report.md` or `report.html` as files. These are analytical documents with tables and static SVG figures; this release has no frontend, backend, local server or navigable application.

## Artifacts

`build/demo` contains canonical JSON/CSV, SQLite raw staging, an analytical JSON view, Markdown/HTML reports, three SVG figures, quality checks, three read-only analyst packets and SHA-256 receipts. Fixed snapshot date 2026-09-21, seed 42. Seventeen tables include 8 synthetic orders, independent returns/refunds, reservations, partial purchasing receipts, inventory movements, expenses, customer cohorts and missing DM traffic.

The simulated case yields MXN 3,916 net revenue, MXN 348 operating proxy and MXN -2,082 observed cash movement. This demonstrates the timing separation of purchase, delivery, revenue and cash; it is **not actual Alma performance**. An inspectable release snapshot is in `evidence/demo`; the SQLite database is generated locally.

## Controlled failures and verification

```powershell
python -m alma demo --scenario missing_cost --output build/missing-cost
python -m alma demo --scenario negative_stock --output build/negative-stock
python -m alma demo --scenario missing_payment --output build/missing-payment
python -m alma demo --scenario duplicate_event --output build/duplicate-event
```

Normal exit is 0. Expected blocked scenarios exit 2 and preserve explicit failure evidence. Invalid structure/references withhold unsafe reports and exit 1. Use separate directories to preserve prior snapshots. Unknown data is never inferred as zero.

Verification runs unit/integration/adversarial tests, all five scenarios, CSV/SQLite roundtrips, deterministic replay and 15 analyst-policy evaluations. Results are written to `build/verification/verification.json` and `agent-evals.json`. See [RELEASE.md](docs/RELEASE.md) for the actual final test results, clean-install proof and publication evidence.

## Method and limits

Revenue is recognized on delivery; credits reduce revenue; settled refunds reduce cash; physical restock reverses historical standard COGS. Inventory derives from signed movements and separate reservations; prototype lifecycle is excluded from replenishment proposals. Net sell-through subtracts restocked units. Costs and thresholds are provisional policies pending owner discovery.

Cash is observed movement, not bank balance or runway. Expense/supplier cash dates use their summarized row date. Thirty-day cohorts use eligible mature customers; channel ratios are descriptive rather than individual attribution or causal lift. Missing DM denominators remain unknown.

Read-only deterministic inventory, finance and Growth policies emit versioned packets with resolvable evidence, unknowns, hypotheses and human approval requirements. There is no LLM caller or external execution tool; every execution attempt raises `PermissionError`. Local evals test these policies, not semantic truth of arbitrary imported prose. Laya was assessed as not applicable because the runtime contains exact deterministic decisions rather than repeated uncertain classification.

The synthetic CSV interchange is ready for adapter development, not approved real-data use. Actual catalog, costs, stock ownership, channel events, privacy/provenance, payment histories and reconciliation need owner-approved discovery. Tax, invoicing, FIFO, formal accounting and production account integrations are outside this MVP. No actual customers, messages, purchases, employer IP or private datasets are included.

## Documentation and contribution

[Domain](docs/DOMAIN.md), [contracts](docs/INTERFACES.md), [ADR](docs/ADR-001-local-first-architecture.md), [market brief](docs/MARKET-RESEARCH.md), [operating playbook](docs/PLAYBOOK.md), [migration](docs/DATA-MIGRATION.md), [adversarial review](docs/ADVERSARIAL-REVIEW.md), [orchestration](docs/ORCHESTRATION.md), [Laya assessment](PROJECT-EFFICIENCY.md).

Erick directed the project and supplied the business context; native Codex Sol/Luna/Terra/Astra agents assisted implementation and review, with parent integration and verification. This demonstrates delivery and analytical methods, not business adoption, revenue improvement or autonomous operations. Original code is MIT-licensed. Third-party photos/reports are not redistributed. [Public repository](https://github.com/erickinorganico/alma-de-lujo-growth-analytics).
