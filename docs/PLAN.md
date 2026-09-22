# Alma de Lujo Growth Analytics — MVP plan

Status: **implemented analytical MVP; local verification green on 2026-09-22**
Repository: `erickinorganico/alma-de-lujo-growth-analytics`
Publication: public GitHub publication is explicitly authorized and handled by the parent orchestrator

## Outcome and scope

Build a reproducible Growth and business analytics portfolio case for an early-stage Mexican D2C sportswear brand. The local workflow creates clearly labelled synthetic fixtures from seed `42`, validates them, stages them in SQLite and CSV, calculates exact-cents and inventory metrics in deterministic Python, and produces JSON evidence, decision packets, Markdown, printable HTML, and local SVG figures.

This is a system of analytical evidence and decisions, not a navigable application. V1 contains no frontend, backend service, local web server, mobile app, SaaS, CRM, ERP, or BI application. Multicolor Pilates socks are a candidate hero-product hypothesis; no real sales evidence currently establishes demand, sell-through, margin, conversion, or product-market fit.

The repository may contain and publish synthetic, public, or appropriately anonymized material. Connecting real Instagram/Meta or customer data, sending messages, buying services, handling payments, making fiscal decisions, or executing proposed business actions remains outside authorization.

## Implemented architecture

| Surface | V1 choice | Contract and boundary |
|---|---|---|
| Runtime | Python 3.11+ standard library | Runs offline on Windows without a paid API or third-party package. |
| Canonical input | Exact table dictionary from `alma.fixtures.generate(seed=42, scenario='normal')` | Fixed columns, integer quantities and MXN cents, explicit coverage, `synthetic=true`. |
| Validation | `alma.validation` | Application validation enforces structure, references, lifecycle/business invariants, and visible quality states. |
| Storage | SQLite staging plus JSON/CSV exports | SQLite preserves raw synthetic rows, including duplicate-event scenarios. It has no PK/FK enforcement in v1; analytical trust comes from Python validation. |
| Analytics | `alma.analytics.analyze(data)` | Deterministic exact-cents calculations; orders, recognized revenue, payments, refunds, returns, inventory, expenses, and cash remain distinct. |
| Decisions | `alma.decisions` | Evidence-referenced read-only packets; every action is blocked and direct execution raises `PermissionError`. |
| Reporting | `alma.reporting.write_reports(report, output_dir)` | Writes `report.md`, printable `report.html`, and three local SVG figures. No scripts, remote assets, or interaction layer. |
| CLI | `python -m alma demo` and `python -m alma verify` | Builds evidence and performs offline replay/scenario verification. |

`docs/INTERFACES.md` is the exact implementation contract. `docs/DOMAIN.md` records wider provisional business semantics and discovery questions. Wider domain concepts do not imply that an unimplemented field, SQL model, freshness monitor, or production connector exists.

## Repository and output shape

```text
alma/
  __init__.py
  __main__.py
  fixtures.py
  validation.py
  storage.py
  analytics.py
  decisions.py
  reporting.py
contracts/
docs/
tests/
run.ps1

build/demo/                 # generated, never canonical source
  .alma-generated
  alma.sqlite3
  data.json
  report.json
  quality.json
  decisions.json
  receipt.json
  csv/*.csv
  csv/metadata.json
  report.md
  report.html
  charts/monthly_finance.svg
  charts/color_stock.svg
  charts/cash_bridge.svg
```

The build accepts a new or empty directory, or an existing directory carrying the exact `.alma-generated` ownership marker. It rejects an unowned nonempty directory. Normal and controlled-failure scenarios use separate output directories.

## End-to-end contract

`python -m alma demo --output build/demo --seed 42 --scenario normal`:

1. generates or imports an exact canonical synthetic dataset;
2. validates structure, references, lifecycle rules, finance, and ledger invariants;
3. withholds analysis for unsafe broken references or delivery dates;
4. calculates the report and blocked decision packet;
5. roundtrips the canonical data through SQLite;
6. writes JSON and CSV evidence;
7. writes Markdown, HTML, and SVG reports;
8. hashes published files into `receipt.json`; and
9. exits `0` only for a `PASS` normal report, while controlled red scenarios remain inspectable and blocked.

`python -m alma verify --output build/verification` runs the standard-library suite, all declared scenarios, CSV roundtrips, and two deterministic replays, then writes `verification.json`.

## Work plan and completion checks

### Phase 1: Discovery and contracts

#### Task 1.1 — Owner discovery

Confirm operating timezone/cutoff, channels, order acceptance, settlement, returns/refunds, locations, cost basis, expense policy, decision cadence, and approval owners.

**Acceptance:** every `DISC-*` item in `docs/DOMAIN.md` has an owner-confirmed answer, explicit `UNKNOWN`, or named follow-up. Provisional demo definitions stay labelled until approved.

**Verification:** each decision maps to affected entities, metrics, fixtures, and tests.

#### Task 1.2 — Freeze the synthetic v1 contract

Maintain exact fixture columns, report shape, reporting artifacts, and CLI behavior in `docs/INTERFACES.md`.

**Acceptance:** money uses integer cents; quantities are integers; nullable fields and coverage are explicit; unknown is not zero; refund and return are independent; all data is synthetic.

**Verification:** structure, extra-column, PII-column, non-synthetic, FK, invalid-date, and coverage tests pass.

### Phase 2: Reproducible analytical foundation

#### Task 2.1 — Generate scenarios

Maintain deterministic fixtures for `normal`, `missing_cost`, `negative_stock`, `missing_payment`, and `duplicate_event`.

**Acceptance:** normal covers the full flow and validates cleanly; each red scenario targets its declared invariant without pretending to be observed business data.

**Verification:** the same seed gives equal fixtures; all normal checks pass; scenario-specific checks become `UNKNOWN` or `FAIL` as contracted.

#### Task 2.2 — Preserve local evidence

Export canonical data to JSON, CSV, and SQLite and verify roundtrips.

**Acceptance:** CSV headers are exact; ragged or oversized inputs fail; SQLite/CSV roundtrips equal canonical data; an unowned output directory is never overwritten.

**Verification:** storage and CLI tests compare complete structures and receipt SHA-256 values.

### Phase 3: Operational and financial analysis

#### Task 3.1 — Reconcile inventory

Derive on hand from signed movements, reserved from active reservations, available as on hand minus reserved, and in transit from unresolved purchase quantities.

**Acceptance:** source movements reconcile to shipped items, receipts, and restocked returns; negative stock blocks; missing variant coverage propagates null inventory values/status rather than zero.

**Verification:** the hand-computed oracle expects 14 on hand, 0 reserved, 14 available, 5 inbound, and 56,000 cents inventory value.

#### Task 3.2 — Reconcile commerce, finance, and cash

Apply the provisional demo policy without merging order, delivery, credit, refund, return, expense, supplier payment, and cash states.

**Acceptance:** all money remains integer cents; unknown cost withholds COGS/profit/margin; a refund affects cash while a restocked return reverses standard COGS; trends follow event dates.

**Verification:** the independent oracle checks literal values, including 16,000 cents net revenue, 4,000 COGS, 12,000 gross profit, and -6,000 observed net cash.

#### Task 3.3 — Preserve unknown and controlled failure states

Apply coverage to every dependent measure and reject unsafe structures before analysis.

**Acceptance:** absent funnel or variant coverage becomes `None`/`UNKNOWN`; broken FK or invalid delivery dates raise `ContractError`; missing/zero denominators never become false performance.

**Verification:** coverage-matrix and malformed-input regressions exercise affected KPI, inventory, channel, order, and trend fields.

### Phase 4: Reports and decisions

#### Task 4.1 — Generate the report package

Produce deterministic `report.md`, printable `report.html`, `monthly_finance.svg`, `color_stock.svg`, and `cash_bridge.svg`.

**Acceptance:** synthetic status, limits, source authority, unknowns, experiments, and blocked actions are visible. HTML contains no script or remote asset. SVGs preserve negative direction and represent zero without inventing a positive bar.

**Verification:** reporting/CLI tests verify returned paths, deterministic bytes, safe local references, synthetic labels, and exact receipt hashes; manual review checks readable narrative and figures.

#### Task 4.2 — Govern decisions

Build evidence-referenced packets from deterministic artifacts.

**Acceptance:** facts resolve to evidence; unknowns and hypotheses remain distinct; actions require approval and stay `BLOCKED`; `execute_action` always denies.

**Verification:** packet tampering and adversarial execution tests fail closed.

### Phase 5: Release verification

#### Task 5.1 — Verify green and red paths

Run the complete suite and repository verification with the required runtime.

**Acceptance:** normal is `PASS`; red scenarios are `BLOCKED` for expected reasons; replay and CSV roundtrip pass; `verification.json` is truthful.

```powershell
C:\Users\erick\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m alma verify --output build/verification
```

#### Task 5.2 — Review portfolio evidence

Confirm README ES/EN, methodology, limitations, licenses, secret scan, example outputs, and repository narrative distinguish synthetic/local evidence from real impact.

**Acceptance:** no real Alma PII, credentials, private Torre material, unsupported market claims, or claim of real adoption/impact is published.

**Verification:** adversarial findings are resolved; affected tests and `git diff --check` pass; the parent orchestrator handles authorized GitHub actions.

## Accountability recommendations

| Accountability | Recommended owner | Duty |
|---|---|---|
| Business definitions and action policy | Founder/brand owner | Approves glossary, commercial policies, cadence, purchases, prices, refunds, messages, and publication decisions. |
| Product and merchandising | Founder initially | Owns assortment, the Pilates-socks hypothesis, costs, and experiment decisions. |
| Inventory operations | Operations owner | Owns counts, receipts, movements, adjustments, and discrepancies. |
| Finance definitions | Founder plus qualified accountant/bookkeeper | Reviews recognition, tax, expense, cash, and formal-accounting boundaries. |
| Growth and experiments | Growth owner | Owns funnel taxonomy, population, metric, guardrail, window, and close rule. |
| Analytical contracts and release | Analytics/data owner | Owns fixtures, validation, metrics, reproducibility, receipts, reports, and evidence limits. |
| Security/privacy | Founder plus named data reviewer | Approves future real-data onboarding, minimization, retention, redaction, and disclosure. |

## Material risks

| Risk | Mitigation |
|---|---|
| Synthetic numbers are mistaken for real performance | Persistent synthetic flags in metadata, reports, receipts, narrative, and examples. |
| Missing values inflate metrics | Coverage-aware null propagation; no unknown cost/evidence is coerced to zero. |
| Order, revenue, payment, refund, return, and cash are conflated | Separate tables, dates, formulas, bridges, and tests. |
| Inventory snapshots overwrite history | Append-only movement ledger is primary; staged outputs remain evidence artifacts. |
| Presentation distorts values | Reports consume calculated data; chart tests cover negative, zero, and unknown values. |
| Files outside project ownership are overwritten | Exact output marker and unowned-directory rejection. |
| Public repository leaks private data or claims | Synthetic/public-only scope, strict schema, no PII columns, secret/license review, qualified prose. |

## Completion gate

The MVP is complete when affected tests and repository verification are green after the latest fixture, analytics, CLI, and reporting corrections; green and red scenarios are reproducible; outputs and hashes reconcile; unknowns remain unknown; reports are readable and safe; and the public repository truthfully presents a synthetic analytical case. Real connectors, real customer data, tax/accounting approval, external actions, and measured business impact remain separate future gates.
