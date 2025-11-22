# Action Plan: Đạt 100% Success Rate cho Performance Benchmarks

Hướng dẫn chi tiết để đạt 100% success rate cho tất cả performance metrics.

## 📋 Tổng quan

Action plan này bao gồm 4 bước chính:

1. **Step A1**: Identify root cause (30 phút)
2. **Step A2**: Apply fixes (1-2 giờ)
3. **Step A3**: Re-benchmark (30 phút)
4. **Step A4**: Load test (1 giờ)

**Tổng thời gian ước tính: 3-4 giờ**

## 🚀 Cách sử dụng

### Chạy tự động toàn bộ action plan

```bash
python backend/benchmarks/action_plan_100_percent.py
```

### Chạy từng bước riêng lẻ

```bash
# Chỉ chạy debug (Step A1)
python backend/benchmarks/action_plan_100_percent.py --skip-fixes --skip-benchmark --skip-load-test

# Chỉ chạy fixes (Step A2)
python backend/benchmarks/action_plan_100_percent.py --skip-debug --skip-benchmark --skip-load-test

# Chỉ chạy re-benchmark (Step A3)
python backend/benchmarks/action_plan_100_percent.py --skip-debug --skip-fixes --skip-load-test
```

## 📝 Chi tiết từng bước

### Step A1: Identify Root Cause (30 phút)

**Mục tiêu**: Xác định bottleneck cụ thể cho các metric bị lỗi.

**Các debug functions được chạy**:

1. **`debug_cache_effectiveness()`**
   - Kiểm tra cache hit rate (>80% cho read operations)
   - Verify Redis connection
   - Check cache keys consistency
   - Measure cold vs warm cache performance

2. **`debug_query_performance()`**
   - Sử dụng EXPLAIN để phân tích query plan
   - Phát hiện full table scan
   - Kiểm tra index usage
   - Đếm số rows examined

3. **`debug_connection_pool()`**
   - Kiểm tra pool status (idle/active connections)
   - Đo connection wait time (<10ms)
   - Phát hiện pool saturation
   - Check overflow connections

**Expected Output**:
- Specific bottleneck identified
- Clear action items
- Detailed metrics và diagnostics

**Cách chạy thủ công**:

```python
from benchmarks.debug_failed_metrics import (
    debug_cache_effectiveness,
    debug_query_performance,
    debug_connection_pool,
)
from app.services.performance_optimizer import OptimizationStack
from app.models.database import db_manager

optimizer = OptimizationStack(...)
with db_manager.get_session() as session:
    debug_cache_effectiveness(optimizer, session)
    debug_query_performance(optimizer, session)
    debug_connection_pool(optimizer)
```

### Step A2: Apply Fixes (1-2 giờ)

**Mục tiêu**: Áp dụng các fixes dựa trên bottlenecks đã xác định.

#### Fix 1: Cache Not Effective

**Triệu chứng**:
- Cache hit rate < 80%
- Warm cache không nhanh hơn cold cache đáng kể
- Redis connection issues

**Fixes**:

```python
# 1. Fix cache key generation
# Đảm bảo cache keys consistent giữa set và get
cache_key = cache_manager._generate_key("pattern_stats", "get_pattern_statistics", pattern_type, days=days)

# 2. Increase TTL
# Trong .env hoặc config
REDIS_CACHE_TTL=600  # 10 minutes thay vì 5 minutes

# 3. Check Redis connection
redis_client = new_redis_client()
if redis_client:
    redis_client.ping()  # Should return True

# 4. Verify decorator is applied
@cached(ttl=300, key_prefix="pattern_stats")
async def get_pattern_statistics(...):
    ...
```

**SQL để kiểm tra Redis**:

```bash
# Test Redis connection
redis-cli ping

# Check cache keys
redis-cli KEYS "pattern_stats:*"

# Check TTL
redis-cli TTL "pattern_stats:get_pattern_statistics:all:7"
```

#### Fix 2: Query Too Slow

**Triệu chứng**:
- Query time > 200ms
- Full table scan detected
- High number of rows examined

**Fixes**:

**A. Thêm indexes**:

```sql
-- Index cho timestamp (quan trọng nhất)
CREATE INDEX IF NOT EXISTS idx_game_results_timestamp 
ON game_results(timestamp DESC);

-- Composite index cho shoe_number + timestamp
CREATE INDEX IF NOT EXISTS idx_game_results_shoe_timestamp 
ON game_results(shoe_number, timestamp DESC);

-- Composite index cho result + timestamp
CREATE INDEX IF NOT EXISTS idx_game_results_result_timestamp 
ON game_results(result, timestamp DESC);

-- Index cho pattern statistics (nếu có table riêng)
CREATE INDEX IF NOT EXISTS idx_pattern_type_created 
ON pattern_statistics(pattern_type, created_at DESC);
```

**B. Tạo Alembic migration**:

```python
# Tạo file migration mới
alembic revision -m "add_performance_indexes"

# Thêm vào upgrade()
def upgrade():
    op.create_index(
        'idx_game_results_timestamp',
        'game_results',
        ['timestamp'],
        unique=False
    )
    op.create_index(
        'idx_game_results_shoe_timestamp',
        'game_results',
        ['shoe_number', 'timestamp'],
        unique=False
    )
    op.create_index(
        'idx_game_results_result_timestamp',
        'game_results',
        ['result', 'timestamp'],
        unique=False
    )

# Chạy migration
alembic upgrade head
```

**C. Optimize query**:

```python
# Thêm LIMIT để giảm rows processed
query = text("""
    SELECT ...
    FROM game_results
    WHERE timestamp >= CURRENT_DATE - :days
    ORDER BY timestamp DESC
    LIMIT :limit  -- Thêm limit
""")

# Sử dụng covering index
# Index bao gồm tất cả columns cần thiết
CREATE INDEX idx_covering 
ON game_results(timestamp, result, shoe_number, hand_number);
```

#### Fix 3: Connection Pool Saturated

**Triệu chứng**:
- Connection wait time > 10ms
- All connections in use
- Overflow connections > 0

**Fixes**:

**A. Increase pool size**:

```python
# Trong .env
DB_POOL_SIZE=20  # Tăng từ 10
DB_MAX_OVERFLOW=15  # Tăng từ 10
```

**B. Optimize connection usage**:

```python
# ✅ ĐÚNG: Sử dụng context manager
with db_manager.get_session() as session:
    result = session.query(...).all()

# ❌ SAI: Không đóng connection
session = db_manager.get_session()
result = session.query(...).all()
# Connection không được đóng!

# ✅ ĐÚNG: Batch operations
batch_processor = optimizer.get_batch_processor()
batch_processor.batch_insert(session, Model, rows)
```

**C. Check for connection leaks**:

```python
# Monitor connection pool
from app.services.performance_optimizer import ConnectionPoolManager

pool_status = ConnectionPoolManager.get_pool_status(engine)
print(f"Active: {pool_status['checked_out']}")
print(f"Idle: {pool_status['checked_in']}")
print(f"Overflow: {pool_status['overflow']}")
```

### Step A3: Re-benchmark (30 phút)

**Mục tiêu**: Verify rằng tất cả fixes đã hoạt động.

**Chạy benchmark**:

```bash
# Chạy full benchmark
python backend/benchmarks/action_plan_100_percent.py --skip-debug --skip-fixes --skip-load-test

# Hoặc chạy trực tiếp
python -m benchmarks.performance_benchmark
```

**Expected Results**:

- ✅ Success rate: **100%** (8/8 metrics)
- ✅ Average improvement: **>9x**
- ✅ All metrics green

**Nếu vẫn có metrics failed**:

1. Xem lại Step A1 output
2. Apply thêm fixes từ Step A2
3. Re-run benchmark

### Step A4: Load Test (1 giờ)

**Mục tiêu**: Verify performance under real-world load.

**Chạy Locust load test**:

```bash
cd backend
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users=100 \
    --spawn-rate=10 \
    --run-time=5m \
    --headless \
    --html=load_test_report.html
```

**Monitor các metrics**:

1. **No errors**: Error rate = 0% under 100 concurrent users
2. **Response times stable**: 
   - p50 < 50ms
   - p95 < 200ms
   - p99 < 500ms
3. **Cache hit rate > 80%**: Check cache statistics
4. **Database connections < pool size**: No saturation

**Nếu có issues**:

- Scale up: Increase pool size, add more workers
- Optimize: Review slow endpoints, add more caching
- Monitor: Set up Prometheus/Grafana for continuous monitoring

## 🔍 Troubleshooting

### Cache không hoạt động

**Checklist**:
- [ ] Redis đang chạy: `redis-cli ping`
- [ ] REDIS_URL đúng trong .env
- [ ] Cache keys consistent giữa set và get
- [ ] TTL đủ dài (> 5 minutes)
- [ ] Decorator `@cached` được apply đúng

### Query vẫn chậm sau khi thêm index

**Checklist**:
- [ ] Index đã được tạo: `\d game_results` (PostgreSQL) hoặc `SHOW INDEXES FROM game_results` (MySQL)
- [ ] Query sử dụng index: Check EXPLAIN output
- [ ] Statistics updated: `ANALYZE game_results` (PostgreSQL) hoặc `ANALYZE TABLE game_results` (MySQL)
- [ ] Query được optimize: Remove unnecessary JOINs, add LIMIT

### Connection pool vẫn saturated

**Checklist**:
- [ ] Pool size đã tăng trong .env
- [ ] Connections được đóng đúng cách (context managers)
- [ ] Không có connection leaks
- [ ] Queries được optimize (nhanh hơn = ít connections hơn)

## 📊 Success Criteria

Action plan được coi là **thành công** khi:

1. ✅ **Benchmark success rate = 100%** (8/8 metrics pass)
2. ✅ **Average improvement > 9x**
3. ✅ **Load test: No errors** under 100 concurrent users
4. ✅ **Response times stable** (p95 < 200ms)
5. ✅ **Cache hit rate > 80%**

## 📈 Next Steps

Sau khi đạt 100% success rate:

1. **Continuous Monitoring**: Set up Prometheus/Grafana
2. **Alerting**: Configure alerts cho performance degradation
3. **Documentation**: Update API docs với performance characteristics
4. **Load Testing**: Regular load tests (weekly/monthly)
5. **Optimization**: Continuous improvement based on metrics

## 🔗 Related Files

- `backend/benchmarks/debug_failed_metrics.py` - Debug functions
- `backend/benchmarks/performance_benchmark.py` - Benchmark runner
- `backend/benchmarks/analyze_failed_metrics.py` - Analyze failed metrics
- `backend/tests/load/locustfile.py` - Load test scenarios

## 📝 Notes

- Action plan này có thể mất 3-4 giờ để hoàn thành
- Một số fixes có thể cần restart server
- Database migrations cần được test trên staging trước
- Load test nên chạy trên environment tương tự production

