# Run a native analytical cycle

Use inside a Codex task with this repository as working directory. Preserve the project GitHub isolation and all synthetic-data boundaries.

1. Run `python -m alma workspace --output build/cycle-NEW` or load an existing generated workspace with `python -m alma process status --workspace PATH`.
2. Read each `PATH/processes/PROCESS/tasks/ROLE.request.json`. Read `contracts/native-agent-response.schema.json` and `alma/native_agents.py` before producing responses. Do not infer that a waiting request has run.
3. Delegate independent bounded requests using native Codex models: Terra for inventory/finance investigation, Luna for commerce/returns, Sol for growth/market synthesis. Each worker owns only its response and trace file and may not delegate further. Existing user authorization governs external research; all business data remains synthetic. Never introduce a paid API provider.
4. Each analyst must inspect bound evidence, make at least one registered mart query if the local DB is present, record query/questions/row observations in a trace, challenge an alternative explanation, and write a schema-valid response. Recommendations include metrics, guardrails, windows, populations and closure rules; `execution` is always `PROHIBITED`.
5. The parent verifies with `validate_response`, records the actual native task ID/model/effort/start and completion timestamps/output hash in a dispatch receipt, and submits via `python -m alma process submit --workspace PATH --id PROCESS --response FILE --receipt FILE`. Never invent a runtime ID or label deterministic replay as live inference.
6. Submission creates a separate `evidence_reviewer.request.json`. Dispatch a different native reviewer (Astra for final adversarial review). The reviewer must compare the analyst's exact values and prose against the evidence, record at least one challenge, and block material errors. The same native task cannot review its own analyst result.
7. Validate and submit the review. Process reaches `READY_FOR_OWNER`, `REVIEW` or `BLOCKED`, with packet and hash-chained event journal. These are advisory analytical results. Business approval and execution remain absent.
8. Export an index containing all live dispatches, traces, response/packet hashes and final process states. Re-run affected checks, retain failures and corrective evidence, and publish only within the user's existing Git authorization.

Example user request for a later cycle: `Ejecuta los seis procesos analíticos de Alma de Lujo sobre el workspace indicado, incluyendo agentes nativos y revisión independiente, y entrega sus paquetes de decisión.`
