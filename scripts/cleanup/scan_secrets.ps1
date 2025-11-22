<#
.SYNOPSIS
  Quick scan for common secret patterns in working tree and commit history.

.DESCRIPTION
  Script chạy một số grep/log to find likely secrets (Slack webhook, GitHub tokens,
  AWS keys) in working tree and commit history (git log -S). Không gửi dữ liệu ra ngoài.

.USAGE
  .\scripts\cleanup\scan_secrets.ps1
#>

Write-Host "Scan for common secret patterns in working tree and commit history" -ForegroundColor Cyan

$patterns = @(
    'hooks.slack.com',
    'xoxb-',
    'xoxp-',
    'ghp_[A-Za-z0-9]{36}',
    'AKIA[0-9A-Z]{16}',
    'ssh-rsa',
    '-----BEGIN PRIVATE KEY-----'
)

foreach ($p in $patterns) {
    Write-Host "\n=== Pattern: $p ===" -ForegroundColor Yellow
    Write-Host 'Working tree occurrences (git grep):' -ForegroundColor Cyan
    try { git grep -n --untracked -I --color=never "$p" } catch { Write-Host 'None' -ForegroundColor Green }

    Write-Host 'Commit history occurrences (git log -S):' -ForegroundColor Cyan
    try { git log --all -S "$p" --pretty=format:"%h %an %ad %s" -n 20 } catch { Write-Host 'None' -ForegroundColor Green }
}

Write-Host "`nScan complete. If secrets are found, do NOT paste them into chat." -ForegroundColor Green
Write-Host "Use scripts/create_replacements.ps1 and scripts/cleanup/remove_secret_full.ps1 to remove found secrets." -ForegroundColor Green
