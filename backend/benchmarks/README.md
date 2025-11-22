# Performance Benchmark System

Hệ thống benchmark để đo lường hiệu suất trước và sau khi tối ưu hóa.

## 📋 Tổng quan

Hệ thống benchmark này đo lường các metrics quan trọng và so sánh với targets đã định nghĩa:

- **API Response Times**: Thời gian phản hồi của các endpoints
- **Cache Performance**: Cache hit rate
- **Throughput**: Số requests per second
- **Resource Usage**: Database connections, memory usage
- **Query Performance**: Average query time, slow query rate

## 🎯 Benchmark Targets

| Metric | Baseline | Target | Improvement |
|--------|----------|--------|-------------|
| `get_game_results` | 250ms | 25ms | 10x |
| `get_pattern_stats` | 800ms | 80ms | 10x |
| `cache_hit_rate` | 0% | 85% | ∞ |
| `requests_per_second` | 100 | 1000 | 10x |
| `database_connections` | 50 | 10 | 5x reduction |
| `avg_query_time_ms` | 150ms | 15ms | 10x |
| `slow_query_rate` | 15% | 1% | 15x reduction |
| `memory_usage_mb` | 500MB | 200MB | 2.5x reduction |

## 🚀 Cách sử dụng

### 1. Chạy tất cả benchmarks

```bash
# Sử dụng script CLI
python scripts/run_benchmark.py --all

# Hoặc chạy trực tiếp
python benchmarks/performance_benchmark.py
```

### 2. Chạy benchmark cho một metric cụ thể

```bash
python scripts/run_benchmark.py --metric get_game_results
```

### 3. Chạy với custom base URL

```bash
python scripts/run_benchmark.py --all --base-url http://localhost:8000
```

### 4. Lưu report vào file

```bash
python scripts/run_benchmark.py --all --output benchmark_report.json
```

## 📊 Output Format

### Console Output

```
================================================================================
PERFORMANCE BENCHMARK REPORT
================================================================================
Timestamp: 2024-01-01T12:00:00.000000

Summary:
  Total Metrics: 8
  Metrics Meeting Target: 6
  Success Rate: 75.0%
  Average Improvement: 8.5x

Detailed Results:
--------------------------------------------------------------------------------
✅ get_game_results
    Measured: 23.45
    Baseline: 250.00
    Target: 25.00
    Improvement: 10.66x
    Description: Get game results endpoint

❌ get_pattern_stats
    Measured: 95.20
    Baseline: 800.00
    Target: 80.00
    Improvement: 8.40x
    Description: Get pattern statistics endpoint
...
```

### JSON Report

```json
{
  "timestamp": "2024-01-01T12:00:00.000000",
  "summary": {
    "total_metrics": 8,
    "metrics_meeting_target": 6,
    "metrics_below_target": 2,
    "success_rate": 75.0,
    "average_improvement": 8.5
  },
  "results": [
    {
      "metric_name": "get_game_results",
      "measured_value": 23.45,
      "baseline": 250.0,
      "target": 25.0,
      "improvement_ratio": 10.66,
      "meets_target": true,
      "description": "Get game results endpoint"
    }
  ]
}
```

## 🔧 Tích hợp vào Code

### Sử dụng trong Python code

```python
from benchmarks.performance_benchmark import PerformanceBenchmark
from app.services.performance_optimizer import OptimizationStack

# Initialize optimizer
optimizer = OptimizationStack(...)

# Create benchmark runner
benchmark = PerformanceBenchmark(optimizer=optimizer)

# Run all benchmarks
report = await benchmark.run_all_benchmarks()

# Access results
for result in report.results:
    print(f"{result.metric_name}: {result.measured_value}")
    print(f"Meets target: {result.meets_target}")
    print(f"Improvement: {result.improvement_ratio}x")
```

### Chạy single benchmark

```python
# Run specific metric
result = await benchmark.run_benchmark("get_game_results")

print(f"Measured: {result.measured_value}ms")
print(f"Target: {result.target}ms")
print(f"Meets target: {result.meets_target}")
```

## 📈 Metrics được đo lường

### 1. API Response Times

- **get_game_results**: GET `/api/v2/game/{game_id}/results`
- **get_pattern_stats**: GET `/api/v2/analysis/pattern`

### 2. Cache Performance

- **cache_hit_rate**: Tỷ lệ cache hits (0.0 - 1.0)

### 3. Throughput

- **requests_per_second**: Số requests xử lý được mỗi giây

### 4. Resource Usage

- **database_connections**: Số kết nối database đang active
- **memory_usage_mb**: Memory usage của process (MB)

### 5. Query Performance

- **avg_query_time_ms**: Thời gian trung bình của queries (ms)
- **slow_query_rate**: Tỷ lệ slow queries (>100ms)

## 🎛️ Configuration

### Thêm metric mới

Chỉnh sửa `TARGETS` trong `performance_benchmark.py`:

```python
TARGETS = {
    "new_metric": {
        "baseline": 100,
        "target": 10,
        "improvement": "10x",
        "description": "New metric description",
    },
}
```

### Thêm measurement method

Thêm method trong `PerformanceBenchmark` class:

```python
async def measure_new_metric(self) -> float:
    """Measure new metric."""
    # Your measurement logic
    return measured_value
```

Và update `run_benchmark()` method để handle metric mới:

```python
elif metric_name == "new_metric":
    measured_value = await self.measure_new_metric()
```

## 📝 Best Practices

1. **Warm up cache**: Chạy một số requests trước khi benchmark để cache được warm up
2. **Multiple iterations**: Mỗi metric được đo nhiều lần và lấy average
3. **Concurrent testing**: Throughput test sử dụng concurrent requests
4. **Error handling**: Benchmark tự động handle errors và tiếp tục
5. **Report saving**: Luôn lưu report để so sánh theo thời gian

## 🔍 Troubleshooting

### API không accessible

```bash
# Kiểm tra server đang chạy
curl http://localhost:8000/health

# Sử dụng custom base URL
python scripts/run_benchmark.py --all --base-url http://your-server:8000
```

### Optimizer không available

Benchmark vẫn chạy được nhưng một số metrics (cache, database) sẽ không đo được. Đảm bảo:
- Database connection được setup
- Redis connection được setup (nếu dùng cache)

### Memory measurement không hoạt động

Cần install `psutil`:
```bash
pip install psutil
```

## 📚 Related Documentation

- [Performance Optimization Guide](../docs/PERFORMANCE_OPTIMIZATION_GUIDE.md)
- [Monitoring Documentation](../deployment/MONITORING.md)
- [Load Testing](../tests/load/README.md)

