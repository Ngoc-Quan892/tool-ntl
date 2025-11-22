# Quick Fix Guide: Fix Failed Metrics

Hướng dẫn nhanh để fix failed metrics trong 4 bước.

## 🚀 Quick Start

```bash
# Chạy toàn bộ quy trình tự động
python scripts/fix_failed_metrics.py
```

## 📋 4 Bước Quy Trình

### Step 1: Debug Failed Metrics (1 giờ)

**Mục tiêu**: Xác định root cause của failed metrics

```bash
# Chạy debug functions
python scripts/fix_failed_metrics.py --skip-fixes --skip-benchmark --skip-load-test
```

**Hoặc chạy thủ công**:

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

**Output**: 
- Cache effectiveness analysis
- Query performance analysis
- Connection pool status

### Step 2: Apply Fixes (2 giờ)

**Mục tiêu**: Áp dụng fixes dựa trên debug output

```bash
# Chạy với fixes (sẽ tự động chạy benchmark trước)
python scripts/fix_failed_metrics.py --skip-debug --skip-benchmark --skip-load-test
```

**Common Fixes**:

#### Cache Issues
```bash
# 1. Check Redis connection
redis-cli ping

# 2. Increase cache TTL
# Update .env: REDIS_CACHE_TTL=600

# 3. Verify cache keys
# Review cache key generation in code
```

#### Query Issues
```sql
-- Add missing indexes
CREATE INDEX IF NOT EXISTS idx_game_results_timestamp 
ON game_results(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_game_results_shoe_timestamp 
ON game_results(shoe_number, timestamp DESC);
```

#### Connection Pool Issues
```bash
# Increase pool size
# Update .env:
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=15
```

### Step 3: Re-benchmark (30 phút)

**Mục tiêu**: Verify fixes đã hoạt động (Target: 100% success rate)

```bash
# Chạy re-benchmark
python scripts/fix_failed_metrics.py --skip-debug --skip-fixes --skip-load-test
```

**Hoặc chạy trực tiếp**:

```bash
python -m benchmarks.performance_benchmark
```

**Expected Output**:
- Success rate: 100% (8/8 metrics)
- All metrics green ✅

### Step 4: Load Test (30 phút)

**Mục tiêu**: Verify performance under load

```bash
# Chạy load test
python scripts/fix_failed_metrics.py --skip-debug --skip-fixes --skip-benchmark
```

**Hoặc chạy thủ công**:

```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:8000 \
    --users=100 \
    --spawn-rate=10 \
    --run-time=5m \
    --headless \
    --html=load_test_report.html
```

**Monitor**:
- No errors under 100 concurrent users
- Response times stable (p95 < 200ms)
- Cache hit rate > 80%

## 🔄 Iterative Process

Nếu Step 3 không đạt 100%:

1. **Review Step 1 output** - Xem lại debug results
2. **Apply additional fixes** - Áp dụng thêm fixes từ Step 2
3. **Re-run Step 3** - Chạy lại benchmark

```bash
# Re-run với fixes đã apply
python scripts/fix_failed_metrics.py --skip-debug --skip-fixes --skip-load-test
```

## 📊 Success Criteria

Quy trình thành công khi:

- ✅ **Step 3**: Benchmark success rate = 100%
- ✅ **Step 4**: Load test passed (no errors, stable performance)

## 🛠️ Advanced Usage

### Skip Specific Steps

```bash
# Chỉ chạy debug
python scripts/fix_failed_metrics.py --skip-fixes --skip-benchmark --skip-load-test

# Chỉ chạy fixes
python scripts/fix_failed_metrics.py --skip-debug --skip-benchmark --skip-load-test

# Chỉ chạy benchmark
python scripts/fix_failed_metrics.py --skip-debug --skip-fixes --skip-load-test
```

### Manual Debug

Nếu cần debug thủ công:

```bash
# Chạy debug functions riêng lẻ
python benchmarks/debug_failed_metrics.py
```

## 📝 Notes

- **Total time**: ~4 hours (1h + 2h + 30m + 30m)
- **Iterations**: Có thể cần nhiều lần lặp lại Step 2-3
- **Documentation**: Ghi lại tất cả fixes đã apply

## 🔗 Related Files

- `scripts/fix_failed_metrics.py` - Main script
- `benchmarks/debug_failed_metrics.py` - Debug functions
- `benchmarks/performance_benchmark.py` - Benchmark runner
- `tests/load/locustfile.py` - Load test scenarios

