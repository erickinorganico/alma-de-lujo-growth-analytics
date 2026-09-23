# Testing Patterns

**Analysis Date:** 2026-09-22

## Test Framework

**Runner:**
- Python standard-library `unittest`; tests are in `tests/test_*.py` and use `unittest.TestCase`.
- Config: no separate pytest/unittest configuration file detected. `scripts/verify_v2.py` discovers the `tests/` directory directly.

**Assertion Library:**
- `unittest` assertions (`assertEqual`, `assertIsNone`, `assertRaises`, `subTest`) and standard Python. Workbook tests use `openpyxl`; optional client tools are pinned in `requirements-client.txt`.

**Run Commands:**
```bash
python -m unittest discover -s tests -v       # Run all unit/integration tests
python scripts/verify_v2.py --output build/verification-v2  # Tests plus core scenarios, warehouse reconciliation, and replay
python scripts/verify_client_v3.py check --directory client --engine-receipt evidence/v0.3/excel/excel-recalculation.json --output build/client-check.json  # Verify delivered workbook bytes and independent arithmetic
```

## Test File Organization

**Location:**
- Tests are separate from implementation under `tests/`; one module generally covers a subsystem or risk boundary.
- Current modules include `tests/test_analytics.py`, `tests/test_warehouse.py`, `tests/test_process_engine.py`, `tests/test_lifecycle.py`, `tests/test_client_review.py`, `tests/test_client_system.py`, `tests/test_costs_operations.py`, and `tests/test_security.py`.

**Naming:**
- Files: `test_<area>.py`; classes end in `Tests` or `Test`; methods start with `test_` and name the invariant/behavior.

**Structure:**
```text
tests/
├── test_analytics.py          # hand-calculated metrics, unknown propagation, CLI report
├── test_client_review.py      # client arithmetic, workbook parsing, hostile input, privacy
├── test_client_system.py      # manifest, lineage, role/process and offline package checks
├── test_security.py           # fail-closed data and action boundaries
└── test_warehouse.py          # schema, ingestion, marts and reconciliation
```

## Test Structure

**Suite Organization:**
```python
class ClientArithmeticTests(unittest.TestCase):
    def test_missing_cost_stays_unknown_while_zero_is_explicit(self):
        data = scenario()
        data['catalog'][0]['other_variable'] = None
        row = cr.evaluate(data)['skus'][0]
        self.assertIsNone(row['unit_variable_cost_mxn'])
        self.assertIsNone(row['target_price_mxn'])
        data['catalog'][0]['other_variable'] = 0
        self.assertEqual(cr.evaluate(data)['skus'][0]['suggested_qty'], 12)
```

**Patterns:**
- Build small explicit fixtures in test helpers (for example `scenario()` and `write_inputs()` in `tests/test_client_review.py`) and use fixed seeds in `tests/test_fixtures.py` / `tests/test_analytics.py`.
- Use `subTest` to cover input variants without losing the failing case. Use temporary directories/databases for generated outputs and patch only the narrow boundary needed to inject invalid cases.
- Include hand-computed expected values and assert exact cent/quantity results. Test invariants and failure behavior rather than mirroring implementation branches.
- Negative controls deliberately mutate one contract fact at a time: unknown cost, missing coverage, bad foreign key, stale hash, unexpected PII-like column, external URL, invalid action approval, or malformed workbook.

## Mocking

**Framework:** `unittest.mock.patch`.

**Patterns:**
```python
with tempfile.TemporaryDirectory() as tmp, patch("alma.__main__.generate", return_value=data):
    with self.assertRaises(ContractError):
        build(Path(tmp) / "blocked")
```

**What to Mock:**
- Patch only an external or nondeterministic boundary when testing fail-closed behavior; most analytics, SQLite, schema, workbook, and package tests use real local implementations and temporary artifacts.

**What NOT to Mock:**
- Do not replace the calculation under test with a mock or treat a synthetic native-agent fixture as actual model execution. Do not substitute cached Excel formula results for the independent arithmetic oracle.

## Fixtures and Factories

**Test Data:**
```python
def scenario():
    return {
        'config': dict(as_of=date(2026, 9, 20), observation_days=7, ...),
        'catalog': [dict(sku='SYN-SOCK-M', purchase_cost=20, ...)],
        'metadata': {'synthetic': True},
    }
```

**Location:**
- Reusable synthetic warehouse data: `alma/fixtures.py` and `alma/simulation.py`.
- Workbook-specific minimal fixture and workbook writer: `tests/test_client_review.py`.
- Scenario evidence and recorded verification: `evidence/` (committed receipts describe prior runs; rerun checks for current code before making a current pass claim).

## Coverage

**Requirements:** No line/branch coverage threshold or coverage tool was detected. CI gates behavior through tests and receipt-producing integration checks.

**View Coverage:**
```bash
# No configured coverage command. Run the full verification and inspect the emitted receipts.
python scripts/verify_v2.py --output build/verification-v2
```

## Test Types

**Unit Tests:**
- Domain arithmetic, validations, decision packet gates, experimentation estimators, fixture determinism, report rendering, and contracts. See `tests/test_analytics.py`, `tests/test_experimentation.py`, `tests/test_security.py`, and `tests/test_reporting.py`.

**Integration Tests:**
- SQLite warehouse creation/import/marts/reconciliation, process transitions, lifecycle hash chains/replay, CLI artifact round trips, workbook parsing, client manifest and package checks. See `tests/test_warehouse.py`, `tests/test_lifecycle.py`, `tests/test_process_engine.py`, `tests/test_cli.py`, `tests/test_client_review.py`, and `tests/test_client_system.py`.

**E2E Tests:**
- No browser or HTTP E2E framework is used. `scripts/verify_v2.py` is a local acceptance runner for fixed synthetic scenarios, SQL controls, deterministic replay, changed-seed behavior, idempotent ingestion, and rejected-batch preservation.

## Verification Layers and CI

- GitHub Actions runs on pushes and pull requests via `.github/workflows/verify.yml`, using Ubuntu and Python 3.12 with read-only repository permissions.
- The workflow installs `requirements-client.txt`, runs `scripts/verify_v2.py`, verifies published evidence/scope with `scripts/check_scope_v2.py`, audits publishable files with `scripts/audit_release.py`, checks delivered Excel bytes and independent arithmetic with `scripts/verify_client_v3.py`, and builds/checks the blank and synthetic package with `scripts/package_client.py`. Receipts are uploaded even when a prior gate fails.
- Treat independent evidence layers separately: code tests and deterministic replays do not establish native-agent runtime execution, workbook engine compatibility, owner approval, actual customer data quality, adoption, or business impact.

## Excel Verification

- `scripts/verify_client_v3.py prepare` creates synthetic adversarial workbooks without formula caches; the workbook must then be recalculated in Microsoft Excel using `scripts/recalculate_client_excel.ps1`, which records engine identity and exact-byte SHA-256 receipts under `evidence/v0.3/excel/`.
- `scripts/verify_client_v3.py check` verifies those exact delivered bytes and formula caches against the independent Python `Decimal` oracle in `alma/client_review.py`; it does not run Excel. CI on Linux validates the committed Excel receipt and workbook hashes, not Excel itself.
- `tests/test_client_review.py` exercises input parsing, formulas/independent arithmetic, source hashes, malicious ZIP members, escaped HTML, private output path constraints, and ZIP metadata/comments/hyperlinks. `docs/CLIENT-SYSTEM-ACCEPTANCE.md` records the separate Excel 16 recalculation evidence and rendered PDF review.
- Never claim compatibility with LibreOffice or another spreadsheet engine from these checks; `README.md` limits the delivered workbook claim to desktop Excel unless another suite is independently checked.

## Mocking, Privacy, and Security Gates

- Test with synthetic or blank workbooks only. Filled inputs and generated client reports stay in `.local/`, which `.gitignore` excludes; public package checks belong to `scripts/package_client.py` and `tests/test_client_system.py`.
- `tests/test_security.py` checks explicit synthetic markers, strict table columns/shapes, foreign-key/date rejection, evidence-backed packets, and permanently denied action execution.
- `tests/test_client_review.py` checks private output directory restrictions, Excel archive/member validation, formula/cache trust boundaries, output escaping, and PII-like content in metadata/comments/hyperlinks. `scripts/audit_release.py` applies bounded secret-pattern checks to public release material.
- Security tests establish known guards for tested paths; the release audit itself states it cannot prove arbitrary user-entered text contains no personal information. Run no real customer records through public CI or committed evidence.

## Async Testing

**Pattern:** No asynchronous test framework or async code path was detected; tests are synchronous.

## Error Testing

**Pattern:** Assert explicit exception types and, where contractually useful, stable diagnostic text with `assertRaises` / `assertRaisesRegex`. Also assert that invalid input leaves no published output or preserves the last accepted marts, as in `tests/test_security.py` and `tests/test_warehouse.py`.

## Gaps to Close Before Final v1.0 Claims

- CI has no configured lint, type-check, or coverage gate; correctness evidence comes from tests, deterministic acceptance scripts, and explicit release checks.
- Excel formula recalculation remains a separately recorded Microsoft Excel gate. Linux CI validates the receipt and exact workbook bytes but cannot independently launch Excel, and no other spreadsheet suite compatibility is established.
- Workbook and privacy checks use synthetic fixtures. Evidence does not establish operation on real private client data, owner adoption, business outcomes, or a broader privacy review of arbitrary free-text inputs.
- Recorded files under `evidence/` are historical receipts; current claims must cite a CI or local receipt for the exact code and workbook hashes being released.

---

*Testing analysis: 2026-09-22*
