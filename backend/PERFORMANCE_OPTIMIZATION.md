# Performance Optimization Documentation

Tài liệu về các tối ưu performance đã được triển khai.

## Overview

Hệ thống đã được tối ưu với:
- Redis caching
- Database query optimization
- Batch operations
- Async processing
- Prometheus metrics
- Performance monitoring

## Redis Caching

### Cache Manager

`app/services/cache.py` cung cấp:
- Connection pooling
- Automatic serialization/deserialization
- TTL management
- Pattern-based invalidation
- Cache statistics

### Usage

#### Basic Caching

```python
from app.services.cache import cache_manager

# Get from cache
value = await cache_manager.get("key")

# Set in cache
await cache_manager.set("key", value, ttl=300)

# Delete from cache
await cache_manager.delete("key")
```

#### Cache Decorator

```python
from app.services.cache import cached

@cached(ttl=300, key_prefix="predictions")
async def get_prediction():
    return compute_prediction()
```

#### Invalidation

```python
# Invalidate by pattern
await cache_manager.invalidate("predictions:*")

# Invalidate on function call
@cached(ttl=300, invalidate_on=["stats:*"])
async def update_stats():
    # This will invalidate all stats:* keys
    pass
```

### Cache Keys

Cache keys follow pattern: `{prefix}:{function_name}:{hash}`

Examples:
- `predictions:get_prediction:abc123`
- `stats:get_statistics:def456`

## Database Optimization

### Indexes

Additional indexes đã được thêm vào migration:

```sql
-- Composite indexes for common queries
CREATE INDEX idx_game_results_result_timestamp ON game_results(result, timestamp);
CREATE INDEX idx_game_results_shoe_timestamp ON game_results(shoe_number, timestamp);
```

### Query Optimization

#### Count Optimization

```python
from app.services.performance import QueryOptimizer

# Uses COUNT(*) instead of loading all records
count = QueryOptimizer.get_count_optimized(session, GameResult, filters={"result": "B"})
```

#### Bulk Operations

```python
# Bulk insert (1000 records at a time)
items = [{"result": "B", ...} for _ in range(5000)]
QueryOptimizer.bulk_insert(session, GameResult, items)

# Bulk update
QueryOptimizer.bulk_update(session, GameResult, items, update_key="id")
```

### Query Tracking

All database queries are tracked:

```python
from app.services.monitoring import track_query

with track_query("select"):
    results = session.query(GameResult).all()
```

## Batch Operations

### Batch Processing

```python
from app.services.performance import BatchProcessor

async def process_item(item):
    # Process item
    return processed_item

items = [1, 2, 3, ...]
results = await BatchProcessor.process_batch(
    items,
    process_item,
    batch_size=100,
    max_concurrent=10
)
```

## Async Processing

### Run Async

```python
from app.services.performance import run_async

# Run sync function asynchronously
result = await run_async(sync_function, arg1, arg2)

# Run async function
result = await run_async(async_function, arg1, arg2)
```

## Prometheus Metrics

### Available Metrics

- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request duration histogram
- `database_query_duration_seconds` - Database query duration
- `cache_hits_total` - Cache hits
- `cache_misses_total` - Cache misses
- `slow_queries_total` - Slow queries (>100ms)
- `active_connections` - Active connections gauge

### Accessing Metrics

```bash
# Prometheus format
curl http://localhost:8000/api/v2/metrics

# Dashboard JSON
curl http://localhost:8000/api/v2/metrics/dashboard
```

### Metrics Dashboard

Endpoint: `GET /api/v2/metrics/dashboard`

Returns:
```json
{
  "success": true,
  "data": {
    "cache": {
      "connected": true,
      "keys": 1000,
      "memory_usage": "10MB",
      "hits": 5000,
      "misses": 200
    },
    "database": {
      "connected": true,
      "pool_size": 5,
      "checked_out": 2
    },
    "websocket": {
      "active_connections": 10,
      "rooms": 3
    },
    "system": {
      "status": "healthy"
    }
  }
}
```

## Performance Monitoring

### Middleware

Performance middleware tự động track:
- Request duration
- Slow requests (>100ms)
- Response headers (`X-Response-Time`)

### Slow Query Detection

Queries > 100ms are automatically:
- Logged as warnings
- Tracked in Prometheus
- Counted in `slow_queries_total` metric

### Performance Logging

Slow requests và queries are logged:

```
WARNING: Slow request: GET /api/v2/predictions took 0.150s (threshold: 0.1s)
WARNING: Slow query: select took 0.200s (threshold: 0.1s)
```

## Best Practices

### Caching

1. **Cache expensive operations**: Predictions, statistics, roadmaps
2. **Use appropriate TTL**: 5 minutes for predictions, 1 hour for static data
3. **Invalidate on updates**: Clear cache when data changes
4. **Monitor cache hit rate**: Aim for >80% hit rate

### Database

1. **Use indexes**: Always index columns used in WHERE clauses
2. **Batch operations**: Use bulk insert/update for multiple records
3. **Limit queries**: Use pagination for large datasets
4. **Optimize counts**: Use COUNT(*) instead of loading all records

### Async Processing

1. **Use async for I/O**: Database, cache, external APIs
2. **Batch processing**: Process items in batches with concurrency control
3. **Avoid blocking**: Don't block event loop with CPU-intensive tasks

## Performance Targets

- **API Response Time**: < 100ms (95th percentile)
- **Database Queries**: < 50ms (95th percentile)
- **Cache Hit Rate**: > 80%
- **Slow Query Rate**: < 1%

## Monitoring

### Prometheus

Setup Prometheus to scrape metrics:

```yaml
scrape_configs:
  - job_name: 'baccarat-api'
    scrape_interval: 15s
    metrics_path: '/api/v2/metrics'
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana Dashboard

Create Grafana dashboard với:
- Request rate và latency
- Cache hit/miss rates
- Database query performance
- Slow query alerts

## Troubleshooting

### High Response Times

1. Check cache hit rate
2. Review slow query logs
3. Verify database indexes
4. Check connection pool usage

### Cache Issues

1. Verify Redis connection
2. Check cache TTL settings
3. Monitor memory usage
4. Review invalidation patterns

### Database Performance

1. Check query execution plans
2. Verify indexes are used
3. Review connection pool
4. Monitor slow queries

