Write-Host "🔍 VALIDATING FILE CONTENTS" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
Write-Host ""

function Test-FileContent {
    param(
        [string]$FilePath,
        [string]$Keyword,
        [string]$Description
    )

    if (-not (Test-Path -LiteralPath $FilePath)) {
        Write-Host "❌ FILE MISSING: $FilePath" -ForegroundColor Red
        return $false
    }

    $content = Get-Content -LiteralPath $FilePath -Raw -ErrorAction SilentlyContinue

    if ($content -like "*$Keyword*") {
        Write-Host "✅ $Description" -ForegroundColor Green
        return $true
    } else {
        Write-Host "⚠️  $Description - INCOMPLETE OR WRONG" -ForegroundColor Yellow
        return $false
    }
}

Write-Host "📋 Checking backend/app/core/engine.py" -ForegroundColor Yellow
Test-FileContent "backend/app/core/engine.py" "class BaccaratEngine" "BaccaratEngine class defined" | Out-Null
Test-FileContent "backend/app/core/engine.py" "class Card" "Card class defined" | Out-Null
Test-FileContent "backend/app/core/engine.py" "class Shoe" "Shoe class defined" | Out-Null
Test-FileContent "backend/app/core/engine.py" "def play_hand" "play_hand method exists" | Out-Null
Write-Host ""

Write-Host "📋 Checking backend/app/core/config.py" -ForegroundColor Yellow
Test-FileContent "backend/app/core/config.py" "BaseSettings" "Pydantic BaseSettings imported" | Out-Null
Test-FileContent "backend/app/core/config.py" "class Settings" "Settings class defined" | Out-Null
Test-FileContent "backend/app/core/config.py" "DATABASE_URL" "DATABASE_URL configured" | Out-Null
Write-Host ""

Write-Host "📋 Checking backend/requirements.txt" -ForegroundColor Yellow
Test-FileContent "backend/requirements.txt" "fastapi" "fastapi dependency" | Out-Null
Test-FileContent "backend/requirements.txt" "sqlalchemy" "sqlalchemy dependency" | Out-Null
Test-FileContent "backend/requirements.txt" "pytest" "pytest dependency" | Out-Null
Test-FileContent "backend/requirements.txt" "pydantic" "pydantic dependency" | Out-Null
Write-Host ""

Write-Host "📋 Checking backend/tests/conftest.py" -ForegroundColor Yellow
Test-FileContent "backend/tests/conftest.py" "@pytest.fixture" "pytest fixtures defined" | Out-Null
Test-FileContent "backend/tests/conftest.py" "def test_db" "test_db fixture" | Out-Null
Write-Host ""

Write-Host "📋 Checking backend/.env.example" -ForegroundColor Yellow
Test-FileContent "backend/.env.example" "DATABASE_URL" "DATABASE_URL in .env" | Out-Null
Test-FileContent "backend/.env.example" "DEBUG" "DEBUG in .env" | Out-Null
Write-Host ""

Write-Host "============================" -ForegroundColor Cyan
Write-Host "✅ VALIDATION COMPLETE" -ForegroundColor Green

