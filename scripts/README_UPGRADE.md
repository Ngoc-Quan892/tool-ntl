# Automated Upgrade Scripts

This folder contains automation to bump dependencies for backend and frontend, run tests, and create a PR automatically via GitHub Actions.

Files added:

- `scripts/ci/upgrade_deps.sh` - CI script executed by `.github/workflows/auto-upgrade.yml` (runs on `ubuntu-latest`).
- `scripts/upgrade-local.ps1` - Helper script for Windows developers to run the same update locally.

How it works (CI):
1. Workflow `auto-upgrade.yml` runs weekly or on demand.
2. It checks out the code, runs `scripts/ci/upgrade_deps.sh` which updates Python and Node dependencies.
3. Workflow runs tests (backend + frontend).
4. If tests pass, the `create-pull-request` action will open a PR with the changes.

Local usage:

```powershell
# From repository root (Windows PowerShell)
.
cd scripts
.
./upgrade-local.ps1
```

Notes & Caveats:
- The automatic upgrade uses naive package bumping. Manual review of the PR is required.
- Some packages may require code changes after major-version bumps.
- Ensure you run tests locally before pushing the branch.
