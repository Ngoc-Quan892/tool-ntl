# Full Stack Integration Tests

Comprehensive integration test suite for full stack monitoring.

## 📋 Overview

This test suite verifies the complete request flow from API → Cache → Database → Monitoring, ensuring all monitoring components work correctly together.

## 🧪 Test Cases

### 1. `test_full_request_flow_with_monitoring`
- **Purpose**: End-to-end API test with monitoring
- **Duration**: ~10 seconds
- **Markers**: `@pytest.mark.slow`, `@pytest.mark.requires_monitoring`
- **Steps**:
  1. Make GET request to `/api/v2/game/1/results`
  2. Verify status code 200 and results not empty
  3. Wait 5 seconds for metrics propagation
  4. Query Prometheus for `http_requests_total`
  5. Verify metric exists and count increased
  6. Query `http_request_duration_seconds`
  7. Verify duration was recorded

### 2. `test_cache_monitoring`
- **Purpose**: Cache effectiveness test
- **Duration**: ~10 seconds
- **Markers**: `@pytest.mark.requires_cache`, `@pytest.mark.requires_monitoring`
- **Steps**:
  1. Make first request (cold cache)
  2. Record response time
  3. Make second identical request (warm cache)
  4. Record response time
  5. Calculate speedup (should be >10x)
  6. Query Prometheus for `cache_hit_rate`
  7. Verify cache hit rate > 0

### 3. `test_alert_triggering`
- **Purpose**: Alert system test
- **Duration**: ~15 seconds
- **Markers**: `@pytest.mark.requires_monitoring`
- **Steps**:
  1. Get current alerts baseline
  2. Trigger slow operations
  3. Wait 10 seconds for alerts
  4. Get new alerts
  5. Verify alert structure

### 4. `test_grafana_dashboard_accessible`
- **Purpose**: Dashboard availability test
- **Duration**: ~5 seconds
- **Markers**: `@pytest.mark.requires_monitoring`
- **Steps**:
  1. Check Grafana health endpoint
  2. Verify database status 'ok'
  3. Try to access dashboard (with auth handling)

### 5. `test_performance_under_monitoring`
- **Purpose**: Overhead measurement test
- **Duration**: ~30-60 seconds
- **Markers**: `@pytest.mark.slow`, `@pytest.mark.requires_monitoring`
- **Steps**:
  1. Run 100 requests without monitoring queries
  2. Record baseline time
  3. Run 100 requests with concurrent Prometheus queries
  4. Record monitoring time
  5. Calculate overhead (should be <10%)

### 6. `test_metrics_export_prometheus`
- **Purpose**: Prometheus format validation
- **Duration**: ~5 seconds
- **Markers**: `@pytest.mark.requires_monitoring`
- **Steps**:
  1. GET `/api/v2/metrics/prometheus`
  2. Verify `text/plain` content type
  3. Parse response text
  4. Verify HELP and TYPE declarations
  5. Verify metric values are numeric
  6. Check for required metrics

### 7. `test_health_check_endpoint`
- **Purpose**: Health check verification
- **Duration**: ~5 seconds
- **Steps**:
  1. GET `/api/v2/monitoring/health`
  2. Verify status code (200 or 503)
  3. Check response contains 'status' field
  4. Verify component statuses

## 🚀 Running Tests

### Prerequisites

1. **Start services:**
   ```bash
   docker compose -f deployment/docker-compose.prod.yml up -d prometheus grafana backend
   ```

2. **Wait for services to be ready:**
   - Prometheus: ~10 seconds
   - Grafana: ~30 seconds
   - Backend: ~60 seconds

### Run All Tests

```bash
# Run all integration tests
pytest tests/integration/test_full_stack.py -v -s

# Run with coverage
pytest tests/integration/test_full_stack.py -v --cov=app --cov-report=html
```

### Run Specific Tests

```bash
# Run only cache monitoring test
pytest tests/integration/test_full_stack.py::test_cache_monitoring -v

# Run only fast tests (exclude slow)
pytest tests/integration/test_full_stack.py -v -m "not slow"

# Run only monitoring tests
pytest tests/integration/test_full_stack.py -v -m "requires_monitoring"
```

### Environment Variables

Set these to override defaults:

```bash
export API_BASE_URL="http://localhost:8000"
export PROMETHEUS_URL="http://localhost:9090"
export GRAFANA_URL="http://localhost:3000"
```

## ✅ Success Criteria

All tests should pass with:

- ✅ All endpoints return expected status codes (200, 201, etc.)
- ✅ Cache speedup >10x for repeated queries
- ✅ Metrics appear in Prometheus within 10 seconds
- ✅ Alerts trigger when thresholds exceeded
- ✅ Monitoring overhead <10% of request time
- ✅ Grafana dashboard returns 200 OK
- ✅ Prometheus format is valid

## 📊 Expected Output

### Successful Test Run

```
===== Test: Full Request Flow with Monitoring =====
Making request to: http://localhost:8000/api/v2/game/1/results
Response status: 200
✅ Request successful, got 10 results
Waiting 5 seconds for metrics to propagate...
✅ Found 5 metric results in Prometheus
✅ Found 3 duration metrics

📊 Summary:
  - Request: ✅ Success
  - Metrics collected: ✅ 5 metrics
  - Duration tracked: ✅

==================================================
INTEGRATION TEST SUMMARY
==================================================
Total: 7 tests
Passed: 7 tests
Failed: 0 tests
Skipped: 0 tests
Duration: 85.23 seconds
==================================================
```

## 🔧 Troubleshooting

### Tests Skipped

If tests are skipped, check:

1. **Services not running:**
   ```bash
   docker compose -f deployment/docker-compose.prod.yml ps
   ```

2. **Services not accessible:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:9090/-/healthy
   curl http://localhost:3000/api/health
   ```

3. **Network issues:**
   - Ensure all services are in same Docker network
   - Check firewall rules

### Tests Failing

Common issues:

1. **Cache speedup <10x:**
   - Cache may not be working
   - Check Redis connection
   - Verify cache is enabled

2. **Metrics not appearing:**
   - Wait longer (metrics may take time to propagate)
   - Check Prometheus targets: http://localhost:9090/targets
   - Verify backend metrics endpoint: http://localhost:8000/api/v2/metrics/prometheus

3. **Monitoring overhead >10%:**
   - This may be normal for first run
   - Check Prometheus query performance
   - Reduce concurrent queries

## 📝 Test Fixtures

### `base_url`
- **Scope**: Session
- **Default**: `http://localhost:8000`
- **Override**: Set `API_BASE_URL` environment variable
- **Validation**: Checks `/health` endpoint before tests

### `prometheus_url`
- **Scope**: Session
- **Default**: `http://localhost:9090`
- **Override**: Set `PROMETHEUS_URL` environment variable
- **Validation**: Checks `/-/healthy` endpoint before tests

### `grafana_url`
- **Scope**: Session
- **Default**: `http://localhost:3000`
- **Override**: Set `GRAFANA_URL` environment variable
- **Validation**: Checks `/api/health` endpoint before tests

### `cleanup_cache`
- **Scope**: Function
- **Purpose**: Clears cache after each test
- **Action**: POST to `/api/v2/performance/clear-cache`

## 🏷️ Test Markers

- `@pytest.mark.integration`: All tests in this file
- `@pytest.mark.requires_monitoring`: Tests that need Prometheus/Grafana
- `@pytest.mark.requires_cache`: Tests that need Redis
- `@pytest.mark.slow`: Tests that take >30 seconds

### Usage

```bash
# Run only fast tests
pytest -m "not slow"

# Run only monitoring tests
pytest -m "requires_monitoring"

# Run cache tests
pytest -m "requires_cache"
```

## 📈 Performance Benchmarks

Expected performance:

- **Request latency**: <200ms (p95)
- **Cache speedup**: >10x
- **Monitoring overhead**: <10%
- **Metrics propagation**: <10 seconds
- **Alert trigger time**: <10 seconds

## 🔗 Related Files

- `backend/tests/integration/test_full_stack.py` - Test implementation
- `backend/pytest.ini` - Pytest configuration
- `deployment/scripts/verify_monitoring.ps1` - Monitoring verification script
- `deployment/VERIFY_MONITORING.md` - Monitoring verification guide

## 📝 Notes

- **Total test time**: ~2-3 minutes for all tests
- **Services required**: Backend, Prometheus, Grafana, Redis
- **Test independence**: All tests can run in any order
- **Cleanup**: Cache is cleared after each test
- **Timeouts**: 5-10 seconds per request, 30 seconds for slow operations

---

**Last Updated**: 2025-01-21
**Status**: ✅ Ready for Testing

