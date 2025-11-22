# Cleanup secret workflow

This folder contains helper scripts to detect and remove secrets accidentally committed to the repository.

Files:
- `scan_secrets.ps1` — quick scan for common secret patterns in working tree and commit history.
- `create_replacements.ps1` — interactively create `replacements.txt` (local) containing `secret==>replacement` mapping for `git-filter-repo`.
- `remove_secret_full.ps1` — full automated workflow: backup repo, create mirror, run `git filter-repo --replace-text`, verify, and force-push to origin (with confirmation).

Security notes:

- DO NOT paste secrets into chat. `create_replacements.ps1` stores the secret locally in `replacements.txt` on your machine only.
- After removing secrets from history you MUST rotate the leaked secret (e.g. delete the old Slack webhook and create a new one).
- Force pushing rewrites history: notify collaborators and ask them to re-clone or reset their local branches.

Usage (recommended sequence):

1. Scan for secrets:
   ```powershell
   .\scripts\cleanup\scan_secrets.ps1
   ```
2. Create replacements file (paste the secret locally when prompted):
   ```powershell
   .\scripts\cleanup\create_replacements.ps1
   ```
3. Run the removal workflow (this will require `git-filter-repo`):
   ```powershell
   .\scripts\cleanup\remove_secret_full.ps1 -ReplacementsPath "C:\path\to\replacements.txt"
   ```

If `git-filter-repo` is not installed:
```powershell
pip install git-filter-repo
```

If you prefer not to rewrite history or you do not have admin rights to force-push, fork the repo and push there; then open a PR.
