# ==================== TEST MONITORING SCRIPT (PowerShell) ====================
# Test real-time monitoring setup
# Usage: .\test_monitoring.ps1

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  TEST MONITORING SETUP" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$deploymentDir = Split-Path -Parent $scriptDir
Set-Location $deploymentDir\..

# Test 1: Check Prometheus is running
Write-Host "📊 Test 1: Checking Prometheus..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Prometheus is running" -ForegroundColor Green
    } else {
        Write-Host "❌ Prometheus returned status: $($response.StatusCode)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Prometheus is not running" -ForegroundColor Red
    Write-Host "   Start with: docker-compose -f deployment/docker-compose.prod.yml up -d prometheus" -ForegroundColor Yellow
    exit 1
}

# Test 2: Check Grafana is running
Write-Host ""
Write-Host "📊 Test 2: Checking Grafana..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Grafana is running" -ForegroundColor Green
        $health = $response.Content | ConvertFrom-Json
        Write-Host "   Version: $($health.version)" -ForegroundColor Gray
        Write-Host "   Database: $($health.database)" -ForegroundColor Gray
    } else {
        Write-Host "❌ Grafana returned status: $($response.StatusCode)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Grafana is not running" -ForegroundColor Red
    Write-Host "   Start with: docker-compose -f deployment/docker-compose.prod.yml up -d grafana" -ForegroundColor Yellow
    exit 1
}

# Test 3: Check backend metrics endpoint
Write-Host ""
Write-Host "📊 Test 3: Checking backend metrics endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v2/metrics/prometheus" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Backend metrics endpoint is accessible" -ForegroundColor Green
        
        # Show sample metrics
        Write-Host ""
        Write-Host "   Sample metrics:" -ForegroundColor Gray
        $metrics = $response.Content -split "`n" | Select-Object -First 20
        foreach ($line in $metrics) {
            if ($line.Trim()) {
                Write-Host "   $line" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "❌ Backend metrics endpoint returned status: $($response.StatusCode)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Backend metrics endpoint is not accessible" -ForegroundColor Red
    Write-Host "   Check if backend is running: docker-compose -f deployment/docker-compose.prod.yml ps backend" -ForegroundColor Yellow
    exit 1
}

# Test 4: Check Prometheus can scrape backend
Write-Host ""
Write-Host "📊 Test 4: Checking Prometheus targets..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9090/api/v1/targets" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    $targets = $response.Content | ConvertFrom-Json
    $activeTargets = $targets.data.activeTargets
    
    $upTargets = $activeTargets | Where-Object { $_.health -eq "up" }
    if ($upTargets.Count -gt 0) {
        Write-Host "✅ Prometheus can scrape backend" -ForegroundColor Green
        Write-Host "   Targets status:" -ForegroundColor Gray
        foreach ($target in $activeTargets) {
            $status = if ($target.health -eq "up") { "✅" } else { "❌" }
            Write-Host "   $status $($target.labels.job): $($target.health)" -ForegroundColor $(if ($target.health -eq "up") { "Green" } else { "Red" })
        }
    } else {
        Write-Host "⚠️  Prometheus targets may not be up yet" -ForegroundColor Yellow
        Write-Host "   Check Prometheus UI: http://localhost:9090/targets" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not check Prometheus targets: $_" -ForegroundColor Yellow
}

# Test 5: Check Grafana can connect to Prometheus
Write-Host ""
Write-Host "📊 Test 5: Checking Grafana datasource..." -ForegroundColor Yellow
try {
    $cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin"))
    $headers = @{ Authorization = "Basic $cred" }
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/datasources" -Headers $headers -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    $datasources = $response.Content | ConvertFrom-Json
    
    if ($datasources.Count -gt 0) {
        Write-Host "✅ Grafana datasource configured" -ForegroundColor Green
        foreach ($ds in $datasources) {
            Write-Host "   Datasource: $($ds.name) (Type: $($ds.type))" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠️  Grafana datasource may need configuration" -ForegroundColor Yellow
        Write-Host "   Access Grafana: http://localhost:3000" -ForegroundColor Yellow
        Write-Host "   Default credentials: admin/admin" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not check Grafana datasource: $_" -ForegroundColor Yellow
    Write-Host "   Access Grafana: http://localhost:3000" -ForegroundColor Yellow
    Write-Host "   Default credentials: admin/admin" -ForegroundColor Yellow
}

# Test 6: Real-time monitoring test
Write-Host ""
Write-Host "📊 Test 6: Real-time monitoring test..." -ForegroundColor Yellow
Write-Host "   Generating some load to test metrics collection..." -ForegroundColor Gray

for ($i = 1; $i -le 10; $i++) {
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # Ignore errors
    }
    Start-Sleep -Milliseconds 500
}

Write-Host "   Waiting 5 seconds for metrics to update..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Check if metrics are updating
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v2/metrics/prometheus" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    $metricsCount = ($response.Content -split "`n" | Where-Object { $_.Trim() }).Count
    if ($metricsCount -gt 5) {
        Write-Host "✅ Metrics are being collected (found $metricsCount metric lines)" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Few metrics found. Check if metrics are being exported." -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not verify metrics count: $_" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ MONITORING TEST COMPLETE" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  - Prometheus: http://localhost:9090" -ForegroundColor White
Write-Host "  - Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "  - Backend Metrics: http://localhost:8000/api/v2/metrics/prometheus" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Open Grafana and import dashboard from: deployment/monitoring/grafana/dashboards/" -ForegroundColor White
Write-Host "  2. Configure alerts in Prometheus (optional)" -ForegroundColor White
Write-Host "  3. Set up Grafana alerting rules (optional)" -ForegroundColor White
Write-Host ""

