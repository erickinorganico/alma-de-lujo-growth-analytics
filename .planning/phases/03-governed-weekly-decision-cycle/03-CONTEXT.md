# Phase 3: Governed Weekly Decision Cycle — Context

## Decisions

The user authorized the recommended GSD path for a complete final product. These decisions come from `AGENTS.md`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, the completed Phase 3 research, and the Phase 1–2 contracts. They are locked for this phase.

- **D-01 — Parallel v1 cycle.** Build a versioned operating-cut cycle around the verified Phase 1 workspace and Phase 2 derived bundle. Keep the released v0.2 process engine and v0.3 workbook review behaviorally unchanged; never project aggregate observations into fabricated orders, customers, or synthetic transactional facts.
- **D-02 — Immutable current-cut evidence.** Before task creation, verify the Phase 1 manifest and every Phase 2 artifact. Bind the stable cut ID, manifest digest, exact report-byte SHA-256, metric-contract digest, cutoff, timezone, source hashes, coverage, quality, lineage, reconciliation and deterministic report values into one canonical current-cut document. Any changed byte or hash starts a new run and invalidates pending responses.
- **D-03 — Real native execution.** Python and SQL create exact facts, hashes, requests and validation only. They never emulate an analyst or reviewer. An accepted live cycle contains actual native Codex task responses and parent-runtime dispatch receipts with real task ID, native model, effort, timestamps and response hash. Validator fixtures prove contract behavior only and must never be described as live inference.
- **D-04 — Role routing and independence.** `merchandiser` and `finance_analyst` route to native Terra; `commerce_analyst` and `returns_analyst` route to native Luna; `growth_analyst` and `market_researcher` route to native Sol. Native Astra performs the final `evidence_reviewer` task. The reviewer task ID must differ from every accepted analyst task ID, and the reviewer request binds every accepted analysis and receipt digest.
- **D-05 — Strict references and authority.** Responses use strict RFC 6901 JSON Pointers into the frozen request evidence. Invalid escapes, missing paths, changed typed values, `null` converted to zero, stale request/hash fields, extra fields, wrong roles/models or altered dispatch receipts fail closed. Native tasks may write only their response and query trace. Every recommendation declares primary metric, guardrail, population, window, closure rule, `approval_required: true`, and `execution: PROHIBITED`.
- **D-06 — Terminal semantics.** A terminal packet visibly separates deterministic facts, unknowns, hypotheses, recommendations, reviewer challenges and provenance. `READY_FOR_OWNER` is advisory and requires every expected analyst response plus a distinct reviewer verdict on unchanged evidence. Reviewer `BLOCKED`, missing roles, failed reconciliations or changed evidence cannot become owner-ready.
- **D-07 — Owner-controlled decisions.** The decision register is an append-only private canonical JSON event ledger; CSV is a deterministic projection or validated proposed-event input, never the authority. A decision can be registered only from an intact `READY_FOR_OWNER` packet and an explicit owner choice. Owner values are allowlisted non-PII role identifiers, not names or contact data.
- **D-08 — Carry-forward, stale and closure.** `OPEN` and `IN_PROGRESS` decisions preserve stable decision ID, original source hash, packet hash, owner and due date across cuts. At the next verified cutoff, an unresolved item with `due_date < cutoff local date` becomes `STALE` unless an accepted extension event exists. Closure requires exact evidence in a verified current cut and a typed predicate that deterministically passes; a closure requiring human judgment remains `REVIEW` until an owner attestation is recorded.
- **D-09 — Privacy, compatibility and public evidence.** Filled cuts, full native responses, query traces and live decision registers stay under ignored `.local/`. Public tests and acceptance receipts use blank or clearly synthetic evidence and disclose only contract/version, task metadata, hashes and gate status. Existing v0.2/v0.3 tests and artifacts remain regression protected. No server, paid inference provider, PII collection or external business execution is introduced.

## Agent's Discretion

- Choose Python dataclass/function names and CLI subcommands while preserving the `start → dispatch/record → submit → review → packet → register/carry/close` workflow and existing repository conventions.
- Use one frozen `current-cut.json`, one manifest-bound task bundle, role-specific request files and an append-only event journal. Keep the workflow resumable and atomic through the existing canonical JSON/hash helpers.
- Bound evidence by the actual Phase 1–2 interfaces after their summaries exist. If a required source, metric, relationship or reconciliation is absent, expose it as an unknown/blocking condition rather than inventing data.
- The canonical event transition set may use `REGISTERED`, `OPEN`, `IN_PROGRESS`, `REVIEW`, `STALE`, `CLOSED`, `REJECTED`, and `CANCELLED` so long as transitions are explicit, append-only, and tested. CSV imports must reject formula prefixes and fields outside the exact contract.
- A single Astra reviewer may review the complete set of accepted analyst responses in one bound request, provided it challenges each included analysis and its task identity differs from all analyst identities.

## Deferred Ideas

- Real client-cut correctness, owner adoption and authenticated owner identity remain external gate `EXT-01`; a local owner-role attestation is visible evidence, not cryptographic authentication.
- Fiscal/tax policy and opening-bank evidence remain external gate `EXT-02`; no analytical packet claims statutory accounting.
- The Pilates-socks winner hypothesis remains `REVIEW` under `EXT-03` until eligible observed data satisfies its declared validation window.
- Storefront, CRM, ERP, web API, autonomous purchase/payment/refund/price/publishing/message actions, bank connectivity and customer PII remain out of scope.

## Phase Boundary

Phase 3 covers `FLOW-01..05`: a verified current-cut/task bundle, real native analysts, distinct native review, a governed terminal packet, and a private decision ledger that carries into later cuts. Phase 2 owns deterministic marts and metric definitions. Phase 4 owns final workbooks, portal, one-command client workflow and sanitized packaging. Phase 5 owns the milestone-wide two-week acceptance run, clean-archive/CI proof and v1.0.0 release.

## Multi-Source Coverage Audit

| Source | Item | Plan | Status |
|--------|------|------|--------|
| GOAL | Evidence-bound native analysis, independent review, owner-ready packet and next-cut continuity | 03-01, 03-02, 03-03 | COVERED |
| REQ | FLOW-01 current-cut report and evidence-hash-bound task bundle through the v1 source-pack route; Phase 4 workbook preparation must converge on the same verified Phase 1/2 boundary | 03-01 | COVERED |
| REQ | FLOW-02 schema, exact current-cut references and read-only native response boundary | 03-02 | COVERED |
| REQ | FLOW-03 distinct native review and stale/changed evidence failure | 03-02 | COVERED |
| REQ | FLOW-04 terminal facts/unknowns/hypotheses/recommendations and complete action contract | 03-02 | COVERED |
| REQ | FLOW-05 validated register, carry-forward, stale actions and evidenced closure | 03-03 | COVERED |
| RESEARCH | Verify exact Phase 1 manifest and Phase 2 report bytes before task generation | 03-01 | COVERED |
| RESEARCH | Strict RFC 6901 references, actual native receipts and unchanged workspace proof | 03-02 | COVERED |
| RESEARCH | Reviewer binds all accepted analysis; same identity, blocked verdict or changed evidence fails | 03-02 | COVERED |
| RESEARCH | Append-only canonical register, CSV projection, independent prior anchor and two-cut controls | 03-03 | COVERED |
| RESEARCH | Formula-injection, path/symlink, PII, tamper, duplicate and forged-closure negative controls | 03-01, 03-02, 03-03 | COVERED |
| CONTEXT | D-01, D-02, D-03 | 03-01, 03-02 | COVERED |
| CONTEXT | D-04, D-05, D-06 | 03-02 | COVERED |
| CONTEXT | D-07, D-08 | 03-03 | COVERED |
| CONTEXT | D-09 | 03-01, 03-02, 03-03 | COVERED |

The exact Phase 1 and Phase 2 module signatures are a dependency, not an open product decision. Plan 03-01 begins by reading their completed summaries, binding the actual build/verification APIs, and exposing a source-pack route that produces those verified artifacts before starting the cycle. Direct v1 workbook preparation stays in Phase 4; a workbook-derived cut may enter Phase 3 only after it resolves to the same canonical Phase 1 workspace and Phase 2 bundle. Plan 03-01 must not preserve a guessed research-era filename or schema when the implemented interface differs.
