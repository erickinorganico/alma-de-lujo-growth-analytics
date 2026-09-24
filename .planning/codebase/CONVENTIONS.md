# Coding Conventions

**Analysis Date:** 2026-09-22

## Naming Patterns

**Files:**
- Python modules and tests use lowercase `snake_case`, for example `alma/client_review.py` and `tests/test_client_review.py`.
- SQL source files use lowercase names; marts live under `models/marts/` and process definitions use kebab-case JSON names under `processes/`.

**Functions:**
- Use `snake_case` for functions and methods (`evaluate`, `read_inputs`, `build_warehouse`). Public module functions typically have descriptive verbs; internal helpers use a leading underscore (`_canonical`, `_validate_shape`).
- Test methods use `test_` followed by the behavior or invariant (`test_missing_cost_stays_unknown_while_zero_is_explicit`).

**Variables:**
- Use `snake_case`; use explicit unit suffixes such as `_cents`, `_qty`, `_date`, and `_utc` for domain values.
- Prefer named dictionaries/records and explicit `None` over sentinel zero where the source value is unknown.

**Types:**
- SQL and JSON contracts use explicit field names and enumerated values; Python uses built-in annotations and `dict[str, Any]` / union annotations in newer modules.
- Schema authority is in `alma/validation.py`, `alma/warehouse.py`, `models/schema.sql`, `contracts/*.schema.json`, and workbook contracts in `alma/client_review.py`; keep validators, producers, and consumer contracts aligned.

## Code Style

**Formatting:**
- No formatter or formatter configuration was detected. Existing Python style is mixed: newer client-review code uses conventional spacing and annotations, while some older analytics and validation code is compact. Follow the clearer modern style in touched/new code and avoid unrelated formatting churn.
- Keep imports grouped as standard library, third-party packages, then local `alma` modules. Examples: `alma/client_review.py`, `alma/warehouse.py`, and `tests/test_client_review.py`.

**Linting:**
- No configured linter, static type checker, or coverage threshold was detected. CI relies on executable verification, not a style gate.
- Keep deterministic calculations in Python/SQL and avoid model-based arithmetic. The project contract in `AGENTS.md` requires exact calculations in SQL/Python.

## Import Organization

**Order:**
1. Standard library imports (`datetime`, `hashlib`, `pathlib`, `unittest`).
2. Third-party dependencies such as `openpyxl` in optional workbook tooling.
3. Project imports from `alma`.

**Path Aliases:**
- No Python import aliases or package path mapping is configured. Scripts and tests add the repository root to `sys.path` using `Path(__file__)` where direct script execution needs it.

## Error Handling

**Patterns:**
- Reject invalid input at the boundary with `ValueError`, `ContractError`, or `PermissionError`; CLI entry points translate expected failures into non-zero exit codes. See `alma/validation.py`, `alma/client_review.py`, `alma/decisions.py`, and `scripts/review_client_workbook.py`.
- Fail closed: malformed shapes, unexpected fields, missing synthetic markers, invalid relationships, stale/tampered hashes, or insufficient evidence withhold downstream analysis or actions.
- Represent a valid absence with `None`/`UNKNOWN`; distinguish that from an explicit measured zero. Do not catch broad exceptions to manufacture a successful result.

## Logging

**Framework:** Standard output/error and structured JSON receipts; no logging framework was detected.

**Patterns:**
- CLI and verification scripts print concise status/results and write machine-readable receipts to caller-provided output paths. Keep private workbook reports under `.local/client-runs/` and generated build artifacts under ignored `build/`.
- Do not write customer records, credentials, or private inputs into committed evidence, test output, or public artifacts.

## Comments

**When to Comment:**
- Explain business semantics, non-obvious fail-closed gates, and independent arithmetic oracles. Comments should clarify why a rule exists rather than repeat the expression.
- Preserve domain limitations in reports: synthetic evidence is not customer evidence; management proxies are not statutory accounting; recommendations do not execute business actions.

**Docstrings:**
- Module and public function docstrings appear in newer code and scripts (for example `alma/client_review.py` and `scripts/verify_client_v3.py`). Add concise docstrings for reusable public functions and non-obvious contract boundaries.

## Function Design

**Size:** Keep input parsing, validation, calculation, and output generation separable. Prefer the seams already exposed by `alma/client_review.py` (`read_inputs`, `evaluate`, report generation) and `alma/warehouse.py` (shape/business validation, ingestion, mart queries).

**Parameters:** Use keyword-only options for optional configuration when that improves call-site clarity. Keep source units explicit in names and types.

**Return Values:** Return JSON-serializable values and explicit statuses/diagnostics at CLI and verification boundaries. Preserve missingness as `None`; do not turn invalid or absent denominators into `0%`.

## Module Design

**Exports:** Keep domain logic in `alma/`; command wrappers and workbook build/verification utilities belong in `scripts/`.

**Barrel Files:** No barrel modules detected. `alma/__init__.py` is minimal; import from the owning module.

## Data and Evidence Invariants

- **Money:** Warehouse values use integer MXN cents and `_cents` suffixes. The client workbook accepts MXN decimal inputs, and `alma/client_review.py` independently calculates workbook outputs with decimal arithmetic and explicit rounding. Do not mix currencies or silently coerce fractional cents.
- **Unknown versus zero:** `None`/`UNKNOWN` means absent, incomplete, or not established; numeric zero means observed zero. Unknown cost/coverage must propagate to COGS, contribution, margin, stock valuation, and recommendations that depend on it. See `alma/analytics.py`, `alma/validation.py`, `alma/client_review.py`, and `tests/test_analytics.py`.
- **Synthetic data:** Every generated or accepted warehouse snapshot must explicitly mark `synthetic: true`; source fixtures and analyst-run outputs retain synthetic markers. Real customer records are outside this repo's authorized analytical fixtures. See `alma/fixtures.py`, `alma/warehouse.py`, `alma/lifecycle.py`, and `tests/test_security.py`.
- **Hashes and provenance:** Use canonical serialization and SHA-256 for source snapshots, artifacts, workbook bytes, and lifecycle event chains. Consumers must verify referenced hashes instead of trusting a written count or cached workbook value. See `alma/storage.py`, `alma/warehouse.py`, `alma/lifecycle.py`, `alma/client_review.py`, and `scripts/verify_client_v3.py`.
- **Temporal/business semantics:** Keep event dates distinct (delivery/recognition, credit note, refund settlement, physical receipt, and payment). Do not infer cash balance from cash movements or causal lift from descriptive experiments; preserve contract limitations in `docs/DOMAIN.md` and `docs/CLIENT-SYSTEM-ACCEPTANCE.md`.
- **Privacy:** Keep filled workbooks and reports private under ignored `.local/`; public packages contain only blank/synthetic workbooks. Treat public release auditing as bounded pattern checking, not proof that arbitrary user input has no personal data. See `.gitignore`, `scripts/package_client.py`, `scripts/audit_release.py`, and `tests/test_client_review.py`.

---

*Convention analysis: 2026-09-22*
