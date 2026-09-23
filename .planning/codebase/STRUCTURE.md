# Codebase Structure

**Analysis Date:** 2026-09-22

## Directory Layout

```text
[project-root]/
├── alma/                    # Python package: CLI, data, warehouse, processes, reports, client oracle
├── models/                  # Versioned SQL schema, mart SQL, lifecycle query
│   ├── marts/               # One SQL file per registered materialized mart
│   └── lifecycle/           # Lifecycle instance context SQL
├── processes/               # Six analytical process definitions
│   └── business/            # Six synthetic business lifecycle definitions
├── agents/                  # Seven native role contracts and cycle procedure
├── contracts/               # Response and decision-packet JSON schemas
├── client/                  # Offline v0.3 kit, atlas, workbooks, extension data
│   └── operating-data/      # Eight separate synthetic cost/operation CSV tables
├── scripts/                 # Verification, builders, private review, release and GitHub helpers
├── specs/                   # Normative product/data/process/metric/client specifications
├── docs/                    # Runbooks, acceptance, release, architecture decisions
├── research/                # Attributed public source register
├── evidence/                # Committed synthetic output and verification receipts
│   ├── demo/                # Compact v0.1 example artifacts
│   ├── v0.2/                # Warehouse, process, native task, acceptance evidence
│   └── v0.3/                # Client example, workbook and Excel evidence
├── tests/                   # Python unittest modules
├── .github/workflows/       # CI verification workflow
├── .planning/codebase/      # GSD codebase reference documents
├── build/                   # Ignored disposable generated workspaces
├── .local/                  # Ignored private client cuts and local release ZIPs
├── .local-archive/          # Ignored local archive
├── README.md                # Spanish public entry point
├── README.en.md             # English overview
├── AGENTS.md                # Repository instructions and authority boundary
├── requirements-client.txt # Optional v0.3 workbook tooling dependencies
└── run.ps1                 # Windows CLI wrapper
```

## Directory Purposes

**`alma/`:**
- Purpose: Importable Python implementation and `python -m alma` CLI.
- Contains: v0.1 demo modules (`alma/fixtures.py`, `alma/analytics.py`, `alma/reporting.py`, `alma/storage.py`); v0.2 source/warehouse/process modules (`alma/simulation.py`, `alma/interchange.py`, `alma/warehouse.py`, `alma/workspace.py`, `alma/lifecycle.py`, `alma/process_engine.py`, `alma/native_agents.py`); v0.3 private review modules (`alma/client_review.py`, `alma/client_report.py`).
- Key files: `alma/__main__.py`, `alma/workspace.py`, `alma/warehouse.py`, `alma/process_engine.py`, `alma/client_review.py`.

**`models/`:**
- Purpose: Keep SQL transformations as inspectable versioned files rather than embedded query strings.
- Contains: `models/schema.sql`, `models/marts.sql`, eleven `models/marts/*.sql`, `models/lifecycle/instance_context.sql`.
- Key files: `models/marts/finance_monthly.sql`, `models/marts/inventory_position.sql`, `models/marts/reconciliation.sql`.

**`processes/`:**
- Purpose: Declare the six analytical workflow inputs, mart dependencies, owner, and agent role.
- Contains: One kebab-case JSON per process, e.g. `processes/finance-close.json` and `processes/weekly-growth-review.json`.
- Key files: `processes/finance-close.json`, `processes/market-to-experiment.json`.

**`processes/business/`:**
- Purpose: Declare distinct synthetic business event lifecycles, legal transitions, gates, and terminal states.
- Contains: Matching process IDs under `processes/business/*.json`.
- Key files: `processes/business/procure-to-stock.json`, `processes/business/return-to-refund.json`.

**`agents/` and `contracts/`:**
- Purpose: Define native analytical role authority and machine-readable response/packet structure.
- Contains: Seven `agents/<role>.json` contracts; `agents/RUN-NATIVE-CYCLE.md`; `contracts/native-agent-response.schema.json` and decision-packet schemas.
- Key files: `agents/evidence_reviewer.json`, `contracts/native-agent-response.schema.json`.

**`client/`:**
- Purpose: Public offline v0.3 delivery surface, separate from private filled cuts.
- Contains: `client/contract.json`, blank/example `.xlsx`, weekly guide and starter docs, static analytical atlas, synthetic cost extension, manifests, blank CSV decision register.
- Key files: `client/Alma_de_Lujo_PLANTILLA.xlsx`, `client/Alma_de_Lujo_EJEMPLO.xlsx`, `client/SISTEMA_ANALITICO.html`, `client/system-manifest.json`, `client/release-manifest.json`, `client/COSTOS_Y_OPERACION.html`.

**`scripts/`:**
- Purpose: Build deliverables and run acceptance/release checks without adding a product service.
- Contains: v0.2 verification (`scripts/verify_v2.py`, `scripts/check_scope_v2.py`); v0.3 workbook/atlas builders and verification (`scripts/build_client_workbook.py`, `scripts/build_client_system.py`, `scripts/verify_client_v3.py`); private review and package/audit helpers (`scripts/review_client_workbook.py`, `scripts/package_client.py`, `scripts/audit_release.py`); GitHub wrapper (`scripts/github-personal.ps1`).
- Key files: `scripts/verify_v2.py`, `scripts/verify_client_v3.py`, `scripts/package_client.py`.

**`specs/` and `docs/`:**
- Purpose: Store normative product contracts and operational/acceptance instructions.
- Contains: Product, architecture, metrics, data dictionary and client scope in `specs/`; runbooks, ADR, verification explanation, release and client operations in `docs/`.
- Key files: `specs/ARCHITECTURE.md`, `specs/DATA-DICTIONARY.md`, `specs/METRIC-CATALOG.md`, `specs/CLIENT-v3.md`, `docs/RUNBOOK-v2.md`, `docs/CLIENT-OPERATIONS-v3.md`.

**`evidence/`:**
- Purpose: Committed synthetic snapshots and proof of verification, separate from executable implementation.
- Contains: `evidence/v0.2/workspace/` with tables, marts, lifecycle, process requests/responses/packets and dossier; `evidence/v0.2/agents/` dispatch index; `evidence/v0.3/` Excel receipts and example review; older compact demo in `evidence/demo/`.
- Key files: `evidence/v0.2/workspace/workspace.json`, `evidence/v0.2/verification.json`, `evidence/v0.3/workbook-checks.json`.

**`tests/` and `.github/workflows/`:**
- Purpose: Assert domain logic, process integrity, client arithmetic/privacy, and CI release gates.
- Contains: `tests/test_warehouse.py`, `tests/test_process_engine.py`, `tests/test_client_review.py`, `tests/test_client_system.py`, and other `test_*.py`; `.github/workflows/verify.yml`.
- Key files: `tests/test_lifecycle.py`, `tests/test_client_review.py`, `.github/workflows/verify.yml`.

## Key File Locations

**Entry Points:**
- `alma/__main__.py`: Main `python -m alma` CLI for demo, verification, workspace, processes and mart queries.
- `run.ps1`: Windows wrapper for CLI commands.
- `scripts/review_client_workbook.py`: Optional private workbook review command.
- `scripts/package_client.py`: Generates validated offline customer ZIP under `.local/releases/`.

**Configuration and Contracts:**
- `AGENTS.md`: Repository access, cycle, data and authority rules.
- `client/contract.json`: Client workbook sheet/field/formula/capacity contract.
- `alma/warehouse.py`: v0.2 table registry, insert order, grains and mart registry.
- `processes/*.json`: Analytical process definitions.
- `processes/business/*.json`: Business lifecycle transition definitions.
- `agents/*.json`: Seven native role contracts.
- `contracts/native-agent-response.schema.json`: Response fields for native tasks.

**Core Logic:**
- `alma/workspace.py`: Workspace assembly and content-hash manifest.
- `alma/warehouse.py`: Typed SQLite creation, SQL materialization and named read-only queries.
- `alma/lifecycle.py`: Business process event replay and gate enforcement.
- `alma/process_engine.py`: Analytical process state and packet production.
- `alma/native_agents.py`: Evidence/request/dispatch validation.
- `alma/client_review.py`: Aggregate workbook input validation and independent arithmetic.

**Testing:**
- `tests/`: Python unittest modules.
- `scripts/verify_v2.py`: v0.2 scenarios and evidence generation.
- `scripts/verify_client_v3.py`: Excel cache versus independent oracle comparison.
- `scripts/check_scope_v2.py`: Published v0.2 evidence and scope acceptance.
- `scripts/audit_release.py`: Publication/privacy file audit.
- `.github/workflows/verify.yml`: CI execution order.

## Naming Conventions

**Files:**
- Use `snake_case.py` for implementation and `test_<domain>.py` for tests, e.g. `alma/process_engine.py`, `tests/test_process_engine.py`.
- Use one registered mart name per SQL file, e.g. `models/marts/cash_daily.sql`; add the name to `MARTS` in `alma/warehouse.py`.
- Use matching kebab-case process IDs across `processes/<id>.json` and `processes/business/<id>.json`, e.g. `return-to-refund`.
- Use `agents/<role>.json` for native role contracts, e.g. `agents/finance_analyst.json`.
- Use versioned evidence roots `evidence/v0.2/` and `evidence/v0.3/`; keep generated private outputs in `.local/`.

**Directories:**
- Use a new empty `build/<cycle-id>/` for each changed v0.2 workspace (`alma/workspace.py`).
- Keep one analytical process under `WORKSPACE/processes/<process-id>/`, with `tasks/<role>.request.json`, `.response.json`, `.dispatch.json`, and `.trace.json` per role (`alma/process_engine.py`, `agents/RUN-NATIVE-CYCLE.md`).
- Use new private `.local/client-runs/<cut-id>/` directories for reviewed filled workbooks (`alma/client_review.py`).

## Where to Add New Code

**New v0.2 source field or relation:**
- Define the contract, order, constraints and grain in `alma/warehouse.py`; update generation/import in `alma/simulation.py` and `alma/interchange.py`; update `specs/DATA-DICTIONARY.md`; add relevant `tests/test_warehouse.py` coverage.
- If it changes the snapshot contract, create a new workspace and regenerate dependent evidence through `alma/workspace.py` and `scripts/verify_v2.py`.

**New metric or mart:**
- Put SQL in `models/marts/<name>.sql`; register the name and grain in `alma/warehouse.py`; update process mart lists in `processes/*.json` only where needed; document grain, units and null meaning in `specs/METRIC-CATALOG.md`; test in `tests/test_warehouse.py`.

**New analytical process or native role:**
- Put definition in `processes/<id>.json` and role contract in `agents/<role>.json`; adapt `alma/process_engine.py` or `alma/native_agents.py` only if the shared lifecycle/response contract needs to change. Keep `contracts/native-agent-response.schema.json`, `specs/PROCESS-CATALOG.md`, and `specs/AGENT-SYSTEM.md` aligned; test in `tests/test_process_engine.py`.
- For a synthetic business transition, update `processes/business/<id>.json` and `alma/lifecycle.py`; test gate/replay behavior in `tests/test_lifecycle.py`.

**New client workbook behavior:**
- Update `client/contract.json` first, then `scripts/build_client_workbook.py` formulas and `alma/client_review.py` independent Decimal calculation; add case coverage in `tests/test_client_review.py` and `scripts/verify_client_v3.py`; regenerate/recalculate Excel and refresh `evidence/v0.3/` before packaging.
- Keep client-facing instructions in `client/EMPIEZA_AQUI.md` or `client/GUIA_SEMANAL.html` and operational details in `docs/CLIENT-OPERATIONS-v3.md`.

**New offline atlas or cost extension:**
- Derive atlas content through `scripts/build_client_system.py` from `evidence/v0.2/workspace/`, `models/marts/`, and `specs/`; keep its hash inventory in `client/system-manifest.json` and tests in `tests/test_client_system.py`.
- Put separate synthetic cost/operations source tables in `client/operating-data/`; generate their HTML/manifest through `scripts/build_costs_operations.py`, without altering the 30-table v0.2 count (`docs/CLIENT-SYSTEM-ACCEPTANCE.md`).

**Utilities:**
- Put reusable deterministic data/report logic in `alma/`; use `scripts/` for build, verification and packaging entry points. Do not add a frontend/server entry point; `AGENTS.md` and `specs/ARCHITECTURE.md` define a local analytical product.

## Special Directories

**`build/`:**
- Purpose: Disposable generated workspaces and CI outputs (`alma/workspace.py`, `.github/workflows/verify.yml`).
- Generated: Yes.
- Committed: No; excluded by `.gitignore`.

**`.local/` and `.local-archive/`:**
- Purpose: Private filled client records, review artifacts and local release ZIPs (`alma/client_review.py`, `scripts/package_client.py`).
- Generated: Yes.
- Committed: No; excluded by `.gitignore` and publication rules in `AGENTS.md`.

**`evidence/v0.2/` and `evidence/v0.3/`:**
- Purpose: Reviewable synthetic run outputs, native task receipts, and workbook/Excel verification evidence (`README.md`, `docs/CLIENT-SYSTEM-ACCEPTANCE.md`).
- Generated: Yes, by controlled build and verification scripts.
- Committed: Yes, as release evidence; do not overwrite a validated snapshot to represent changed inputs.

**`.planning/codebase/`:**
- Purpose: GSD reference map for future planning and execution.
- Generated: Yes, by codebase mapping.
- Committed: Determined by the orchestrator; see `.planning/codebase/ARCHITECTURE.md`.

---

*Structure analysis: 2026-09-22*
