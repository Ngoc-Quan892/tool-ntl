# Verify Monitoring Components - Hướng dẫn

Hướng dẫn verify tất cả monitoring components hoạt động đúng.

## 🚀 Quick Start

### Option 1: PowerShell Script (Windows)

```powershell
# Chạy script verification
cd deployment/scripts
.\verify_monitoring.ps1
```

### Option 2: Bash Script (Linux/Mac)

```bash
# Chạy script verification
cd deployment/scripts
bash test_monitoring.sh
```

### Option 3: Manual Verification

Xem các bước bên dưới.

## 📋 Verification Steps

### Step 1: Start Monitoring Stack

```bash
# Start Prometheus và Grafana
cd deployment
docker compose -f docker-compose.prod.yml up -d prometheus grafana

# Hoặc nếu dùng docker-compose (V1)
docker-compose -f docker-compose.prod.yml up -d prometheus grafana

# Wait for services to be ready
sleep 30  # hoặc Start-Sleep -Seconds 30 trong PowerShell
```

### Step 2: Check Prometheus

```bash
# Health check
curl http://localhost:9090/-/healthy
# Expected: "Prometheus is Healthy."

# Check targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
# Expected: All targets "up"
```

**PowerShell:**
```powershell
# Health check
Invoke-WebRequest -Uri "http://localhost:9090/-/healthy"

# Check targets
$response = Invoke-WebRequest -Uri "http://localhost:9090/api/v1/targets"
$targets = $response.Content | ConvertFrom-Json
$targets.data.activeTargets | Select-Object @{N='job';E={$_.labels.job}}, health
```

### Step 3: Check Grafana

```bash
# Health check
curl http://localhost:3000/api/health
# Expected: {"commit": "...", "database": "ok", "version": "..."}
```

**PowerShell:**
```powershell
$response = Invoke-WebRequest -Uri "http://localhost:3000/api/health"
$health = $response.Content | ConvertFrom-Json
$health
```

### Step 4: Verify Metrics Endpoint

```bash
# Check metrics endpoint
curl -s http://localhost:8000/api/v2/metrics/prometheus | head -20
# Expected: Prometheus format metrics
```

**PowerShell:**
```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v2/metrics/prometheus"
$response.Content -split "`n" | Select-Object -First 20
```

**Expected Output:**
```
# HELP cache_hit_rate Cache hit rate
# TYPE cache_hit_rate gauge
cache_hit_rate{level="l1"} 0.85
...
```

### Step 5: Run Comprehensive Test

```bash
# Run test script
bash deployment/scripts/test_monitoring.sh
```

**PowerShell:**
```powershell
.\deployment\scripts\verify_monitoring.ps1
```

## ✅ Expected Results

### All Services Healthy

```
✅ Monitoring Stack Validation Results:

├─ Prometheus: UP (http://localhost:9090)
├─ Grafana: UP (http://localhost:3000)
├─ Metrics Endpoint: RESPONDING
├─ Data Flow: WORKING
└─ Dashboard: ACCESSIBLE
```

### Sample Metrics

Sau khi chạy test, bạn sẽ thấy các metrics như:

```
📊 Sample Metrics:
- cache_hit_rate: 0.85
- avg_response_time_ms: 45.2
- active_connections: 8
- requests_per_second: 120
```

## 🔧 Troubleshooting

### Prometheus không chạy

**Kiểm tra:**
```bash
docker compose -f deployment/docker-compose.prod.yml ps prometheus
docker compose -f deployment/docker-compose.prod.yml logs prometheus
```

**Fix:**
```bash
docker compose -f deployment/docker-compose.prod.yml up -d prometheus
```

### Grafana không chạy

**Kiểm tra:**
```bash
docker compose -f deployment/docker-compose.prod.yml ps grafana
docker compose -f deployment/docker-compose.prod.yml logs grafana
```

**Fix:**
```bash
docker compose -f deployment/docker-compose.prod.yml up -d grafana
```

### Metrics endpoint không accessible

**Kiểm tra:**
1. Backend có đang chạy không?
   ```bash
   docker compose -f deployment/docker-compose.prod.yml ps backend
   ```

2. Backend có expose port 8000 không?
   ```bash
   curl http://localhost:8000/health
   ```

3. Metrics endpoint có đúng path không?
   ```bash
   curl http://localhost:8000/api/v2/metrics/prometheus
   ```

**Fix:**
```bash
# Start backend
docker compose -f deployment/docker-compose.prod.yml up -d backend

# Wait for backend to be ready
sleep 10

# Test again
curl http://localhost:8000/api/v2/metrics/prometheus
```

### Prometheus không scrape được backend

**Kiểm tra:**
1. Prometheus config đúng chưa?
   ```bash
   cat deployment/monitoring/prometheus.yml
   ```

2. Backend có accessible từ Prometheus container không?
   ```bash
   docker compose -f deployment/docker-compose.prod.yml exec prometheus \
     wget -O- http://backend:8000/api/v2/metrics/prometheus
   ```

**Fix:**
- Đảm bảo backend và Prometheus trong cùng network
- Kiểm tra target URL trong Prometheus UI: http://localhost:9090/targets

### Grafana không connect được Prometheus

**Kiểm tra:**
1. Datasource có được provision không?
   ```bash
   cat deployment/monitoring/grafana/provisioning/datasources/prometheus.yml
   ```

2. Prometheus có accessible từ Grafana container không?
   ```bash
   docker compose -f deployment/docker-compose.prod.yml exec grafana \
     wget -O- http://prometheus:9090/-/healthy
   ```

**Fix:**
- Đảm bảo Grafana và Prometheus trong cùng network
- Check Grafana logs: `docker compose logs grafana`
- Manually add datasource trong Grafana UI nếu cần

## 📊 Access URLs

Sau khi verify thành công, truy cập:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Backend Metrics**: http://localhost:8000/api/v2/metrics/prometheus
- **Monitoring Dashboard**: http://localhost:8000/api/monitoring/dashboard

## 🎯 Next Steps

1. **Import Grafana Dashboard:**
   - Access Grafana: http://localhost:3000
   - Login với admin/admin
   - Import dashboard từ: `deployment/monitoring/grafana/dashboards/baccarat-dashboard.json`

2. **Configure Alerts:**
   - Set up alert rules trong Prometheus
   - Configure notification channels trong Grafana

3. **Monitor Production:**
   - Watch metrics dashboard
   - Set up alerting rules
   - Review performance trends

## 📝 Notes

- **Total verification time**: ~2-3 phút
- **Services cần chạy**: Prometheus, Grafana, Backend
- **Network**: Tất cả services phải trong cùng Docker network
- **Ports**: 9090 (Prometheus), 3000 (Grafana), 8000 (Backend)

## 🔗 Related Files

- `deployment/scripts/verify_monitoring.ps1` - PowerShell verification script
- `deployment/scripts/test_monitoring.sh` - Bash verification script
- `deployment/monitoring/prometheus.yml` - Prometheus configuration
- `deployment/monitoring/grafana/` - Grafana configuration

