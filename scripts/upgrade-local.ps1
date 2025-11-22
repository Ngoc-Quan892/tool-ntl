<#
Local helper to perform dependency upgrades on Windows (PowerShell).
Usage: .\scripts\upgrade-local.ps1
#>

Set-StrictMode -Version Latest

Write-Host "==> Starting local upgrade process"

# Create branch
$branch = "upgrade-automation-$(Get-Date -Format yyyyMMdd_HHmmss)"
Write-Host "Creating branch: $branch"
git checkout -b $branch

# Backend upgrades
if (Test-Path "backend\requirements.txt") {
    Write-Host "--> Upgrading backend Python packages"
    python -m pip install --upgrade pip setuptools wheel
    Push-Location backend
    $outdated = & python -m pip list --outdated --format=freeze 2>$null | ForEach-Object { ($_ -split "=")[0] }
    if ($outdated) {
        Write-Host "Updating: $outdated"
        foreach ($pkg in $outdated) { python -m pip install --upgrade $pkg }
    } else { Write-Host "No outdated Python packages" }
    & python -m pip freeze > requirements.txt
    Pop-Location
}

# Frontend upgrades
if (Test-Path "frontend\package.json") {
    Write-Host "--> Upgrading frontend Node packages"
    Push-Location frontend
    npx --yes npm-check-updates -u
    npm install
    Pop-Location
}

Write-Host "==> Run tests locally now (backend/frontend) and commit changes when ready."
