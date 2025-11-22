# Production Load Testing Suite

Production-grade load testing suite với Locust cho Baccarat Predictor API.

## 📋 Overview

Bộ test này mô phỏng hành vi người dùng thực tế với:
- **Weighted tasks**: Phân bổ tác vụ theo tỷ lệ thực tế
- **Progressive load testing**: Tăng dần tải (10, 100, 500, 1000 users)
- **Response time tracking**: Theo dõi percentiles (p50, p95, p99)
- **Slow request logging**: Ghi log các request >200ms
- **Request categorization**: Phân loại theo read, analytics, write
- **Success/failure rates**: Tính toán và báo cáo tỷ lệ thành công/thất bại
- **System metrics**: Monitor CPU, memory, connections trong khi test
- **HTML reports**: Tạo báo cáo HTML với charts
- **Custom test scenarios**: Burst, ramp, steady-state

## 🚀 Installation

```bash
# Install Locust
pip install locust>=2.0.0

# Or install from requirements-dev
pip install -r requirements-dev.txt
```

## 👥 User Classes

### 1. BaccaratProductionUser (60% traffic)
- **Weight**: 3
- **Wait time**: 1-3 seconds
- **Tasks**:
  - `get_game_results` (weight=6): Read operations
  - `get_pattern_statistics` (weight=3): Analytics queries
  - `create_game_result` (weight=1): Write operations

### 2. BaccaratHeavyUser (20% traffic)
- **Weight**: 1
- **Wait time**: 0.5-2 seconds
- **Tasks**:
  - `get_detailed_analytics` (weight=5): Complex queries
  - `get_historical_data` (weight=3): Large date ranges
  - `export_reports` (weight=2): Generate reports

### 3. BaccaratWriteUser (20% traffic)
- **Weight**: 1
- **Wait time**: 1 second (constant)
- **Tasks**:
  - `bulk_create_results` (weight=5): Batch operations
  - `update_game_settings` (weight=3): Configuration changes
  - `delete_old_results` (weight=2): Cleanup operations

## 🎯 Performance Targets

| Operation Type | Target (p95) | Description |
|----------------|--------------|-------------|
| Read operations | <50ms | Game results (cached) |
| Analytics | <200ms | Pattern statistics (heavy computation, cached) |
| Write operations | <100ms | Create results |
| Detailed analytics | <500ms | Complex queries |
| Historical data | <1000ms | Large datasets |
| Bulk operations | <500ms | Batch inserts |
| Error rate | <1% | Overall failure rate |
| Throughput | >1000 req/s | At 500 users |

## 📊 Usage

### Basic Usage

```bash
# Run with default settings
locust -f tests/load/locustfile_production.py --host=http://localhost:8000

# Run with specific user count
locust -f tests/load/locustfile_production.py \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=10

# Run headless (no UI)
locust -f tests/load/locustfile_production.py \
  --headless \
  --host=http://localhost:8000 \
  --users=500 \
  --spawn-rate=50 \
  --run-time=10m \
  --html=report.html
```

### Progressive Load Testing

```bash
# Step load: 10 → 50 → 100 → 500 users
locust -f tests/load/locustfile_production.py \
  --host=http://localhost:8000 \
  --step-load
```

### Custom Load Shapes

```bash
# Burst testing
locust -f tests/load/locustfile_production.py \
  --host=http://localhost:8000 \
  --shape-class=BurstLoadShape

# Soak testing (endurance)
locust -f tests/load/locustfile_production.py \
  --host=http://localhost:8000 \
  --shape-class=SoakLoadShape
```

### Environment Variables

```bash
export LOCUST_TARGET_HOST="http://localhost:8000"
export LOCUST_RUN_TIME="10m"
export LOCUST_USERS="100"
export LOCUST_SPAWN_RATE="10"
export LOCUST_REPORT_HTML="report.html"

locust -f tests/load/locustfile_production.py
```

## 📈 Test Scenarios

### 1. StepLoadShape
Gradually increase load:
- 10 users (2 min)
- 50 users (2 min)
- 100 users (2 min)
- 500 users (5 min)

### 2. BurstLoadShape
Burst testing pattern:
- 10 users steady (1 min)
- Burst to 500 users (30 sec)
- Back to 10 users (1 min)
- Repeat 3 times

### 3. SoakLoadShape
Endurance testing:
- Ramp to 200 users (5 min)
- Hold 200 users (60 min)
- Ramp down (5 min)

## 📊 Metrics Collection

### Automatic Metrics

- **Request times**: Average, median, p95, p99
- **Success/failure rates**: Per endpoint
- **Slow requests**: >200ms logged automatically
- **System metrics**: CPU, memory (if psutil available)

### Custom Metrics

Metrics are logged to CSV: `metrics_TIMESTAMP.csv`

Includes:
- Timestamp
- CPU usage %
- Memory usage %
- Memory usage (MB)
- Active connections

## 📝 Output

### Console Output

```
⚠️  SLOW: get_game_results took 250ms
⚠️  SLOW: get_pattern_statistics took 350ms

==================================================
📊 LOAD TEST SUMMARY
==================================================

Total Requests: 10,000
Failures: 50 (0.50%)
Duration: 600.00 seconds
Requests/sec: 16.67

Response Times:
  - Average: 45.23ms
  - Median: 38.50ms
  - 95th %ile: 89.20ms
  - 99th %ile: 145.30ms

Slowest Endpoints (>200ms):
  1. get_pattern_statistics: 245.30ms (avg, 15 occurrences)
  2. get_detailed_analytics: 320.50ms (avg, 8 occurrences)

Most Failed Endpoints:
  1. create_game_result: 25 failures
  2. bulk_create_results: 15 failures
==================================================
```

### HTML Report

Generate HTML report:
```bash
locust -f tests/load/locustfile_production.py \
  --headless \
  --users=500 \
  --run-time=10m \
  --html=report.html
```

Report includes:
- Request statistics
- Response time charts
- Failure rates
- Per-endpoint breakdown

## ✅ Validation

### Response Validation

All tasks validate:
- ✅ Status codes
- ✅ Response time targets
- ✅ Response data structure
- ✅ Required fields present

### Example Validation

```python
# Game results validation
- Status code: 200
- Content-Type: application/json
- Has 'results' key
- 'results' is a list
- Each result has: id, game_id, result

# Pattern statistics validation
- Status code: 200
- Has 'pattern_type' key
- Has 'occurrences' key
- Has 'statistics' dict
```

## 🔧 Troubleshooting

### Tests Failing

1. **Check target host:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check endpoints exist:**
   ```bash
   curl http://localhost:8000/api/v2/game/1/results
   ```

3. **Check response times:**
   - Review slow requests in console
   - Check if targets are too aggressive

### High Failure Rate

1. **Check error messages:**
   - Review console output
   - Check HTML report

2. **Reduce load:**
   ```bash
   locust -f tests/load/locustfile_production.py \
     --users=50 \
     --spawn-rate=5
   ```

3. **Check system resources:**
   - Monitor CPU, memory
   - Check database connections

### Slow Requests

1. **Identify slow endpoints:**
   - Check console for "⚠️ SLOW" messages
   - Review summary report

2. **Optimize targets:**
   - Adjust response time targets in code
   - Focus on optimizing slow endpoints

## 📊 Performance Benchmarks

### Expected Results (500 users)

- **Read operations**: <50ms (p95)
- **Analytics**: <200ms (p95)
- **Write operations**: <100ms (p95)
- **Error rate**: <1%
- **Throughput**: >1000 req/s
- **CPU usage**: <80%
- **Memory usage**: <2GB

## 🔗 Related Files

- `backend/tests/load/locustfile_production.py` - Main test file
- `backend/tests/load/locustfile.py` - Basic load tests
- `backend/tests/load/README.md` - Basic load testing guide

## 📝 Notes

- **Test duration**: 10 minutes default
- **User distribution**: 60% production, 20% heavy, 20% write
- **Task weights**: Reflect real-world usage patterns
- **Validation**: All responses validated for correctness
- **Metrics**: System metrics collected if psutil available

---

**Status**: ✅ Production Ready
**Last Updated**: 2025-01-21

