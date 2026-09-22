# Native agent orchestration v0.2

The implementation and analytical execution were delegated within the user's authorization. All inference used native Codex models. No separately billed model provider or automatic mid-task model switching was introduced.

## Build assignments

| Native task | Routed model / effort | Bounded responsibility |
| --- | --- | --- |
| sol_scope_v2 | gpt-5.6-sol / high | PRD, scope, business lifecycle implementation and acceptance runner |
| terra_warehouse_v2 | gpt-5.6-terra / high | Constrained SQLite, eleven SQL marts, lineage, independent clean installation |
| luna_simulation_v2 | gpt-5.6-luna / high | Seeded annual scenarios and fixture verification; final documentary consistency review |
| astra_v2_review | gpt-6-astra / high | Independent financial, SQL and bridge integrity probes; substantive native reviews |
| Parent | Native Codex | Integration, request/response engine, import/report tools, runtime attestations and release verification |

Contributors owned separate files and preserved concurrent edits. Concrete failures led to targeted rework: shipment chronology, unknown-cost propagation, month/cohort denominators, immutable request binding, state/receipt/packet tampering, and prose contracts. The final review records what was actually rechecked.

## Actual analytical execution

| Native task | Analytical roles executed | Reviewer |
| --- | --- | --- |
| terra_warehouse_v2 | Finance analyst and merchandiser | astra_v2_review |
| luna_simulation_v2 | Commerce and returns analysts | astra_v2_review |
| sol_scope_v2 | Growth analyst and market researcher | astra_v2_review |
| astra_v2_review | Six independent evidence reviews | Parent validates schema, hashes, role separation and final state |

There are **seven role contracts, twelve accepted role outputs, four native task identities, and four routed models**. Reusing the review task does not imply six distinct reviewers. Independence means each reviewer task differs from the analyst task for that process.

[Accepted run index](../evidence/v0.2/agents/task-runs.json) contains actual model, effort, task ID, request hash, response digest, dispatch times, retry history, parent validation and trace paths. [Orchestration windows](../evidence/v0.2/orchestration.json) record the bounded parent dispatch windows. [Routing metadata](../evidence/v0.2/agents/model-provenance.json) verifies models from native session metadata; a generic model self-description in an initial Sol trace was corrected using that source.

The receipt is a parent-runtime attestation, not a provider-signed certificate. Exact observations validate mechanically; freeform inferences require semantic review. Queries, calculations, alternative explanations, unknowns and reviewer challenges remain inspectable. Intermediate drafts are ignored in Git; accepted outputs are immutable within their process history.

The six analytical workflows completed in REVIEW. This is a substantive result: numeric calculations reconciled while reviewers challenged uncalibrated reorder thresholds, causal assumptions, immature cohorts, an invalid per-line refund allocation, and monetary experiment uncertainty. External execution remains PROHIBITED.

No token, latency, cost or supervision savings were measured. The [Laya assessment](../PROJECT-EFFICIENCY.md) found no validated bounded classification step worth substituting into this deterministic calculation and open-ended analysis workflow.
