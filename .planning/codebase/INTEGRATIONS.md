# External Integrations

**Analysis Date:** 2026-09-22

## APIs & External Services

**Native analysis runtime:**
- Codex native task runtime - executes bounded analyst and independent-review tasks using evidence-bound requests prepared by `alma/native_agents.py` and `alma/process_engine.py`.
  - SDK/Client: No model SDK or network client in the repository; the parent Codex runtime dispatches tasks and returns responses/receipts through the documented procedure in `agents/RUN-NATIVE-CYCLE.md`.
  - Auth: Codex task runtime account/session outside this repository; no API key is configured by project code.
  - Boundary: Offline workspace creation leaves analytical processes at `WAITING_AGENT`. `alma/native_agents.py` validates request/response contracts but does not call a model. Native analysis is advisory and cannot execute business actions.

**Public research references:**
- INEGI MOPRADEF, AMVO, Instagram catalog, and Google Trends appear in `alma/decisions.py` and `research/source-register.json` as attributed market context, an unverified catalog, or a candidate source.
  - SDK/Client: None. References are static citations; there is no ingestion or scheduled fetch integration.
  - Auth: None for recorded references. Some source content may require separate access or terms review; Instagram's latest catalog is unverified, AMVO material was not downloaded, and Google Trends is only a candidate.
  - Limitation: Public context does not establish Alma de Lujo product demand, sales, prices, or inventory.

**Repository hosting and CI:**
- GitHub repository `erickinorganico/alma-de-lujo-growth-analytics` and GitHub Actions workflow `.github/workflows/verify.yml`.
  - SDK/Client: Git and optional GitHub CLI via `scripts/github-personal.ps1`; CI uses pinned GitHub Actions for checkout, Python setup, and artifact upload.
  - Auth: Local GitHub CLI configuration under ignored `.local/github`; CI uses GitHub Actions' built-in permissions, set to `contents: read` in `.github/workflows/verify.yml`.
  - Limitation: CI runs tests, acceptance/release audits, and workbook checks; no deployment workflow is defined. Account authentication does not itself authorize unrelated GitHub mutations.

## Data Storage

**Databases:**
- Embedded SQLite - per-run workspaces materialize the 30-table synthetic source model, marts, and lifecycle records.
  - Connection: Local file path supplied as workspace/output argument; common files are `warehouse.sqlite3`, `alma.sqlite3`, and `lifecycle/lifecycle.sqlite3`.
  - Client: Python standard-library `sqlite3` in `alma/storage.py`, `alma/warehouse.py`, and `alma/lifecycle.py`; DDL lives in `models/schema.sql` and mart SQL in `models/marts/`.
  - Limitation: No database service, hosted persistence, live adapter, or real-data import path is enabled. CSV import requires the exact schema and synthetic marker.

**File Storage:**
- Local filesystem only. Workspace interchange and results use CSV/JSON/Markdown/HTML/SVG plus SQLite; client workbook deliverables live under `client/`. Build scripts write to explicit output locations, and filled workbook reviews are restricted to `.local/client-runs` by `alma/client_review.py` and `scripts/review_client_workbook.py`.
- Excel files are generated/read locally by `scripts/build_client_workbook.py`, `scripts/package_client.py`, and `alma/client_review.py`; calculation compatibility evidence comes from the separate Windows Excel COM script `scripts/recalculate_client_excel.ps1`.

**Caching:**
- None. SQLite and generated workspace/report artifacts are durable run outputs, not a shared cache service.

## Authentication & Identity

**Auth Provider:**
- No application-user authentication. Core local analysis needs no identity or credential.
- GitHub CLI identity is scoped by `scripts/github-personal.ps1` to the project's `.local/github` and checks the expected owner; details and recovery are in `docs/GITHUB-ACCESS.md`.
- Native Codex task identity/model provenance is recorded in dispatch receipts by `scripts/record_native_run.py`; runtime identity is supplied by the Codex task environment, not obtained from a repository auth flow.

## Monitoring & Observability

**Error Tracking:**
- None (no hosted error-tracking service or SDK).

**Logs:**
- CLI output and local structured evidence: verification JSON, quality checks, lineage, process event journals, response/dispatch receipts, and SHA-256 artifact receipts. Relevant producers are `alma/__main__.py`, `alma/process_engine.py`, `alma/native_agents.py`, and `scripts/verify_v2.py`.
- GitHub Actions stores CI verification artifacts using `actions/upload-artifact` in `.github/workflows/verify.yml`.

## CI/CD & Deployment

**Hosting:**
- Source is hosted on GitHub. The offline client portal and workbooks are local/static files generated and packaged by `scripts/build_client_system.py` and `scripts/package_client.py`.
- No application hosting, server deployment, or automated release publish step is defined.

**CI Pipeline:**
- GitHub Actions on push and pull request, `.github/workflows/verify.yml`: Python 3.12 setup, optional workbook dependency install, synthetic tests/scenarios/replay, scope acceptance, release audit, client workbook verification, package privacy checks, and evidence artifact upload.

## Environment Configuration

**Required env vars:**
- None for the core or offline workbook generation/review.
- GitHub CLI wrapper temporarily manages `GH_CONFIG_DIR`, `GH_TOKEN`, `GITHUB_TOKEN`, and `GH_HOST` in process scope in `scripts/github-personal.ps1`; these are not application configuration inputs, and the wrapper restores/clears inherited values around its GitHub CLI call.

**Secrets location:**
- No application secrets are stored in project source. GitHub CLI state is local in ignored `.local/github`; `.gitignore` excludes `.local/` and `.local-archive/`.
- No `.env` contents are required or used by the core.

## Webhooks & Callbacks

**Incoming:**
- None. There is no HTTP server, API route, webhook receiver, or callback endpoint.

**Outgoing:**
- No business-system calls, webhooks, emails, payments, inventory updates, or customer messaging.
- Optional GitHub CLI commands and Codex task dispatch occur only when explicitly run through their host tools. Public research source URLs are references, not outgoing integration calls.

---

*Integration audit: 2026-09-22*
