# Monitoring Verification Summary

Tài liệu tổng hợp về verification monitoring components.

## 📋 Files Created

### 1. PowerShell Verification Script
- **Location**: `deployment/scripts/verify_monitoring.ps1`
- **Purpose**: Script PowerShell để verify monitoring stack
- **Features**:
  - Kiểm tra Prometheus health
  - Kiểm tra Grafana health
  - Verify metrics endpoint
  - Check Prometheus targets
  - Check Grafana datasource
  - Generate load test
  - Display sample metrics
  - Status summary

### 2. Verification Documentation
- **Location**: `deployment/VERIFY_MONITORING.md`
- **Purpose**: Hướng dẫn chi tiết về verification
- **Contents**:
  - Quick start guide
  - Manual verification steps
  - Troubleshooting guide
  - Expected results
  - Access URLs

## 🚀 Quick Start

### Prerequisites

1. **Docker services đang chạy:**
   ```bash
   docker compose -f deployment/docker-compose.prod.yml up -d prometheus grafana backend
   ```

2. **Đợi services sẵn sàng:**
   - Prometheus: ~10 giây
   - Grafana: ~30 giây
   - Backend: ~60 giây

### Run Verification

**PowerShell (Windows):**
```powershell
cd deployment/scripts
.\verify_monitoring.ps1
```

**Bash (Linux/Mac):**
```bash
cd deployment/scripts
bash test_monitoring.sh
```

## ✅ Expected Output

### Successful Verification

```
==========================================
  MONITORING STACK VALIDATION
==========================================

🚀 Step 1: Starting monitoring stack...
⏳ Waiting 30 seconds for services to be ready...

🔍 Test 2: Checking Prometheus...
   ✅ Prometheus is Healthy
   📊 Prometheus Targets:
      ✅ baccarat-backend: up

🔍 Test 3: Checking Grafana...
   ✅ Grafana is running
      Version: 10.x.x
      Database: ok

🔍 Test 4: Checking metrics endpoint...
   ✅ Metrics endpoint is responding
   📊 Sample Metrics (first 20 lines):
      cache_hit_rate = 0.85
      avg_response_time_ms = 45.2
      active_connections = 8

==========================================
✅ MONITORING STACK VALIDATION RESULTS
==========================================

Component Status:
├─ Prometheus: UP (http://localhost:9090)
├─ Grafana: UP (http://localhost:3000)
├─ Metrics Endpoint: RESPONDING
├─ Data Flow: WORKING
└─ Dashboard: ACCESSIBLE

📊 Sample Metrics:
- cache_hit_rate: 0.85
- avg_response_time_ms: 45.2
- active_connections: 8
- requests_per_second: 120

✅ All critical components are healthy!
```

## 🔍 Manual Verification Steps

### Step 1: Check Prometheus

```powershell
# Health check
$response = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy"
$response.Content
# Expected: "Prometheus is Healthy."

# Check targets
$response = Invoke-WebRequest -Uri "http://localhost:9090/api/v1/targets"
$targets = $response.Content | ConvertFrom-Json
$targets.data.activeTargets | Select-Object @{N='job';E={$_.labels.job}}, health
# Expected: All targets "up"
```

### Step 2: Check Grafana

```powershell
# Health check
$response = Invoke-WebRequest -Uri "http://localhost:3000/api/health"
$health = $response.Content | ConvertFrom-Json
$health
# Expected: {"commit": "...", "database": "ok", "version": "..."}
```

### Step 3: Check Metrics Endpoint

```powershell
# Get metrics
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v2/metrics/prometheus"
$metrics = $response.Content -split "`n" | Select-Object -First 20
$metrics
# Expected: Prometheus format metrics
```

## 📊 Verification Checklist

Trước khi deploy production, verify:

- [ ] Prometheus running và healthy
- [ ] Grafana running và healthy
- [ ] Backend metrics endpoint accessible
- [ ] Prometheus can scrape backend
- [ ] Grafana can connect to Prometheus
- [ ] Metrics are being collected
- [ ] Sample metrics visible
- [ ] All targets "up" in Prometheus
- [ ] Grafana datasource configured

## 🔧 Troubleshooting

### Prometheus không chạy

**Symptoms:**
- `curl http://localhost:9090/-/healthy` fails
- Script shows "Prometheus is not accessible"

**Solutions:**
```bash
# Check status
docker compose -f deployment/docker-compose.prod.yml ps prometheus

# Check logs
docker compose -f deployment/docker-compose.prod.yml logs prometheus

# Restart
docker compose -f deployment/docker-compose.prod.yml restart prometheus
```

### Grafana không chạy

**Symptoms:**
- `curl http://localhost:3000/api/health` fails
- Script shows "Grafana is not accessible"

**Solutions:**
```bash
# Check status
docker compose -f deployment/docker-compose.prod.yml ps grafana

# Check logs
docker compose -f deployment/docker-compose.prod.yml logs grafana

# Restart
docker compose -f deployment/docker-compose.prod.yml restart grafana
```

### Metrics endpoint không accessible

**Symptoms:**
- `curl http://localhost:8000/api/v2/metrics/prometheus` fails
- Script shows "Metrics endpoint is not accessible"

**Solutions:**
```bash
# Check backend status
docker compose -f deployment/docker-compose.prod.yml ps backend

# Check backend logs
docker compose -f deployment/docker-compose.prod.yml logs backend

# Restart backend
docker compose -f deployment/docker-compose.prod.yml restart backend

# Wait for backend to be ready
sleep 30

# Test again
curl http://localhost:8000/api/v2/metrics/prometheus
```

### Prometheus không scrape được backend

**Symptoms:**
- Targets show "down" in Prometheus UI
- Script shows "Prometheus targets may not be up yet"

**Solutions:**
1. Check Prometheus config:
   ```bash
   cat deployment/monitoring/prometheus.yml
   ```

2. Verify backend is accessible from Prometheus:
   ```bash
   docker compose -f deployment/docker-compose.prod.yml exec prometheus \
     wget -O- http://backend:8000/api/v2/metrics/prometheus
   ```

3. Check network:
   ```bash
   docker compose -f deployment/docker-compose.prod.yml network ls
   ```

4. Restart Prometheus:
   ```bash
   docker compose -f deployment/docker-compose.prod.yml restart prometheus
   ```

## 📍 Access URLs

Sau khi verification thành công:

- **Prometheus**: http://localhost:9090
  - Targets: http://localhost:9090/targets
  - Graph: http://localhost:9090/graph
  - Alerts: http://localhost:9090/alerts

- **Grafana**: http://localhost:3000
  - Default credentials: admin/admin
  - Dashboards: http://localhost:3000/dashboards
  - Datasources: http://localhost:3000/datasources

- **Backend Metrics**: http://localhost:8000/api/v2/metrics/prometheus
- **Monitoring Dashboard**: http://localhost:8000/api/monitoring/dashboard
- **Health Check**: http://localhost:8000/health

## 🎯 Next Steps

Sau khi verification thành công:

1. **Import Grafana Dashboard:**
   - Access Grafana: http://localhost:3000
   - Login với admin/admin
   - Import dashboard từ: `deployment/monitoring/grafana/dashboards/baccarat-dashboard.json`

2. **Configure Alerts:**
   - Set up alert rules trong Prometheus
   - Configure notification channels trong Grafana
   - Test alert notifications

3. **Monitor Production:**
   - Watch metrics dashboard
   - Review performance trends
   - Set up alerting rules
   - Document baseline metrics

## 📝 Notes

- **Verification time**: ~2-3 phút
- **Services required**: Prometheus, Grafana, Backend
- **Network**: All services must be in same Docker network
- **Ports**: 9090 (Prometheus), 3000 (Grafana), 8000 (Backend)
- **Script timeout**: 5 seconds per check
- **Load test**: 10 requests with 0.5s interval

## 🔗 Related Files

- `deployment/scripts/verify_monitoring.ps1` - PowerShell verification script
- `deployment/scripts/test_monitoring.sh` - Bash verification script
- `deployment/VERIFY_MONITORING.md` - Detailed verification guide
- `deployment/monitoring/prometheus.yml` - Prometheus configuration
- `deployment/monitoring/grafana/` - Grafana configuration
- `deployment/SETUP_COMPLETE.md` - Complete setup summary

## ✅ Success Criteria

Verification được coi là thành công khi:

- ✅ Prometheus: UP
- ✅ Grafana: UP
- ✅ Metrics Endpoint: RESPONDING
- ✅ Data Flow: WORKING
- ✅ Dashboard: ACCESSIBLE
- ✅ All targets: UP
- ✅ Metrics being collected
- ✅ Sample metrics visible

---

**Last Updated**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Status**: ✅ Ready for Verification

