<!-- refreshed: 2026-09-22 -->
# Architecture

**Analysis Date:** 2026-09-22

## System Overview

```text
                 CLI and offline client entry points
     `alma/__main__.py`       `client/*.xlsx`, `client/*.html`
             |                            |
             v                            v
     v0.2 snapshot and process     v0.3 workbook and packaging
     `alma/workspace.py`           `alma/client_review.py`
     `alma/process_engine.py`      `scripts/package_client.py`
             |                            |
             v                            v
     SQLite + SQL marts             private report / offline kit
     `alma/warehouse.py`            `.local/client-runs/`, `client/`
     `models/marts/*.sql`
             |
             v
     Native Codex task bridge and independent review
     `alma/native_agents.py`, `agents/RUN-NATIVE-CYCLE.md`
             |
             v
     Hashed evidence and advisory decision packets
     `evidence/v0.2/workspace/`, `contracts/`
```

The product is a local analytical system. It has a CLI, relational snapshots, stateful analytical processes, native Codex task exchange, reports, and an offline client kit. The client HTML is a navigable static artifact, not an HTTP application. The v0.3 client aggregate workflow supplements the v0.2 synthetic warehouse; it does not import workbook aggregates as invented orders or customers (`README.md`, `specs/CLIENT-v3.md`, `alma/client_review.py`).

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI | Route `demo`, `verify`, `workspace`, `process`, and fixed `query` commands | `alma/__main__.py` |
| Workspace builder | Generate/import 30-table synthetic snapshot, validate, export tables/marts/lineage, run lifecycle demo, write manifest, start six analytical processes | `alma/workspace.py` |
| Source simulation and import | Produce deterministic synthetic business records or enforce the v0.2 interchange contract | `alma/simulation.py`, `alma/interchange.py` |
| Warehouse | Validate typed source contract, build SQLite atomically, materialize registered SQL, expose read-only named mart queries | `alma/warehouse.py`, `models/marts/*.sql` |
| Business lifecycle | Apply synthetic event gates and transitions; persist replayable instances, events, and receipts in SQLite | `alma/lifecycle.py`, `processes/business/*.json` |
| Analytical process engine | Bind immutable workspace evidence to agent requests, manage waiting/review states, journal transitions, issue decision packets | `alma/process_engine.py`, `processes/*.json` |
| Native task bridge | Build evidence-bound role requests and validate responses, source pointers, and dispatch receipts | `alma/native_agents.py`, `agents/*.json`, `contracts/native-agent-response.schema.json` |
| v0.3 workbook producer | Build the blank and synthetic example books from a single client contract | `scripts/build_client_workbook.py`, `client/contract.json` |
| v0.3 private review | Read declared workbook inputs, calculate an independent Decimal oracle, write private review artifacts | `alma/client_review.py`, `alma/client_report.py`, `scripts/review_client_workbook.py` |
| Offline atlas | Derive linked client HTML and a hashed manifest from committed v0.2 evidence and specifications | `scripts/build_client_system.py`, `client/SISTEMA_ANALITICO.html`, `client/system-manifest.json` |
| Release package | Check generated workbook content and evidence hashes before building an offline ZIP | `scripts/package_client.py`, `client/release-manifest.json` |

## Pattern Overview

**Overall:** Local-first, contract-driven analytical pipeline with immutable evidence and advisory human decision boundaries (`specs/ARCHITECTURE.md`, `AGENTS.md`).

**Key Characteristics:**
- Keep exact arithmetic and controls in Python/SQL; use native agents only for evidence-bound interpretation (`alma/warehouse.py`, `models/marts/*.sql`, `alma/native_agents.py`).
- Generate a new empty workspace for changed source, SQL, or process contracts; bind processes to the `workspace.json` hashes (`alma/workspace.py`, `alma/process_engine.py`).
- Treat business lifecycle replay and analytical task scheduling as distinct state machines (`alma/lifecycle.py`, `alma/process_engine.py`).
- Keep external business execution prohibited in analytical responses and packets (`alma/native_agents.py`, `alma/process_engine.py`).
- Keep filled client files and review output private; publish only generated blank/synthetic materials (`alma/client_review.py`, `scripts/package_client.py`).

## Layers

**Contracts and source inputs:**
- Purpose: Define exact source fields, role authority, process steps, and workbook inputs.
- Location: `alma/warehouse.py`, `contracts/`, `agents/`, `processes/`, `processes/business/`, `client/contract.json`.
- Contains: Typed table registry, JSON schemas/contracts, analytical and business process definitions, workbook schema.
- Depends on: Versioned specifications in `specs/`.
- Used by: `alma/workspace.py`, `alma/process_engine.py`, `alma/lifecycle.py`, `scripts/build_client_workbook.py`.

**Deterministic data and calculation:**
- Purpose: Validate facts, create/replay a warehouse, derive metrics and report artifacts.
- Location: `alma/simulation.py`, `alma/interchange.py`, `alma/validation.py`, `alma/warehouse.py`, `models/marts/`, `alma/workspace_report.py`.
- Contains: Synthetic generation, strict ingestion, SQL materialization, read-only mart access, reporting.
- Depends on: Source contract and `models/marts/*.sql`.
- Used by: Workspace, process evidence, verification, and offline atlas.

**Analytical control and cognition:**
- Purpose: Move each of six analytical processes from evidence validation to analyst request, independent review, and advisory packet.
- Location: `alma/process_engine.py`, `alma/native_agents.py`, `agents/RUN-NATIVE-CYCLE.md`.
- Contains: Hash-chained JSON events, state checkpoint, role request/response validation, dispatch receipt checks.
- Depends on: `workspace.json`, exported marts/research/lineage, `processes/*.json`, `agents/*.json`.
- Used by: `python -m alma process ...`, native Codex workers, decision-book tooling.

**Client delivery:**
- Purpose: Let a client work offline with aggregates and let an analyst review a private cut.
- Location: `client/`, `alma/client_review.py`, `alma/client_report.py`, `scripts/build_client_workbook.py`, `scripts/build_client_system.py`, `scripts/package_client.py`.
- Contains: Excel workbooks, static guide and atlas, independent Decimal review, verified ZIP packaging.
- Depends on: `client/contract.json`, committed v0.2 evidence, v0.3 Excel recalculation receipts.
- Used by: Client in desktop Excel, analyst review command, release verification.

## Data Flow

### Primary v0.2 Workspace Path

1. `python -m alma workspace` enters `alma/__main__.py:75`, then calls `alma/workspace.py:13`.
2. `alma/workspace.py:13` obtains a seeded synthetic snapshot from `alma/simulation.py:121` or explicit import from `alma/interchange.py:8`; it writes source/quality files and blocks failed checks.
3. `alma/warehouse.py:525` builds a temporary typed SQLite database, materializes only SQL in `models/marts/*.sql`, checks foreign keys, then atomically replaces the destination.
4. `alma/workspace.py:13` exports source CSV, marts, lineage, quality, research, experiment analysis, dossier, and business lifecycle replay. It hashes files in `workspace.json` before starting processes.
5. `alma/process_engine.py:93` verifies the manifest, checks required table coverage, and writes each analyst request under `WORKSPACE/processes/PROCESS/tasks/` with status `WAITING_AGENT`.
6. Native Codex tasks follow `agents/RUN-NATIVE-CYCLE.md`. `alma/native_agents.py:61` checks exact observation values against JSON pointers and recommendation authority; `alma/native_agents.py:102` checks the live dispatch receipt.
7. `alma/process_engine.py:219` accepts an analyst response, emits a separate reviewer request, and accepts review from a different native agent. `alma/process_engine.py:184` writes a packet and terminal state `READY_FOR_OWNER` or `REVIEW`, or blocks on material error.

### Synthetic Business Lifecycle Path

1. Definitions in `processes/business/*.json` drive `alma/lifecycle.py:30` and a six-process replay during `alma/workspace.py:13`.
2. `alma/lifecycle.py:491` validates legal transitions and state-aware gates, persists instance/event/receipt records, and preserves idempotency.
3. `alma/lifecycle.py:625` verifies hash chains; `alma/lifecycle.py:653` exports the lifecycle evidence consumed by analytical process requests.

### v0.3 Client Workbook and Offline Kit Path

1. `scripts/build_client_workbook.py:196` builds the blank and synthetic Excel books from `client/contract.json`; `scripts/build_client_system.py:179` derives the static atlas from committed v0.2 evidence.
2. A private filled workbook is read by `alma/client_review.py:76`; `alma/client_review.py:155` independently recalculates inventory, price, and 91 daily cash closes with Decimal. `alma/client_review.py:319` writes JSON/HTML/corrections and a native-review brief only under `.local/client-runs/`.
3. `scripts/verify_client_v3.py:86` compares Excel cached formula results with the independent oracle and recorded Microsoft Excel recalculation evidence in `evidence/v0.3/excel/`.
4. `scripts/package_client.py:64` checks exact generated workbook contents, hashes, blank decision register, and offline atlas evidence; it writes a ZIP only under `.local/releases/`.

**State Management:** v0.2 business lifecycles use SQLite (`alma/lifecycle.py`); analytical processes use hash-chained JSON journals and checkpoints (`alma/process_engine.py`); a v0.3 private review produces a new immutable output directory rather than shared application state (`alma/client_review.py`).

## Key Abstractions

**Workspace manifest:** `workspace.json` records source metadata, coverage, counts, file and SQLite hashes; each analytical run binds to it (`alma/workspace.py`, `alma/process_engine.py`).

**Registered mart:** A fixed name in `MARTS` maps to one SQL file and a materialized SQLite relation; arbitrary SQL is absent from the CLI (`alma/warehouse.py`, `models/marts/*.sql`).

**Process definition and checkpoint:** A definition fixes owner, required tables, marts, and analyst role; state and journal anchor a replayable run (`processes/*.json`, `alma/process_engine.py`).

**Native task request and dispatch receipt:** A request carries the role contract and evidence hash. A separate dispatch receipt records actual native model/task identity and response hash (`alma/native_agents.py`, `contracts/native-agent-response.schema.json`).

**Client workbook contract:** Sheet names, input columns, capacities, and formulas are centralized in `client/contract.json`; the workbook and private oracle both consume it (`scripts/build_client_workbook.py`, `alma/client_review.py`).

## Entry Points

**CLI:** `alma/__main__.py` is invoked by `python -m alma`; `run.ps1` wraps common Windows commands.

**Native analytical cycle:** `agents/RUN-NATIVE-CYCLE.md` is the operator procedure; `python -m alma process submit` enters `alma/__main__.py` and `alma/process_engine.py` after a real native Codex task.

**Client review:** `scripts/review_client_workbook.py` invokes `alma/client_review.py` on a private `.xlsx`.

**Build and release:** `scripts/build_client_workbook.py`, `scripts/build_client_system.py`, `scripts/verify_client_v3.py`, `scripts/package_client.py`, and `scripts/audit_release.py` produce/check static deliverables. `.github/workflows/verify.yml` runs the release gates.

## Architectural Constraints

- **Threading:** CLI processes are synchronous; no background service or worker thread is used in `alma/__main__.py`, `alma/workspace.py`, or `alma/process_engine.py`. Native Codex tasks execute outside the deterministic Python bridge (`agents/RUN-NATIVE-CYCLE.md`).
- **Global state:** Contract registries are module constants in `alma/warehouse.py`; the workbook contract is read at import in `alma/client_review.py`. Durable mutable state is stored in workspace files or lifecycle SQLite, not a Python singleton.
- **Circular imports:** No circular dependency is evident in the entry-point/import path inspected across `alma/__main__.py`, `alma/workspace.py`, `alma/process_engine.py`, and `alma/native_agents.py`.
- **Money units:** v0.2 canonical money uses integer MXN cents (`alma/warehouse.py`); the v0.3 workbook uses MXN pesos and two-decimal Decimal arithmetic (`alma/client_review.py`, `docs/CLIENT-OPERATIONS-v3.md`). Keep conversions explicit.
- **Authority:** Decision packets are advisory; no purchase, payment, refund, price-change, or publication executor is implemented (`alma/native_agents.py`, `specs/ARCHITECTURE.md`).
- **Publication:** Never package real client records or ignored `.local/` output (`scripts/package_client.py`, `.gitignore`, `AGENTS.md`).

## Anti-Patterns

### Treating deterministic output as an agent execution

**What happens:** A waiting process or generated native-review brief can be mistaken for a completed LLM run.
**Why it's wrong:** The bridge only prepares requests and validates submitted results; it does not invoke a model (`alma/native_agents.py`, `alma/client_review.py`).
**Do this instead:** Follow `agents/RUN-NATIVE-CYCLE.md`, record the real task and dispatch receipt, then submit through `alma/process_engine.py:219`.

### Mixing client aggregates into synthetic warehouse rows

**What happens:** A v0.3 workbook cut could be projected into v0.2 order/customer tables without the required source detail.
**Why it's wrong:** It would invent transactional facts and break the source contract (`specs/CLIENT-v3.md`, `alma/warehouse.py`).
**Do this instead:** Validate aggregate input separately with `alma/client_review.py` and store the report under `.local/client-runs/`.

## Error Handling

**Strategy:** Reject invalid inputs and preserve accepted evidence. `alma/warehouse.py:525` validates before atomic replacement and records a rejection where possible; `alma/workspace.py:13` writes a blocked receipt on quality failures; `alma/process_engine.py:116` verifies manifest, request, journal, and packet hashes before advancing state.

**Patterns:**
- Use a new empty output directory for changed workspace facts (`alma/workspace.py:13`).
- Preserve `UNKNOWN`/null for missing coverage and withhold unsupported recommendations (`alma/warehouse.py`, `alma/client_review.py`).
- Refuse modified requests, stale responses, wrong role, reused reviewer identity, or altered packet (`alma/native_agents.py`, `alma/process_engine.py`).

## Cross-Cutting Concerns

**Logging:** Durable JSON receipts, state/event journals, workspace manifest, and verification evidence rather than a central log service (`alma/process_engine.py`, `evidence/v0.2/`, `evidence/v0.3/`).
**Validation:** Exact source shape and business invariants in `alma/warehouse.py`; role and evidence validation in `alma/native_agents.py`; declared workbook inputs and independent arithmetic in `alma/client_review.py`.
**Authentication:** No product login exists. GitHub operations use repository-local access isolation in `scripts/github-personal.ps1`; the analytical CLI and static kit have no external identity provider (`AGENTS.md`, `docs/GITHUB-ACCESS.md`).

---

*Architecture analysis: 2026-09-22*
