Write-Host "`n🔍 AUDIT" -ForegroundColor Cyan
Test-Path "backend" -PathType Container | ForEach-Object { Write-Host "✅ backend/" -ForegroundColor Green }
Test-Path "backend\app\main.py" | ForEach-Object { Write-Host "✅ backend\app\main.py" -ForegroundColor Green }
Test-Path "backend\app\core\engine.py" | ForEach-Object { Write-Host "✅ backend\app\core\engine.py" -ForegroundColor Green }
Write-Host "All files OK!`n" -ForegroundColor Green
