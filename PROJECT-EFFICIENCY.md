# Project efficiency — Alma de Lujo

Decision: **not applicable** for Laya inference in v0.1. Reviewed 2026-09-22 after implementation, using the local `laya-local` skill. This is a code-scoped opportunity report, not a runtime installation claim.

| Observed surface | Input/output | Observed frequency | Decision and fallback |
|---|---|---|---|
| `alma/analytics.py` inventory status | exact stock/cost/age -> fixed threshold status | once per SKU per build | deterministic arithmetic; no model |
| `alma/validation.py` | typed records -> invariant results | every build/test | deterministic rules; unknown remains unknown |
| `alma/decisions.py` | validated report -> versioned proposal | once per build | deterministic baseline; no text classifier |
| `alma/storage.py` CSV columns | explicit schema -> typed values | optional local interchange | exact parse/reject; no inferred categories |

No model callers, open-text classification, ranking judgments, or repeated LLM decisions exist in the runtime. Therefore no compact uncertain closed-option judgment is being replaced. No checkpoint was loaded, no shadow evaluation was warranted, no candidate was found validated and left unused, and no token/cost/latency benefit is claimed. Existing local Laya installation history is context only. Jev, paid inference and Beacon capture are absent.

Refresh trigger: add real repeated text categorization (e.g. expense description -> category). Before any inference define labeled Spanish/multilingual baseline, positives, negatives, missing/ambiguous inputs, prompt injection, boundary lengths and REVIEW. Promotion requires zero critical policy violations, quality at least baseline, lower total measured work including cold/warm latency/retries/supervision, deterministic fallback and versioned regression fixtures. Do not use Laya for cents, joins, pricing, buying, inventory posting or causality.

Native Sol, Luna, Terra and Astra dispatch is orchestration by the parent Codex task, not Laya routing. See `docs/ORCHESTRATION.md` for actual work and evidence.
