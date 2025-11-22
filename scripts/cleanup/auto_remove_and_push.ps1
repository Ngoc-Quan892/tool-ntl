<#
.SYNOPSIS
  Automated wrapper to run the secret-removal workflow end-to-end.

.DESCRIPTION
  This script performs a safe, repeatable sequence:
    - set UTF-8 code page
    - ensure replacements file exists
    - install git-filter-repo (pip --user) if missing
    - run remove_secret_full.ps1 in DryRun mode and capture transcript
    - optionally run the real rewrite + force-push (AutoConfirm) if DryRun output looks good

.USAGE
  .\auto_remove_and_push.ps1 -ReplacementsPath .\replacements.txt

Note: This script must be executed locally. Do NOT paste secrets into chat.
#>

param(
    [string]$ReplacementsPath = "$(Get-Location)\replacements.txt",
    [switch]$SkipInstall,
    [switch]$RunAutoPush,
    [string]$LogPath = "$(Get-Location)\auto-remove-log.txt"
)

function Write-ErrExit($m) { Write-Host $m -ForegroundColor Red; exit 1 }

Write-Host "Auto cleanup wrapper: starting" -ForegroundColor Cyan

# set UTF-8 code page for current process
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

if (-not (Test-Path $ReplacementsPath)) {
    Write-ErrExit "Replacements file not found: $ReplacementsPath`nPlease create it with secret==>replacement or regex:...==>[REDACTED]"
}

if (-not $SkipInstall) {
    # ensure git-filter-repo available
    $found = $false
    try { & git-filter-repo --version > $null 2>&1; if ($LASTEXITCODE -eq 0) { $found = $true } } catch {}
    if (-not $found) {
        Write-Host "Installing git-filter-repo via pip (user)" -ForegroundColor Yellow
        python -m pip install --user git-filter-repo
        # add user Scripts path to PATH for this session
        $userScripts = Join-Path $env:USERPROFILE "AppData\Roaming\Python\Python312\Scripts"
        if (Test-Path $userScripts) { $env:PATH += ";$userScripts" }
        try { & git-filter-repo --version > $null 2>&1; if ($LASTEXITCODE -eq 0) { $found = $true } } catch {}
        if (-not $found) { Write-ErrExit "Failed to install or detect git-filter-repo. Please install manually." }
    } else {
        Write-Host "git-filter-repo is available." -ForegroundColor Green
    }
} else {
    Write-Host "Skipping install step as requested." -ForegroundColor Yellow
}

# Run DryRun and capture transcript
Write-Host "Running DryRun of remove_secret_full.ps1..." -ForegroundColor Cyan
if (Test-Path $LogPath) { Remove-Item $LogPath -Force }
Start-Transcript -Path $LogPath -Force

# Resolve path to remove_secret_full.ps1 relative to this wrapper script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$removeScript = Join-Path $scriptDir 'remove_secret_full.ps1'
if (-not (Test-Path $removeScript)) {
    Stop-Transcript
    Write-ErrExit "Cannot find the required script: $removeScript. Ensure it exists in the same folder as this wrapper.";
}

& $removeScript -ReplacementsPath $ReplacementsPath -DryRun
$dryExit = $LASTEXITCODE
Stop-Transcript

if ($dryExit -ne 0) { Write-Host "DryRun failed (exit code $dryExit). Check $LogPath for details." -ForegroundColor Red; exit 1 }

Write-Host "DryRun completed. Transcript saved to: $LogPath" -ForegroundColor Green
Write-Host "Please review the transcript. If results look correct, re-run this script with -RunAutoPush to perform force-push." -ForegroundColor Yellow

if ($RunAutoPush) {
    Write-Host "Auto-push requested: running remove_secret_full.ps1 with AutoConfirm..." -ForegroundColor Cyan
    Start-Transcript -Path $LogPath -Append
    & .\remove_secret_full.ps1 -ReplacementsPath $ReplacementsPath -AutoConfirm
    $pushExit = $LASTEXITCODE
    Stop-Transcript
    if ($pushExit -ne 0) { Write-ErrExit "Auto-push failed (exit code $pushExit). See $LogPath" }
    Write-Host "Auto-push completed successfully. See $LogPath for details." -ForegroundColor Green
}

Write-Host "Auto wrapper finished." -ForegroundColor Cyan
