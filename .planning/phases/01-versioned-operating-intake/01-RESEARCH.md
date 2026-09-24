# Phase 1: Versioned Operating Intake - Research

**Researched:** 2026-09-22  
**Domain:** Versioned CSV intake, aggregate SQLite workspace, privacy and restore  
**Confidence:** HIGH for repository patterns and constraints; MEDIUM for proposed v1 schemas

## User Constraints

### Locked Decisions

- **Architecture**: Python 3.11+, SQLite, CSV/JSON/XLSX and offline HTML; no required server or paid inference provider.
- **Money**: Integer MXN cents in relational data and Decimal at input boundaries; binary floats are prohibited for financial truth.
- **Unknowns**: Missing, partial, zero, not applicable, estimated and error remain distinct.
- **Privacy**: Public Git/release artifacts contain blank or synthetic data only; private cuts stay under ignored `.local/` paths.
- **Agents**: Native Codex tasks provide interpretation; SQL/Python own exact calculations. A different agent reviews each analysis.
- **Authority**: External business execution is always `PROHIBITED`.
- **Compatibility**: Existing v0.2 and v0.3 evidence and release behavior remain regression protected.

### Project Constraints (from AGENTS.md)

- Use `scripts/github-personal.ps1` for project GitHub CLI calls; do not switch global GitHub accounts or run global `gh auth setup-git`.
- Never publish `.local/`, `.local-archive/`, credentials or real customer information.
- For any authorized analytical cycle, follow `agents/RUN-NATIVE-CYCLE.md`; deterministic scripts are not LLM agents.
- Keep exact calculations in SQL/Python; preserve unknown coverage, temporal recognition, integer MXN cents, synthetic markers and source hashes.
- Keep the product a local analytical system with CLI, relational data, processes and reports. No frontend, HTTP backend, store, CRM or ERP; no real customer data or external business execution is authorized by an analytical run.

These are copied from `.planning/PROJECT.md` and `AGENTS.md`. There is no Phase 1 CONTEXT.md. [VERIFIED: `.planning/PROJECT.md`; `AGENTS.md`]

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Initialize blank/synthetic v1 packs with exact CSV schemas, grains, keys, units and provenance. | Add a versioned registry and exact-header parser; publish blank/example pack in a new v1 directory. |
| DATA-02 | Build a private immutable workspace; malformed, duplicate or conflicting rows fail before metrics. | Validate all sources before staging SQLite; require new absent output path and publish only after all checks pass. |
| DATA-03 | Record hashes, cutoff, timezone, coverage, quality, relationships and stable PII-free cut identity. | Bind input-byte and canonical-row digests to a cut manifest, with explicit coverage and FK result. |
| DATA-04 | Use canonical SKU/event identities across operating sources, without competing ledgers. | Define PK/FK and aggregate composite keys once; keep obligations, payments, cash, receipts and expenses distinct. |
| DATA-05 | Export, restore and verify hashes and row relationships. | Reuse strict CSV/JSON serialization, SQLite checks, manifest hashing and tamper rejection. |

## Summary

Create a separate aggregate-specific v1 path. `alma/interchange.py` requires `metadata.synthetic is True`; the v2 warehouse schema has customer, order and order-item tables. Those facts make it unsuitable for importing private aggregate sales without inventing transaction detail. Preserve the v0.2/v0.3 inputs and evidence; do not edit their schemas or regenerate their hashed outputs for v1. [VERIFIED: `alma/interchange.py`; `alma/warehouse.py`; `.planning/PROJECT.md`; `.planning/REQUIREMENTS.md`]

Recommended ownership: `alma/operating_contracts.py` (schema registry), `alma/operating_interchange.py` (strict CSV import/export and pack validation), `alma/operating_workspace.py` (build/restore/verify), and `models/operating_v1.sql` (separate STRICT schema). Store public blank/synthetic samples under `client/source-packs/v1/`; store populated cuts only under `.local/operating-cuts/<cut-id>/`. These names are proposals; the isolation and privacy boundaries are fixed. [ASSUMED: names; constraints VERIFIED in `.planning/PROJECT.md` and `AGENTS.md`]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pack initialization and CSV contract | API / Backend (local CLI) | Browser / Client (workbook handoff) | Python owns deterministic schemas and validation; no hosted API is in scope. |
| Intake, canonical identity and quality checks | API / Backend (local CLI) | Database / Storage | Validate typed inputs and relationships before inserting source facts. |
| Cut snapshot, coverage, provenance and restore | Database / Storage | API / Backend (local CLI) | SQLite and manifest persist the accepted cut; CLI coordinates verification. |

Local CLI and SQLite match the project architecture. [VERIFIED: `.planning/PROJECT.md`; `alma/workspace.py`; `alma/warehouse.py`]

## Standard Stack

| Component | Version | Use |
|-----------|---------|-----|
| Python standard library | 3.11+ per project contract | CSV/JSON, validation, hashing, path operations and `sqlite3`. |
| SQLite `sqlite3` | 3.37.0+ for `STRICT` tables | Embedded relational store with typed columns, PK/FK/CHECK constraints. |
| CSV / JSON | Standard library | Source pack, manifest, export and portable receipts. |

The core uses Python `sqlite3`; `models/schema.sql` marks tables `STRICT`. SQLite's official documentation sets the minimum `STRICT` version at 3.37.0. [VERIFIED: `.planning/PROJECT.md`; `models/schema.sql`; [SQLite STRICT Tables](https://www.sqlite.org/stricttables.html)] No new external package is needed for this phase's data core. [VERIFIED: `.planning/PROJECT.md`; `alma/interchange.py`; `alma/warehouse.py`]

## Recommended V1 Source Contracts

Use one versioned registry as the sole definition of ordered headers, type, nullability, unit, grain, PK, FK, allowed enums and source provenance. Require exact header order; reject extra/missing/repeated headers, ragged rows, unknown versions, invalid dates and undeclared nulls. Existing v2 interchange checks exact header order, rejects ragged rows, and only coerces declared integer columns. [VERIFIED: `alma/interchange.py`]

Recommended shared rules: UTF-8 CSV with optional BOM on read and `newline=''`; ISO calendar dates; explicit cutoff timestamp with offset plus named timezone; MXN only; all money as integer cents; all units as integer units; rates as integer basis points. Missing numeric input is null only where the contract allows it; zero remains numeric zero. Keep free text out of schemas: use bounded `source_ref` tokens and controlled codes. [VERIFIED: `.planning/PROJECT.md`; `client/contract.json`; CSV mechanics VERIFIED in `alma/interchange.py`; exact v1 metadata and code rules are ASSUMED]

The following is a prescriptive schema proposal for planner breakdown. `?` means nullable; every row has a bounded non-personal `source_ref` unless stated. Text enums must be allowlisted in the registry. Fields are ordered as listed. [ASSUMED: new v1 schema, keys and field names]

| CSV | Grain and primary key | Ordered fields after common `source_ref` | Units / key relationships |
|-----|------------------------|--------------------------------------|---------------------------|
| `sku_catalog.csv` | One sellable variant; `sku_id` | `sku_id, product_code, variant_code, category_code, color_code, size_code, lifecycle_status, effective_date` | `sku_id` anchors all SKU facts; no customer/order IDs. |
| `sales_aggregates.csv` | One date × SKU × channel; `(sales_date, sku_id, channel_code)` | `sales_date, sku_id, channel_code, delivered_units, returned_units, restocked_units, net_revenue_cents, variable_cost_cents?, coverage_status` | SKU FK; units and MXN cents; `restocked_units <= returned_units`; window completeness declared separately. |
| `inventory_counts.csv` | One SKU at one cutoff; `(count_id)` | `count_id, sku_id, cutoff_date, on_hand_units, reserved_units, in_transit_units, non_sellable_units, source_ref` | SKU FK; integer units; do not calculate available until definitions/reconciliation validate. |
| `cost_versions.csv` | One immutable SKU cost version; `cost_version_id` | `cost_version_id, sku_id, effective_date, lifecycle_status, quantity_basis, public_price_cents, selling_fee_bps, currency, source_ref` | SKU FK; cents, quantity and basis points; never rewrite prior version. |
| `cost_components.csv` | One component in one cost version; `component_id` | `component_id, cost_version_id, component_code, classification, amount_cents?, required_flag, quality_status, included_in_component_id?, source_ref` | Cost-version FK and optional self-FK; cents; `missing` is not zero. |
| `cost_allocations.csv` | One allocation of a component; `allocation_id` | `allocation_id, component_id, sku_id, method_code, allocated_cents, remainder_cents, source_ref` | Component/SKU FKs; cents; allocated plus residual must equal source amount exactly. |
| `purchase_orders.csv` | One purchase order; `purchase_order_id` | `purchase_order_id, sku_id, ordered_units, agreed_unit_cents, order_date, promised_date?, status_code, source_ref` | SKU FK; units/cents; no second order ledger. |
| `purchase_receipts.csv` | One physical receipt event; `receipt_id` | `receipt_id, purchase_order_id, received_date, received_units, inspection_units, accepted_units, rejected_units, source_ref` | Purchase-order FK; `received = inspection + accepted + rejected`; receipt key prevents replay. |
| `obligations.csv` | One economic obligation; `obligation_id` | `obligation_id, origin_type, origin_id, due_date?, original_cents, currency, status_code, source_ref` | Origin uniquely identifies the economic source; obligation is canonical payable, not invoice/payment duplicate. |
| `obligation_payments.csv` | One observed payment applied to one obligation; `payment_id` | `payment_id, obligation_id, paid_date, amount_cents, source_ref` | Obligation FK; cents; each payment applies once. |
| `cash_events.csv` | One event per scenario; `event_id` | `event_id, scenario_id, event_date?, level, direction, amount_cents, currency, source_ref` | Cents; explicit reconciled/committed/expected/scenario/undated level; one opening record per declared scenario/cut. |
| `budgets.csv` | One approved budget per window/drop/channel; `budget_id` | `budget_id, period_start, period_end, drop_code, channel_code, approved_cents, source_ref` | Cents; period start ≤ end; keep distinct from expense/payment/obligation. |
| `expenses.csv` | One incurred economic expense; `expense_id` | `expense_id, incurred_date, category_code, amount_cents, status_code, source_ref` | Cents; origin can link to one obligation; don't count payment as another expense. |
| `quality_events.csv` | One return/inspection/quality event; `quality_event_id` | `quality_event_id, sku_id, event_date, event_type, units, reason_code, resolution_code?, source_ref` | SKU FK; units; reported return, physical receipt, inspection, refund and restock stay separate facts. |
| `sales_readiness.csv` | One SKU readiness assessment per effective date; `(sku_id, effective_date)` | `sku_id, effective_date, readiness_status, missing_info_code?, source_ref` | SKU FK; controlled readiness codes; no internal costs in sales-facing outputs. |
| `loans.csv` | One loan/custody event; `loan_id` | `loan_id, sku_id, quantity, recipient_ref, borrowed_date, due_date?, returned_date?, condition_code, status_code, source_ref` | SKU FK; `recipient_ref` is opaque/nonpersonal; units; no creator/person documents or PII. |

This list covers DATA-04's named source families while preserving distinct facts and event IDs. Exact field names and the business-provided source-key mapping are not present in the current codebase; the owner must validate them before the v1 contract is locked. [VERIFIED: `.planning/REQUIREMENTS.md`; current eight-source subset in `scripts/build_costs_operations.py`; field proposal ASSUMED]

Add pack metadata/manifest fields: `contract_version`, `input_class` (`PRIVATE` or `SYNTHETIC_EXAMPLE`), explicit `cutoff_at`, `timezone`, `currency`, source file hashes, row counts, per-domain coverage, quality status, relationships, normalized-content digest and database digest. Define stable `cut_id` from contract version + cutoff/timezone + sorted source digests; exclude `cut_id` and digest fields from their own hash preimage. Store raw source SHA-256 separately from canonical normalized-row SHA-256. [ASSUMED: exact manifest format and digest preimage]

## Import, Workspace, Export and Restore Patterns

1. Parse all declared CSVs and validate whole-pack shape, types, ranges, keys, FKs, duplicate/conflicting IDs, coverage metadata and privacy before building any database or metrics. Existing v2 parser provides exact headers/ragged-row/integer coercion precedent. [VERIFIED: `alma/interchange.py`]
2. Insert into a sibling staging SQLite file using explicit table order. Enable `PRAGMA foreign_keys=ON`; declare source tables `STRICT`, with PK/FK/NOT NULL/CHECK constraints. Run `PRAGMA foreign_key_check` plus Python/SQL business reconciliation before publish. The current warehouse already enables FK checks, builds a temp DB, and calls `os.replace` after successful insertion and controls. [VERIFIED: `alma/warehouse.py`; `models/schema.sql`]
3. Require a new, absent cut destination; never change accepted source rows. Current `alma/workspace.py` rejects a nonempty workspace output, and `alma/process_engine.py` rejects modified manifest evidence and directs changed inputs to a new workspace. [VERIFIED: `alma/workspace.py`; `alma/process_engine.py`]
4. Publish manifest and artifacts only after validation succeeds. Hash exact input bytes; hash canonical normalized rows separately; record the SQLite file hash and row/key counts. Restore verifies all hashes, contract version, row counts, FKs and relationships. A matching file hash alone is not a substitute for relationship checks. [VERIFIED: `alma/workspace.py`; `alma/warehouse.py`; restore checks are an implementation requirement from `.planning/REQUIREMENTS.md`]
5. Keep populated cuts under `.local/`; reject symlinks and paths resolving outside the private root. Public examples are synthetic by construction; do not echo cell values into diagnostics. Current workbook review restricts its output to `.local/client-runs/`; the release audit describes its PII/secret scan as bounded pattern checking rather than proof. [VERIFIED: `alma/client_review.py`; `scripts/audit_release.py`; `.planning/PROJECT.md`]

Immutability here means append a new versioned cut and verify it before use; a hash alone does not prevent a user with filesystem access from editing bytes. [VERIFIED: `alma/workspace.py`; `alma/process_engine.py`; final explanation is standard integrity reasoning]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stable row serialization | Delimiter-concatenated values or unordered JSON | One canonical JSON serializer (`sort_keys=True`, fixed separators, UTF-8, `allow_nan=False`) + SHA-256 | Existing warehouse uses canonical JSON content digest. [VERIFIED: `alma/warehouse.py`] |
| Relational checks | Python-only FK validation | SQLite PK/FK/CHECK + `PRAGMA foreign_key_check` plus business-specific checks | Existing v2 build performs both application validation and database FK check. [VERIFIED: `alma/warehouse.py`; `models/schema.sql`] |
| Money representation | Float values or rounded SQL doubles | Integer MXN cents in DB and Decimal at input boundary | Locked project constraint. [VERIFIED: `.planning/PROJECT.md`] |
| General-purpose workbook ingestion | New spreadsheet parsing framework in Phase 1 | Reuse the existing workbook contract/review boundary only as an adapter to the same v1 source contract | `client/contract.json` centralizes current workbook fields; exact business calculations live in `alma/client_review.py`. [VERIFIED: `client/contract.json`; `.planning/PROJECT.md`] |

## Common Pitfalls and Required Invariants

- **Don't import v1 into v2.** Existing import is synthetic-only and the v2 warehouse has row-level customers/orders. A v1 pack must stay aggregate and not create fake transactions. [VERIFIED: `alma/interchange.py`; `alma/warehouse.py`]
- **Don't equate blank with zero.** Nullable empty input maps to `None` only when the field is declared nullable; numeric zero remains an explicit zero. Coverage must say which sources/windows are absent or partial. [VERIFIED: `alma/interchange.py`; `client/contract.json`; `.planning/PROJECT.md`]
- **Reject all duplicate primary/composite keys.** Do not silently deduplicate rows. Exact same whole pack can resolve to the same `cut_id`; same ID with different content is a conflict and must block publication. [ASSUMED: recommended idempotency policy; requirement says duplicate/conflicting rows fail in `.planning/REQUIREMENTS.md`]
- **Keep events distinct.** Receipt events affect accepted stock; obligations are not additional to their purchase/expense origins; payment applies once; cash scenario amounts are not reconciled cash. Existing candidate source contract already distinguishes these facts. [VERIFIED: `scripts/build_costs_operations.py`; `.planning/REQUIREMENTS.md`]
- **No metrics on failed intake.** Build into staging and discard on any schema/privacy/business/FK failure. Diagnostics should identify file/row/column and issue code, not reproduce private content. [VERIFIED: `alma/warehouse.py`; staging behavior in `alma/warehouse.py`; sanitized diagnostic detail ASSUMED]
- **Hashing is not privacy.** Do not publish private-source hashes/manifests if those themselves reveal sensitive metadata; no real data or filled private pack enters Git or client package. [VERIFIED: `AGENTS.md`; `.planning/PROJECT.md`]

## Code Examples

### Exact CSV contract

`alma/interchange.py` uses UTF-8-SIG, `newline=''`, ordered exact headers, ragged-row rejection and explicit integer conversion. Extend this pattern with duplicate-header detection, size limits, date parsing and strict per-field coercion. [VERIFIED: `alma/interchange.py`; extension items ASSUMED]

```python
with path.open(encoding="utf-8-sig", newline="") as stream:
    reader = csv.DictReader(stream)
    if reader.fieldnames != list(contract.columns):
        raise ContractError("columns differ from versioned contract")
    for row_number, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ContractError(f"ragged CSV row {row_number}")
        typed_rows.append(coerce_declared_fields(row, contract))
```

### Strict SQLite and FK check

`models/schema.sql` uses SQLite `STRICT`; `alma/warehouse.py` enables foreign keys and checks them before replacing the destination. SQLite's STRICT typing feature requires version 3.37.0 or newer. [VERIFIED: `models/schema.sql`; `alma/warehouse.py`; [SQLite STRICT Tables](https://www.sqlite.org/stricttables.html)]

```sql
CREATE TABLE purchase_receipts (
  receipt_id TEXT PRIMARY KEY,
  purchase_order_id TEXT NOT NULL REFERENCES purchase_orders(purchase_order_id),
  received_date TEXT NOT NULL,
  received_units INTEGER NOT NULL CHECK(received_units >= 0),
  accepted_units INTEGER NOT NULL CHECK(accepted_units >= 0),
  source_ref TEXT NOT NULL
) STRICT;
```

Parse the calendar date in Python; a `LIKE '____-__-__'` check validates shape only. [VERIFIED: `models/schema.sql`; `alma/warehouse.py`]

## Validation Architecture

Nyquist validation is enabled because `.planning/config.json` does not set it to false. The repository uses `unittest`; the current test modules include warehouse and security/input validation. [VERIFIED: `.planning/config.json`; `tests/test_warehouse.py`; `.planning/codebase/TESTING.md`]

| Requirement | Required tests | Suggested new file |
|-------------|----------------|---------------------|
| DATA-01 | Blank/example output has exact version, ordered headers, declared grains/keys/units/provenance; bad version/header/repeated header fails. | `tests/test_operating_intake.py` |
| DATA-02 | Missing/extra columns, ragged rows, invalid dates/types/ranges, duplicate keys, same-key conflict, broken FK and PII-like columns block before DB/metrics exist. | same |
| DATA-03 | Same exact pack/cutoff yields stable identity; changing source bytes, normalized row, cutoff or timezone changes expected digest; all missing/partial/zero/estimated states remain distinct. | same |
| DATA-04 | Cross-domain SKU/event IDs resolve; duplicated receipt/payment cannot change accepted units or amount; 20 ordered/18 received/2 inspection/16 accepted reconciles. | same |
| DATA-05 | Export/restore preserves canonical row digest, FK relationships and source hashes; one-byte CSV/SQLite tamper fails verification; existing cut is never overwritten. | same |

Test with `python -m unittest discover -s tests -p 'test_operating_intake.py' -v`, then `python -m unittest discover -s tests -v` for the phase regression gate. Current tests use temporary directories/real SQLite and negative controls; follow that pattern with blank/synthetic fixtures only. [VERIFIED: `tests/test_warehouse.py`; test command pattern from repository]

## Sources

- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `AGENTS.md` — product boundary, DATA requirements, compatibility, privacy and authority.
- `alma/interchange.py`, `alma/storage.py`, `alma/warehouse.py`, `alma/workspace.py` — CSV contracts, canonical serialization, schema/load/hash and output behavior.
- `tests/test_warehouse.py` — existing warehouse contract tests.
- `client/contract.json`, `scripts/build_costs_operations.py` — current workbook and eight-source synthetic example.
- [SQLite STRICT Tables](https://www.sqlite.org/stricttables.html) — official SQLite strict type mode/version.

## Assumptions Log

| # | Claim | Risk if Wrong |
|---|-------|---------------|
| A1 | Proposed v1 CSV fields, primary/composite keys, enum/range rules and module names represent the right owner-facing contract. | Phase plan should treat exact fields/keys as a contract design task, then require owner validation before real intake. |
| A2 | Pack metadata should bind source-byte hashes and normalized-row digest separately; cut identity includes cutoff and timezone. | DATA-05 export/restore equality could mean byte-for-byte pack preservation instead. Lock digest preimage and restore semantics before implementation. |
| A3 | `coverage_status` plus nullable field states can represent missing/partial/zero/N/A/estimated without confusing source errors with observations. | An owner-approved vocabulary may require another representation; ensure tests preserve every required state. |
| A4 | Public blank/example templates belong under a new `client/source-packs/v1/` path and private builds under `.local/operating-cuts/`. | Existing v0.3 files are hashed; placing new files in old input directories could invalidate release manifests. |

**Confidence breakdown:** Repo patterns and privacy/compatibility boundaries HIGH; new source fields and cut identity semantics MEDIUM pending explicit owner contract.  
**Research date:** 2026-09-22  
**Valid until:** 2026-10-22 for repository patterns; verify configured Python/SQLite runtime before implementation.
