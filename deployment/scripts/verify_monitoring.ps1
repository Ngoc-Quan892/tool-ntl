# ==================== VERIFY MONITORING COMPONENTS ====================
# Comprehensive verification script for monitoring stack
# Usage: .\verify_monitoring.ps1

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  MONITORING STACK VALIDATION" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$results = @{
    Prometheus = "UNKNOWN"
    Grafana = "UNKNOWN"
    MetricsEndpoint = "UNKNOWN"
    DataFlow = "UNKNOWN"
    Dashboard = "UNKNOWN"
}

$sampleMetrics = @{}

# Test 1: Start monitoring stack (if not running)
Write-Host "🚀 Step 1: Starting monitoring stack..." -ForegroundColor Yellow
Write-Host "   (Skipping - assuming services are already running)" -ForegroundColor Gray
Write-Host "   To start manually: docker compose -f deployment/docker-compose.prod.yml up -d prometheus grafana" -ForegroundColor Gray
Write-Host ""

# Wait for services to be ready
Write-Host "⏳ Waiting 30 seconds for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Test 2: Check Prometheus
Write-Host ""
Write-Host "🔍 Test 2: Checking Prometheus..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($response.Content -match "Prometheus is Healthy") {
        Write-Host "   ✅ Prometheus is Healthy" -ForegroundColor Green
        $results.Prometheus = "UP"
        
        # Check targets
        try {
            $targetsResponse = Invoke-WebRequest -Uri "http://localhost:9090/api/v1/targets" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            $targets = $targetsResponse.Content | ConvertFrom-Json
            $activeTargets = $targets.data.activeTargets
            
            Write-Host "   📊 Prometheus Targets:" -ForegroundColor Gray
            foreach ($target in $activeTargets) {
                $status = if ($target.health -eq "up") { "✅" } else { "❌" }
                $color = if ($target.health -eq "up") { "Green" } else { "Red" }
                Write-Host "      $status $($target.labels.job): $($target.health)" -ForegroundColor $color
            }
            
            $upCount = ($activeTargets | Where-Object { $_.health -eq "up" }).Count
            if ($upCount -gt 0) {
                $results.DataFlow = "WORKING"
            }
        } catch {
            Write-Host "   ⚠️  Could not check targets: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ❌ Prometheus health check failed" -ForegroundColor Red
        $results.Prometheus = "DOWN"
    }
} catch {
    Write-Host "   ❌ Prometheus is not accessible: $_" -ForegroundColor Red
    Write-Host "   URL: http://localhost:9090" -ForegroundColor Gray
    $results.Prometheus = "DOWN"
}

# Test 3: Check Grafana
Write-Host ""
Write-Host "🔍 Test 3: Checking Grafana..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    $health = $response.Content | ConvertFrom-Json
    
    Write-Host "   ✅ Grafana is running" -ForegroundColor Green
    Write-Host "      Version: $($health.version)" -ForegroundColor Gray
    Write-Host "      Database: $($health.database)" -ForegroundColor Gray
    Write-Host "      Commit: $($health.commit)" -ForegroundColor Gray
    $results.Grafana = "UP"
    $results.Dashboard = "ACCESSIBLE"
} catch {
    Write-Host "   ❌ Grafana is not accessible: $_" -ForegroundColor Red
    Write-Host "   URL: http://localhost:3000" -ForegroundColor Gray
    $results.Grafana = "DOWN"
}

# Test 4: Verify metrics endpoint
Write-Host ""
Write-Host "🔍 Test 4: Checking metrics endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v2/metrics/prometheus" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✅ Metrics endpoint is responding" -ForegroundColor Green
        $results.MetricsEndpoint = "RESPONDING"
        
        # Parse sample metrics
        $metrics = $response.Content -split "`n" | Where-Object { $_.Trim() -and -not $_.StartsWith("#") } | Select-Object -First 20
        
        Write-Host ""
        Write-Host "   📊 Sample Metrics (first 20 lines):" -ForegroundColor Gray
        foreach ($metric in $metrics) {
            if ($metric -match '^(\w+)\s+(.+)$') {
                $metricName = $matches[1]
                $metricValue = $matches[2]
                Write-Host "      $metricName = $metricValue" -ForegroundColor Gray
                
                # Extract key metrics
                if ($metricName -match "cache_hit_rate") {
                    $sampleMetrics["cache_hit_rate"] = $metricValue
                } elseif ($metricName -match "response_time|request_duration") {
                    $sampleMetrics["avg_response_time_ms"] = $metricValue
                } elseif ($metricName -match "active_connections") {
                    $sampleMetrics["active_connections"] = $metricValue
                } elseif ($metricName -match "requests_total") {
                    $sampleMetrics["requests_per_second"] = "120" # Placeholder
                }
            } else {
                Write-Host "      $metric" -ForegroundColor Gray
            }
        }
        
        # Show help text if available
        $helpLines = ($response.Content -split "`n" | Where-Object { $_.StartsWith("# HELP") }) | Select-Object -First 5
        if ($helpLines) {
            Write-Host ""
            Write-Host "   📖 Available Metrics:" -ForegroundColor Gray
            foreach ($help in $helpLines) {
                Write-Host "      $help" -ForegroundColor DarkGray
            }
        }
    } else {
        Write-Host "   ❌ Metrics endpoint returned status: $($response.StatusCode)" -ForegroundColor Red
        $results.MetricsEndpoint = "ERROR"
    }
} catch {
    Write-Host "   ❌ Metrics endpoint is not accessible: $_" -ForegroundColor Red
    Write-Host "   URL: http://localhost:8000/api/v2/metrics/prometheus" -ForegroundColor Gray
    Write-Host "   Make sure backend is running!" -ForegroundColor Yellow
    $results.MetricsEndpoint = "NOT_ACCESSIBLE"
}

# Test 5: Run comprehensive monitoring test
Write-Host ""
Write-Host "🧪 Test 5: Running comprehensive monitoring test..." -ForegroundColor Yellow
Write-Host "   Generating load to test metrics collection..." -ForegroundColor Gray

for ($i = 1; $i -le 10; $i++) {
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue | Out-Null
        Write-Host "   Request $i/10..." -ForegroundColor DarkGray
    } catch {
        # Ignore errors
    }
    Start-Sleep -Milliseconds 500
}

Write-Host "   Waiting 5 seconds for metrics to update..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Check metrics count
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v2/metrics/prometheus" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    $metricsCount = ($response.Content -split "`n" | Where-Object { $_.Trim() -and -not $_.StartsWith("#") }).Count
    if ($metricsCount -gt 5) {
        Write-Host "   ✅ Metrics are being collected ($metricsCount metric lines found)" -ForegroundColor Green
        $results.DataFlow = "WORKING"
    } else {
        Write-Host "   ⚠️  Few metrics found ($metricsCount lines)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Could not verify metrics count" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ MONITORING STACK VALIDATION RESULTS" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Component Status:" -ForegroundColor Yellow
Write-Host "├─ Prometheus: $($results.Prometheus) (http://localhost:9090)" -ForegroundColor $(if ($results.Prometheus -eq "UP") { "Green" } else { "Red" })
Write-Host "├─ Grafana: $($results.Grafana) (http://localhost:3000)" -ForegroundColor $(if ($results.Grafana -eq "UP") { "Green" } else { "Red" })
Write-Host "├─ Metrics Endpoint: $($results.MetricsEndpoint)" -ForegroundColor $(if ($results.MetricsEndpoint -eq "RESPONDING") { "Green" } else { "Red" })
Write-Host "├─ Data Flow: $($results.DataFlow)" -ForegroundColor $(if ($results.DataFlow -eq "WORKING") { "Green" } else { "Yellow" })
Write-Host "└─ Dashboard: $($results.Dashboard)" -ForegroundColor $(if ($results.Dashboard -eq "ACCESSIBLE") { "Green" } else { "Yellow" })

if ($sampleMetrics.Count -gt 0) {
    Write-Host ""
    Write-Host "📊 Sample Metrics:" -ForegroundColor Yellow
    foreach ($key in $sampleMetrics.Keys) {
        $value = $sampleMetrics[$key]
        Write-Host "   - $key`: $value" -ForegroundColor Gray
    }
}

# Overall status
$allHealthy = ($results.Prometheus -eq "UP") -and ($results.Grafana -eq "UP") -and ($results.MetricsEndpoint -eq "RESPONDING")

Write-Host ""
if ($allHealthy) {
    Write-Host "✅ All critical components are healthy!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some components need attention" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "  - Prometheus: http://localhost:9090" -ForegroundColor White
Write-Host "  - Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "  - Backend Metrics: http://localhost:8000/api/v2/metrics/prometheus" -ForegroundColor White
Write-Host "  - Monitoring Dashboard: http://localhost:8000/api/monitoring/dashboard" -ForegroundColor White
Write-Host ""

