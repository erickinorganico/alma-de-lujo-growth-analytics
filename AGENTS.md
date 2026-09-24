# Alma de Lujo project access

- GitHub owner for this project is `erickinorganico`.
- Use `scripts/github-personal.ps1` for GitHub CLI calls. It validates the authenticated account and isolates configuration to ignored `.local/github`.
- Git credentials and author are repository-local. Do not switch global GitHub accounts or run global `gh auth setup-git` to operate this project.
- Never publish `.local/`, `.local-archive/`, credentials or real customer information.
- Read `docs/GITHUB-ACCESS.md` for verified access and recovery. Public creation/push follow the user's current task authorization; account access alone is not authorization for unrelated external business actions.

## Analytical cycles

- For an authorized aggregate-v1 Alma de Lujo analysis cycle, follow `agents/RUN-NATIVE-CYCLE-v1.md`, `agents/native-cycle-v1.roles.json` and `scripts/run_weekly_cycle.py`. Each of the two release-acceptance cuts requires six distinct native analyst tasks and a later, distinct native Astra review task (14 native tasks total). Read the current workspace manifest, process requests, role contracts and response schema. The task bridge requires actual native Codex execution; deterministic scripts and `TEST_FIXTURE` receipts are not LLM agents. `agents/RUN-NATIVE-CYCLE.md` is historical v0.2 regression-only.
- Delegate bounded native analytical roles and independent review when carrying out an authorized cycle. Native Terra handles inventory/finance, Luna handles commerce/returns, Sol handles growth/market synthesis, and Astra performs independent final review. Preserve other contributors' files and do not introduce paid inference providers.
- Keep exact calculations in SQL/Python. Preserve unknown coverage, temporal recognition, integer MXN cents, synthetic markers and source hashes. Every recommendation needs a primary metric, guardrail, population, window and closure rule.
- The product is an analytical system with CLI, relational data, processes and reports. Do not replace it with a frontend, HTTP backend, store, CRM or ERP. No real customer data or external business execution is authorized by an analytical run.
