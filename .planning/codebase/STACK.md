# Technology Stack

**Analysis Date:** 2026-09-22

## Languages

**Primary:**
- Python 3.11+ - CLI, synthetic data generation, validation, analytics, SQLite workspace and report generation in `alma/`.
- SQL (SQLite dialect) - schema, lifecycle context and 11 analytical marts in `models/schema.sql`, `models/marts/`, and `models/lifecycle/instance_context.sql`.

**Secondary:**
- PowerShell - Windows launcher, GitHub CLI wrapper and Excel desktop recalculation in `run.ps1`, `scripts/github-personal.ps1`, and `scripts/recalculate_client_excel.ps1`.
- JavaScript (Node.js CommonJS) - optional static report preview in `scripts/render_preview.cjs`; Playwright and Chromium are not part of the analytical core.
- HTML/CSS - static reports and client guides in `alma/reporting.py`, `alma/client_report.py`, and `client/`.
- JSON, CSV, and Markdown - role/process contracts, interchange, evidence, and documentation throughout `agents/`, `processes/`, `contracts/`, `evidence/`, and `docs/`.

## Runtime

**Environment:**
- Python 3.11+ with SQLite STRICT table support. CI pins Python 3.12 in `.github/workflows/verify.yml`; documented local work also uses Python 3.12.14.
- SQLite is the Python standard-library `sqlite3` runtime; no separate database server is needed.
- Windows PowerShell is used by `run.ps1` and Excel COM recalculation. GitHub Actions uses Ubuntu for CI.

**Package Manager:**
- Python pip only for optional workbook review/build dependencies listed in `requirements-client.txt`.
- Lockfile: missing. Core `alma/` has no third-party package requirement. `requirements-client.txt` pins `openpyxl==3.1.5`, `et-xmlfile==2.0.0`, and `XlsxWriter==3.2.9`.
- No `package.json` or Node lockfile is present. `scripts/render_preview.cjs` requires externally available `playwright` and Chromium when that optional preview is run.

## Frameworks

**Core:**
- Python standard library - CLI (`alma/__main__.py`), calculations, file IO, schema checks, process state, SQLite persistence, and Markdown/HTML/SVG outputs.
- SQLite - embedded typed relational storage and query execution in `alma/warehouse.py`, `alma/storage.py`, and `alma/lifecycle.py`.
- XlsxWriter and openpyxl - optional Excel kit generation, reading, and independent workbook review in `scripts/build_client_workbook.py` and `alma/client_review.py`.

**Testing:**
- `unittest` - tests in `tests/`, invoked by `scripts/verify_v2.py` and `.github/workflows/verify.yml`.
- Python standard-library checks and project-specific acceptance/evidence gates in `scripts/check_scope_v2.py`, `scripts/audit_release.py`, and `scripts/verify_client_v3.py`.

**Build/Dev:**
- `python -m alma` - workspace, demo, verification, query, and analytical process CLI, implemented in `alma/__main__.py`.
- `run.ps1` - Windows wrapper selecting `.venv`, bundled Codex Python, or `python` from PATH.
- `scripts/build_*.py` - deterministic report, system catalogue, decision book, operating-cost appendix, workbook, and package builders.
- GitHub Actions - CI verification workflow in `.github/workflows/verify.yml`.

## Key Dependencies

**Critical:**
- Python standard library - complete offline synthetic analytics core; key modules include `alma/analytics.py`, `alma/validation.py`, `alma/warehouse.py`, and `alma/reporting.py`.
- SQLite (`sqlite3`) - local workspace database; no ORM or server dependency.

**Infrastructure:**
- `openpyxl==3.1.5`, `et-xmlfile==2.0.0`, `XlsxWriter==3.2.9` - optional analyst workbook interface, not required for `python -m alma workspace`.
- Microsoft Excel desktop via COM - optional formula recalculation and recorded engine receipt through `scripts/recalculate_client_excel.ps1`; CI validates that recorded receipt, it does not run Excel.
- Playwright/Chromium - optional local preview only via `scripts/render_preview.cjs`; no declared package manifest or CI dependency.
- GitHub CLI (`gh`) - optional repository operations, isolated by `scripts/github-personal.ps1` to `.local/github`.

## Configuration

**Environment:**
- Core requires no API key, secret, database URL, or `.env` configuration.
- Runtime/output paths are command-line arguments; `run.ps1` may select `.venv`, the bundled Codex Python runtime, or PATH Python.
- GitHub authentication is handled through the project-local CLI config and repository Git helper documented in `docs/GITHUB-ACCESS.md`; credentials stay outside published files.

**Build:**
- No `pyproject.toml`, `setup.py`, `package.json`, or application build configuration is present.
- Dependency/configuration inputs are `requirements-client.txt`, `.github/workflows/verify.yml`, `.gitignore`, and `run.ps1`.
- SQL definitions are source files under `models/`; builders materialize SQLite, CSV/JSON, and report artifacts into caller-selected output folders.

## Platform Requirements

**Development:**
- Python 3.11+ and modern SQLite; Windows PowerShell for the convenience launcher and Excel COM step. The analytics core is standard-library and designed for offline use.
- Excel workbook generation/review additionally needs `requirements-client.txt`; workbook recalculation specifically needs desktop Microsoft Excel on Windows.

**Production:**
- No hosted application or production deployment target is defined. User-facing outputs are local files, SQLite workspaces, and downloadable static artifacts; native interpretation is performed in a Codex task runtime.
- GitHub hosts source and runs CI; the repository does not deploy a server or connect to a live commerce system.

---

*Stack analysis: 2026-09-22*
