# GitHub access — verified, 2026-09-22

Target account: **erickinorganico**. Access is isolated to this repository; global account configuration is not needed for project work.

## Verified configuration

- Project GitHub CLI session: `erickinorganico`, authenticated by device flow, stored in the OS keyring.
- Git's actual credential helper: retrieved a credential and authenticated to GitHub's `/user` endpoint as `erickinorganico`; no token was displayed or written in evidence.
- Local author: `erickinorganico <erickinorganico@users.noreply.github.com>`.
- Local remote: `https://github.com/erickinorganico/alma-de-lujo-growth-analytics.git` (created and initial main pushed).
- `.local/github/hosts.yml` is ignored by Git.
- Local Git helper resets inherited helpers for github.com and invokes `gh auth git-credential` with this project's isolated `GH_CONFIG_DIR`; token/host environment overrides are removed for that helper process.

## Use

```powershell
.\scripts\github-personal.ps1 api user --jq .login
.\scripts\github-personal.ps1 repo list erickinorganico
```

The wrapper requires `erickinorganico` before non-auth commands and restores environment values afterwards. Normal `git fetch/push` in this repository uses the local helper automatically. Do not use `gh auth setup-git` or a global credential switch for this project.

If this folder moves, update the absolute `GH_CONFIG_DIR` path in its local Git credential helper. If authorization expires:

```powershell
.\scripts\github-personal.ps1 auth login --hostname github.com --git-protocol https --web
```

No credentials belong in the public repository; never copy `.local` into publication artifacts.
