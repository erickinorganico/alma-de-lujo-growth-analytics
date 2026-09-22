# Alma de Lujo project access

- GitHub owner for this project is `erickinorganico`.
- Use `scripts/github-personal.ps1` for GitHub CLI calls. It validates the authenticated account and isolates configuration to ignored `.local/github`.
- Git credentials and author are repository-local. Do not switch global GitHub accounts or run global `gh auth setup-git` to operate this project.
- Never publish `.local/`, `.local-archive/`, credentials or real customer information.
- Read `docs/GITHUB-ACCESS.md` for verified access and recovery. Public creation/push follow the user's current task authorization; account access alone is not authorization for unrelated external business actions.
