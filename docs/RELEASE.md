# Alma de Lujo v0.2.0 release evidence

This release replaces the small v0.1 baseline with a substantive synthetic Growth & Business Analytics system. The public destination is [erickinorganico/alma-de-lujo-growth-analytics](https://github.com/erickinorganico/alma-de-lujo-growth-analytics). v0.1 remains historical under its tag; this document describes v0.2.

## Delivered system

- 30 typed source tables, 22,844 rows, 1,200 orders and 46 variants across 365 days.
- 11 executable SQL marts with grain, ownership, column metadata, lineage and source reconciliation.
- Six business lifecycles with 42 accepted golden events, six rejected illegal transitions, immutable receipts, replay and conflict controls.
- Six persistent analytical processes and seven role contracts. Six actual analyst outputs plus six separate Astra reviews are recorded across four native tasks and four models.
- Structured decision packets and a readable [decision book](../evidence/v0.2/DECISION-BOOK.md), plus Markdown/HTML/SVG analytical reports and CSV/SQLite deliverables.

## Verification

| Gate | Verified evidence |
| --- | --- |
| Unit and integration tests | [67 tests passed](../evidence/v0.2/verification.json); zero failures/errors |
| Scenarios | Six expected outcomes; stock pressure, discount illusion, cash pressure, unknown cost and broken linkage are distinguishable; [comparison](../evidence/v0.2/SCENARIO-COMPARISON.md) |
| Replay and import | Same seed reproduces canonical data; another seed changes data while validating; identical batches are no-ops; invalid batches preserve accepted marts; [CSV roundtrip](../evidence/v0.2/interchange.json) |
| Financial/SQL integrity | Six source-to-mart reconciliations; independent financial oracle across 13 calendar months; [controls](../evidence/v0.2/sql-controls.json) |
| Independent code review | 13 probes, six finding groups corrected and rechecked, 19 reviewed file hashes; [Astra review](ADVERSARIAL-REVIEW-v2.md) |
| Native cognition | 12 validated response/dispatch/trace bundles; analyst and reviewer identities differ per process; [run index](../evidence/v0.2/agents/task-runs.json) and [routing evidence](../evidence/v0.2/agents/model-provenance.json) |
| Written/runtime contract consistency | Five findings resolved; [resolution](../evidence/v0.2/spec-consistency-resolution.json), [v2 packet schema](../contracts/decision-packet-v2.schema.json) and [instance context](../evidence/v0.2/lifecycle-instance-context.json) |
| Scope acceptance | [32 criteria PASS, zero FAIL/BLOCKED](../evidence/v0.2/acceptance.json) |
| Clean installation | Fresh no-pip Python 3.12.14 environment, offline build, all 30 CSV and 11 JSON/CSV marts identical; all six final native packets validate in a copied snapshot; [receipt](../evidence/v0.2/clean-install.json) |
| Static visual report | 12 tables, 15 headings, three loaded local charts, zero scripts/errors/overflow; [preview](../evidence/v0.2/report-preview.json) |
| Publication audit | Synthetic SQLite binaries verified by hash and metadata; publishable text/SQL dumps checked for secret patterns; [audit](../evidence/v0.2/release-audit.json) |
| Ongoing CI | GitHub Actions reruns tests, scenarios, scope acceptance and release audit on pushes and pull requests; [workflow](../.github/workflows/verify.yml) |

The business packet status is REVIEW, independently of software acceptance PASS. Reviewers verified calculations and preserved objections about demand, attribution, cohort maturity, allocation of refunds, payment timing and experimental uncertainty. No owner approval or business impact is claimed.

## Portability and limits

The core needs only Python and SQLite. It installs no paid inference provider or production integration. A new local workspace waits at WAITING_AGENT; actual cognition runs through the documented native Codex task bridge. Offline replay verifies recorded responses and makes no new model call.

Both exact synthetic SQLite files are published to preserve snapshot hashes. A fresh SQLite build may have different binary bytes while its canonical source and all analytical exports match. Cross-version binary reproducibility is not promised.

The user's sportswear/Pilates-socks direction is distinct from simulated garments, colors, costs, prices and sales. Instagram's latest catalog was inaccessible. INEGI observations are attributed market context, not a Pilates demand estimate. Real customers, real inventory, tax accounting, paid campaigns, orders and payments are outside this release.

The audit is a bounded pattern and provenance check, not proof that arbitrary future user text is free of personal data. Source credentials, local scratch files and intermediate native drafts are excluded from Git. Personal GitHub access stays isolated to this repository.

## Reproduce

```powershell
python -m alma workspace --output build/cycle-001
python scripts/verify_v2.py --output build/verification-v2
python scripts/check_scope_v2.py --workspace evidence/v0.2/workspace --verification build/verification-v2/verification.json --output build/acceptance.json
python scripts/build_decision_book.py --workspace evidence/v0.2/workspace --output build/DECISION-BOOK.md
python scripts/audit_release.py
```

See the [runbook](RUNBOOK-v2.md), [native procedure](../agents/RUN-NATIVE-CYCLE.md) and [PRD](../specs/PRD.md).
