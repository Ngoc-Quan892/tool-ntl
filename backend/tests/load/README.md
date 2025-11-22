# Load Testing với Locust

Module này chứa các load tests sử dụng [Locust](https://locust.io/) để test hiệu năng của Baccarat Predictor API.

## Cài đặt

```bash
# Cài đặt Locust
pip install locust

# Hoặc thêm vào requirements-dev.txt
echo "locust>=2.0.0" >> requirements-dev.txt
pip install -r requirements-dev.txt
```

## Chạy Load Tests

### 1. Chạy với Web UI (Recommended)

```bash
# Khởi động server trước
cd backend
uvicorn app.main:app --reload

# Trong terminal khác, chạy Locust
cd backend
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

Sau đó mở browser tại: http://localhost:8089

### 2. Chạy Headless (Không có UI)

```bash
# 100 users, spawn rate 10 users/second, chạy 5 phút
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --html=load_test_report.html
```

### 3. Chạy với Custom Parameters

```bash
# 500 users, spawn rate 20 users/second, chạy 10 phút
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users 500 \
    --spawn-rate 20 \
    --run-time 10m \
    --headless
```

## Performance Targets

### 100 Users
- **95th percentile response time**: < 200ms
- **Average response time**: < 100ms
- **Failure rate**: < 0.1%

### 500 Users
- **95th percentile response time**: < 500ms
- **Average response time**: < 250ms
- **Failure rate**: < 0.5%

### 1000 Users
- **System stability**: No crashes
- **95th percentile response time**: < 1000ms
- **Failure rate**: < 1%

## Test Scenarios

### BaccaratUser (Default)
- **Wait time**: 1-3 seconds between requests
- **Tasks**:
  - `get_game_results` (60%): GET `/api/v2/game/{game_id}/results`
  - `get_pattern_statistics` (40%): GET `/api/v2/game/statistics/pattern`
  - `play_hand` (20%): POST `/api/v2/hands/play`
  - `get_hand_history` (20%): GET `/api/v2/hands/history`
  - `get_statistics` (20%): GET `/api/v2/analysis/statistics`

### HeavyUser
- **Wait time**: 0.5-1.5 seconds (faster)
- More frequent requests to game results

### LightUser
- **Wait time**: 3-6 seconds (slower)
- Less frequent requests

## Endpoints Tested

### Read Operations (Cached)
1. **GET `/api/v2/game/{game_id}/results`**
   - Target: < 50ms
   - Cache: L1 (memory) + L2 (Redis), 60s TTL
   - Most popular games (1-10) accessed 70% of the time

2. **GET `/api/v2/game/statistics/pattern`**
   - Target: < 200ms
   - Cache: Aggressive (5+ minutes)
   - Patterns: B, P, T, all

3. **GET `/api/v2/hands/history`**
   - Target: < 100ms
   - Paginated results

4. **GET `/api/v2/analysis/statistics`**
   - Target: < 150ms
   - General statistics

### Write Operations (Cache Invalidation)
1. **POST `/api/v2/hands/play`**
   - Target: < 100ms
   - Creates new game result
   - Should invalidate related caches

## Monitoring

### Real-time Metrics
- Request rate (requests/second)
- Response times (min, max, average, percentiles)
- Failure rate
- Number of users

### Response Time Percentiles
- 50th percentile (median)
- 75th percentile
- 95th percentile (target metric)
- 99th percentile

## Tips

1. **Warm up cache first**: Run a small load test (10 users) for 1 minute before the main test
2. **Monitor server resources**: Watch CPU, memory, and database connections
3. **Check cache hit rates**: Verify that caching is working effectively
4. **Database connection pool**: Ensure pool size is sufficient for concurrent users
5. **Redis performance**: Monitor Redis memory and connection count

## Troubleshooting

### High Response Times
- Check database query performance
- Verify cache is working (check hit rates)
- Monitor database connection pool
- Check for slow queries

### High Failure Rate
- Check server logs for errors
- Verify database connections
- Check Redis availability
- Monitor server resources (CPU, memory)

### Connection Errors
- Increase database connection pool size
- Check Redis max connections
- Verify network connectivity
- Check firewall rules

## Example Output

```
Name                                                          # reqs      # fails     Avg     Min     Max    Median   req/s
--------------------------------------------------------------------------------------------------------------------------------------------
GET /api/v2/game/[game_id]/results                          5000        0(0.00%)    45      12      234    42       83.33
GET /api/v2/game/statistics/pattern                          2000        0(0.00%)    180     89      456    175      33.33
POST /api/v2/hands/play                                      1000        2(0.20%)    95      45      234    89       16.67
GET /api/v2/hands/history                                    1000        0(0.00%)    78      23      189    75       16.67
GET /api/v2/analysis/statistics                             1000        0(0.00%)    120     56      298    115      16.67
--------------------------------------------------------------------------------------------------------------------------------------------
Total                                                        10000       2(0.02%)    89      12      456    85       166.67
```

## CI/CD Integration

Có thể tích hợp vào CI/CD pipeline:

```yaml
# .github/workflows/load-test.yml
- name: Run load test
  run: |
    locust -f tests/load/locustfile.py \
      --host=http://localhost:8000 \
      --users 100 \
      --spawn-rate 10 \
      --run-time 2m \
      --headless \
      --html=load_test_report.html \
      --csv=load_test_results
```

## References

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://docs.locust.io/en/stable/writing-a-locustfile.html)

