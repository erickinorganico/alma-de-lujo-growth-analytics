# MVP release evidence — 2026-09-22

Status: **synthetic analytical MVP complete**. Public repository: [erickinorganico/alma-de-lujo-growth-analytics](https://github.com/erickinorganico/alma-de-lujo-growth-analytics).

The verified executable source milestone is commit `9c55c61` (pipeline, reports, tests and scripts). Documentation/evidence are published in subsequent commits without changing the analytical runtime. Public history started with `cdab0cb`; both commits were pushed to the personal repository before this evidence package.

## Gates and concrete evidence

| Gate | Result | Artifact |
|---|---|---|
| Unit, integration and independent adversarial regressions | 33 tests PASS; 0 failures/errors/skips | `evidence/verification.json` |
| Normal route | PASS; all declared quality checks green | `evidence/demo/quality.json`, `report.json` |
| Four controlled failures | Correct BLOCKED states; absent cost remains UNKNOWN; negative stock/missing payment/duplicate event detected | verification scenario results; `evidence/red/` missing-cost report |
| Analyst policies | 15/15 eval cases PASS; 3 packets per scenario; forged refs/approval bypass/execution blocked | `evidence/agent-evals.json`, `contracts/decision-packet.schema.json` |
| Determinism and interchange | Repeated report equal; canonical CSV and SQLite roundtrips equal input; declared artifact hashes checked | CLI integration tests; per-snapshot `receipt.json` |
| Clean install | Fresh copied source/tests + venv without pip; demo and full verify exit 0 | `evidence/clean-install.json` |
| Tested runtime | Windows, Python 3.12.14, SQLite 3.53.1; pip absent in clean venv | clean-install receipt |
| Adversarial gate | PASS for bounded synthetic scope; original and follow-up blockers fixed | `docs/ADVERSARIAL-REVIEW.md` |
| Visual document review | 6 tables, 14 headings, 3 loaded local charts; 0 scripts/errors, no horizontal overflow at 1440px | `evidence/report-preview.json`, `.png` |
| Secrets/licensing | Pattern scan of Git publication scope has no findings; original code MIT; no third-party media/data redistribution | `scripts/audit_release.py`, `evidence/release-audit.json`, LICENSE |
| Git/publication | Isolated personal credential verified; public main created and verified milestones pushed; staged diff whitespace checked | commit history; `docs/GITHUB-ACCESS.md` |

The analytical runtime needs no credentials, paid API, external package or browser. Browser preview is optional development verification using an existing Playwright installation, not a demo dependency. Network URLs in source citations are links for human review; no report asset is loaded remotely.

## Coverage and semantics

Seventeen canonical tables span market/product/purchasing/inventory/commerce/finance/customer/Growth information. Market sources are linked context; the raw business dataset is entirely synthetic. No live catalog or social account was imported. The user-confirmed sportswear/Pilates-socks direction is distinct from invented example garments, colors, costs and activity.

Financial policies remain provisional: delivery-based revenue, distinct credit/refund/return events, standard COGS, observed cash, summarized supplier/expense payment dates and no fiscal accounting. Derived unknowns remain unknown, with conservative withholding of complete inventory-classification counts when dependencies are missing. Read-only packets resolve references but do not prove semantic entailment of arbitrary freeform text.

The reproducibility guarantee covers the same declared fixture/policy and tested runtime. SQLite binary hash portability across different SQLite versions is not promised; canonical JSON/CSV and analytical outputs remain inspectable. The snapshot receipts include the locally generated SQLite file, which is deliberately ignored in Git; public canonical data is sufficient to reconstruct it.

## Explicit remaining business work

Real-data use is outside this MVP: confirm owner process, actual SKU/cost/source coverage, privacy/provenance and financial policy; add an approved adapter and reconcile real authoritative totals. Actual market demand, adoption, causal lift, ROI, production deployment, payments and tax correctness are not claimed. No frontend/backend, SaaS, CRM or ERP was built into the release.

## Reproduce

```powershell
python -m alma demo
python -m alma verify
python scripts/audit_release.py
```

Open generated report documents directly. Use separate output paths for red scenarios. `demo` exits 0 for a green snapshot, 2 for a controlled blocked snapshot and 1 for an input/build error. `verify` evaluates red outcomes as expected successful tests. See README ES/EN for fresh-environment commands and the migration/playbook documents for the next authority boundary.
