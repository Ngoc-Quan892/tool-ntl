---
name: Security incident / leaked secret
about: Report and track actions for a secret exposure or repository security incident
title: '[SECURITY] Secret exposure / history scrub — ACTION REQUIRED'
labels: security, incident
assignees: ''
---

## Tóm tắt ngắn (summary)
Vui lòng điền các thông tin dưới đây để báo cáo nhanh sự cố liên quan đến rò rỉ bí mật trong kho mã.

- **Ngày giờ phát hiện**: 
- **Người báo cáo**: 
- **Branch liên quan**: `upgrade-automation-2025` (backup: `upgrade-automation-2025-backup`)
- **Tóm tắt**: Phát hiện Slack webhook trong lịch sử; đã redact file và chạy history-rewrite. Thực hiện quét detect-secrets và tạo baseline để CI không báo false-positives.

## Các file / mục đã kiểm tra (affected files)
- `deployment/ALERT_PROCEDURES.md` — Slack webhook đã redacted and history rewritten.
- `backend/app/services/authentication.py` — API key prefix flagged (false positive).
- `scripts/rebase_sequence_editor.ps1` — hex commit id flagged (false positive).
- `backend/tests/security/test_security.py` — example passwords flagged (false positives).
- `backend/app/core/config.py` — placeholder DATABASE_URL (cleared in tree to avoid false positives).
- `.github/workflows/ci-cd.yml` — references to `${{ secrets.SECRET_KEY }}` (no plaintext, false positive).

## Hành động đã thực hiện
- Slack webhook redacted and history rewritten (backup branch `upgrade-automation-2025-backup` created and pushed).
- Per-commit detect-secrets run (partial), aggregated to `.detect_secrets_history.csv` and `.detects_summary.json`.
- `.secrets.baseline` generated and added to repo root to approve known findings and prevent CI failures.
- `backend/app/core/config.py` updated to remove default `DATABASE_URL` placeholder.

## Hành động khẩn (IMMEDIATE)
- [ ] **Rotate Slack webhook** (owner of the webhook): create a new Incoming Webhook and update CI/GH Secrets.
- [ ] **Rotate any other third-party credentials** you maintain that may have been exposed historically.
- [ ] **Confirm rotation** in this issue: who rotated, what, and timestamp.

## Verification checklist (devs / ops)
- [ ] Re-clone the repository fresh after rewrite.
- [ ] Run the quick git grep to ensure `hooks.slack.com` no longer appears in history.
- [ ] Run local detect-secrets baseline check:

```powershell
# from repo root
# ensure venv and detect-secrets installed
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install detect-secrets
& ".\.venv\Scripts\detect-secrets.exe" scan --all-files --baseline .secrets.baseline > detect-output.json
# inspect any new results
& ".\.venv\Scripts\python.exe" -c "import json; print(json.load(open('detect-output.json'))['results'])"
```

## Suggested next steps (owner/security)
- [ ] Rotate any real keys identified.
- [ ] Update CI/Secrets store (GitHub Actions secrets) with the new values.
- [ ] Once rotations are confirmed, security lead may confirm and then we can safely remove the backup branch `upgrade-automation-2025-backup`.
- [ ] Update team runbook with post-incident steps and add guidance to avoid committing secrets.

## Notes and artifacts
- Aggregated report: `.detect_secrets_history.csv`
- Per-commit outputs: `.detects/`
- Summary JSON: `.detects_summary.json`
- Backup branch: `upgrade-automation-2025-backup`

---

*Use this issue to coordinate rotations, verification, and branch cleanup.*
