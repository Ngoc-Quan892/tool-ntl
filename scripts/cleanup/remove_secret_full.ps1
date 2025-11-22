<#
.SYNOPSIS
  Rewrite history to remove/replace secrets using git-filter-repo, then force-push.

.DESCRIPTION
  Script thực hiện các bước an toàn: backup repo, tạo mirror, chạy git-filter-repo
  với file replacements (tạo bởi create_replacements.ps1), kiểm tra, sau đó hỏi
  xác nhận và force-push lên remote.

.USAGE
  Chạy từ thư mục repo:
    .\scripts\cleanup\remove_secret_full.ps1 -ReplacementsPath "C:\path\replacements.txt"

  Nếu không truyền -ReplacementsPath, script sẽ tìm `replacements.txt` trong thư mục gốc.
#>

param(
  [string]$ReplacementsPath = "$(Get-Location)\replacements.txt",
  [string]$MirrorDir = "$(Get-Location)\tool-ntl-mirror.git",
  [switch]$DryRun,
  [switch]$AutoConfirm
)

function Write-ErrExit($m) { Write-Host $m -ForegroundColor Red; exit 1 }

Write-Host "Starting secret-removal workflow (git-filter-repo)" -ForegroundColor Cyan

if (-not (Test-Path $ReplacementsPath)) {
    Write-Host "Không tìm thấy replacements file tại: $ReplacementsPath" -ForegroundColor Yellow
    Write-Host "Hãy tạo bằng scripts\cleanup\create_replacements.ps1 trước." -ForegroundColor Yellow
    exit 1
}

Write-Host "Creating a full filesystem backup (Tool NTL.backup)" -ForegroundColor Cyan
$root = (Get-Location).Path
$backup = Join-Path (Split-Path $root -Parent) "Tool NTL.backup"
if (Test-Path $backup) { Write-Host "Backup folder exists: $backup" -ForegroundColor Yellow } else {
    robocopy $root $backup /MIR | Out-Null
    Write-Host "Backup created at: $backup" -ForegroundColor Green
}

Write-Host "Checking for git-filter-repo..." -ForegroundColor Cyan
$gf_cmd = $null
try {
  & git-filter-repo --version > $null 2>&1
  if ($LASTEXITCODE -eq 0) { $gf_cmd = 'git-filter-repo' }
} catch {}
if (-not $gf_cmd) {
  # Try adding common user Scripts path (pip --user)
  $userScripts = Join-Path $env:USERPROFILE "AppData\Roaming\Python\Python312\Scripts"
  if (Test-Path $userScripts) { $env:PATH += ";$userScripts" }
  try { & git-filter-repo --version > $null 2>&1; if ($LASTEXITCODE -eq 0) { $gf_cmd = 'git-filter-repo' } } catch {}
}
if (-not $gf_cmd) {
  # Try python -m git_filter_repo
  try { python -m git_filter_repo --version > $null 2>&1; if ($LASTEXITCODE -eq 0) { $gf_cmd = 'python -m git_filter_repo' } } catch {}
}
if (-not $gf_cmd) {
  Write-Host 'git-filter-repo not found in PATH and python -m git_filter_repo failed.' -ForegroundColor Yellow
  Write-Host 'Install via: python -m pip install --user git-filter-repo' -ForegroundColor Yellow
  Write-Host 'Or use BFG (Java) as an alternative.' -ForegroundColor Yellow
  exit 1
} else {
  Write-Host "Using git-filter-repo command: $gf_cmd" -ForegroundColor Green
}

Write-Host "Creating mirror clone: $MirrorDir" -ForegroundColor Cyan
if (Test-Path $MirrorDir) { Remove-Item -Recurse -Force $MirrorDir }
& git clone --mirror --no-local "$root" "$MirrorDir"
if ($LASTEXITCODE -ne 0) { Write-ErrExit 'git clone --mirror failed' }

# Resolve replacements path to absolute path so the mirror process can read it
try {
  $ReplacementsPathFull = (Resolve-Path -Path $ReplacementsPath -ErrorAction Stop).Path
} catch {
  Write-ErrExit "Cannot resolve replacements path: $ReplacementsPath"
}

Push-Location $MirrorDir
Write-Host "Running git-filter-repo with replacements file: $ReplacementsPathFull" -ForegroundColor Cyan
try {
    if ($gf_cmd -eq 'git-filter-repo') {
      & git-filter-repo --replace-text "$ReplacementsPathFull"
      if ($LASTEXITCODE -ne 0) { Write-ErrExit 'git-filter-repo failed' }
    } else {
      & python -m git_filter_repo --replace-text "$ReplacementsPathFull"
      if ($LASTEXITCODE -ne 0) { Write-ErrExit 'git-filter-repo failed' }
    }
} catch { Write-ErrExit "git-filter-repo invocation failed: $_" }

Write-Host "Checking mirror for remaining 'REDACTED_SLACK_HOOKS_DOMAIN' occurrences..." -ForegroundColor Cyan
try {
  $found = & git grep -n "REDACTED_SLACK_HOOKS_DOMAIN" --all 2>$null
  if ($LASTEXITCODE -ne 0) { $found = $null }
} catch { $found = $null }
if ($found) {
  Write-Host "WARNING: occurrences still found:" -ForegroundColor Red
  Write-Host $found
  Write-Host 'Aborting. Review replacements.txt or other strings.' -ForegroundColor Red
  Pop-Location
  exit 1
} else {
  Write-Host "No occurrences of 'REDACTED_SLACK_HOOKS_DOMAIN' found in mirror." -ForegroundColor Green
}

Write-Host "Ready to force-push rewritten history to remote 'origin'." -ForegroundColor Yellow
if ($DryRun) {
  Write-Host "DryRun mode enabled -- skipping force-push. You can review the mirror at: $MirrorDir" -ForegroundColor Cyan
  Pop-Location
  Write-Host "DryRun finished." -ForegroundColor Green
  exit 0
}

$doPush = $false
if ($AutoConfirm) { $doPush = $true } else {
  $confirm = Read-Host 'Confirm force-push all branches and tags to origin? Type "y" to confirm'
  if ($confirm -eq 'y') { $doPush = $true }
}

if (-not $doPush) { Write-Host 'Aborting as requested by user.'; Pop-Location; exit 0 }

Write-Host 'Pushing --force --all to origin' -ForegroundColor Cyan
& git remote -v
  try {
    # Get origin URL from source repository (outside mirror)
    try { $sourceOrigin = git -C "$root" remote get-url origin 2>$null } catch { $sourceOrigin = $null }
    if (-not $sourceOrigin) {
      Write-Host "Warning: could not determine origin URL from source repo. Mirror may not have 'origin' remote to push to." -ForegroundColor Yellow
    } else {
      # If mirror lost origin remote, add it
      try { $mirrorOrigin = git remote get-url origin 2>$null } catch { $mirrorOrigin = $null }
      if (-not $mirrorOrigin) {
        Write-Host "Adding origin to mirror: $sourceOrigin" -ForegroundColor Cyan
        git remote add origin $sourceOrigin
        if ($LASTEXITCODE -ne 0) { Write-ErrExit 'git remote add origin failed' }
      } else {
        git remote set-url origin $mirrorOrigin 2>$null | Out-Null
      }
    }

    git push --force --all origin
    if ($LASTEXITCODE -ne 0) { Write-ErrExit 'git push --force --all failed' }
    git push --force --tags origin
    if ($LASTEXITCODE -ne 0) { Write-ErrExit 'git push --force --tags failed' }
  } catch { Write-ErrExit "Force-push failed: $_" }

Pop-Location

Write-Host "Force-push completed. Next steps: rotate the exposed secret and notify collaborators." -ForegroundColor Green
Write-Host "Quick guidance: revoke the old secret (e.g. delete webhook), create a new one, update configs, and DO NOT commit secrets into the repo." -ForegroundColor Yellow
