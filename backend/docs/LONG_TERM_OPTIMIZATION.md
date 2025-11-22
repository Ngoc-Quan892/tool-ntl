# Long-term Optimization Strategies

Kế hoạch tối ưu hóa dài hạn cho production system, chia thành các giai đoạn rõ ràng.

## 📅 Timeline Overview

- **Week 1-2**: Stabilization - Monitor và fix issues
- **Week 3-4**: Advanced Optimization - Query, cache, database optimization
- **Month 2+**: Scale Preparation - Horizontal scaling, advanced features, cost optimization

---

## Week 1-2: Stabilization

**Focus**: Monitor và fix issues

### Daily Tasks

#### 1. Review Daily Metrics

**Checklist mỗi ngày**:

```bash
# Review metrics dashboard
curl http://localhost:8000/api/monitoring/dashboard | jq

# Check key metrics
- API response times (p50, p95, p99)
- Cache hit rate
- Database query times
- Connection pool utilization
- Error rates
```

**Script tự động**:

```bash
# Generate daily metrics report
python scripts/daily_metrics_report.py
```

**Expected metrics**:
- Response time p95 < 200ms
- Cache hit rate > 80%
- Query time avg < 50ms
- Connection pool utilization < 70%
- Error rate < 0.1%

#### 2. Investigate Alerts

**Alert investigation process**:

1. **Check alert history**:
```bash
# View recent alerts
curl http://localhost:8000/api/monitoring/alerts?hours=24
```

2. **Analyze root cause**:
   - Review logs for the time period
   - Check related metrics
   - Identify patterns

3. **Document findings**:
   - Root cause
   - Impact
   - Resolution
   - Prevention measures

**Alert response checklist**:
- [ ] Alert acknowledged
- [ ] Root cause identified
- [ ] Fix applied
- [ ] Verified resolution
- [ ] Documentation updated

#### 3. Fine-tune Cache TTLs

**Cache TTL optimization**:

```python
# Current TTLs (baseline)
CACHE_TTL = {
    "game_results": 300,      # 5 minutes
    "pattern_stats": 600,      # 10 minutes
    "user_sessions": 1800,     # 30 minutes
    "predictions": 60,         # 1 minute
}

# Optimization strategy
# 1. Monitor cache hit rate per key pattern
# 2. Adjust TTL based on:
#    - Access frequency
#    - Data freshness requirements
#    - Memory constraints
```

**TTL tuning script**:

```bash
# Analyze cache patterns
python scripts/analyze_cache_patterns.py

# Adjust TTLs based on analysis
# Update in .env or config
REDIS_CACHE_TTL=600
```

**TTL adjustment guidelines**:
- High hit rate (>90%): Increase TTL
- Low hit rate (<70%): Decrease TTL or review keys
- Memory pressure: Decrease TTL for large objects

#### 4. Adjust Connection Pool Sizes

**Connection pool monitoring**:

```python
# Current settings
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 10

# Monitor utilization
# - If consistently >80%: Increase pool size
# - If consistently <30%: Decrease pool size
# - If frequent timeouts: Increase max_overflow
```

**Pool size adjustment**:

```bash
# Monitor connection pool
python scripts/monitor_connection_pool.py

# Adjust based on metrics
# Update in .env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=15
```

**Adjustment criteria**:
- Utilization >80% for >1 hour: Increase by 50%
- Utilization <30% for >1 day: Decrease by 25%
- Timeouts >10/day: Increase max_overflow

### Weekly Review

**Week 1-2 summary report**:

```bash
# Generate weekly report
python scripts/weekly_optimization_report.py --week 1
```

**Report includes**:
- Metrics trends
- Alert summary
- Performance improvements
- Issues resolved
- Next week priorities

---

## Week 3-4: Advanced Optimization

**Focus**: Query optimization, cache enhancement, database optimization

### 1. Query Optimization Round 2

#### Analyze Slow Query Logs

**Enable slow query logging**:

```sql
-- PostgreSQL
ALTER DATABASE baccarat SET log_min_duration_statement = 100;  -- Log queries >100ms

-- MySQL
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.1;  -- Log queries >100ms
```

**Analyze slow queries**:

```bash
# Extract slow queries
python scripts/analyze_slow_queries.py --hours 24

# Generate optimization recommendations
python scripts/query_optimization_recommendations.py
```

**Query analysis checklist**:
- [ ] Identify top 10 slowest queries
- [ ] Run EXPLAIN ANALYZE for each
- [ ] Identify missing indexes
- [ ] Review query patterns
- [ ] Document optimization plan

#### Add More Specific Indexes

**Index analysis**:

```sql
-- Find missing indexes
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
    AND n_distinct > 100
    AND correlation < 0.1
ORDER BY n_distinct DESC;
```

**Common index patterns**:

```sql
-- Composite indexes for common queries
CREATE INDEX idx_game_results_shoe_timestamp_result 
ON game_results(shoe_number, timestamp DESC, result);

-- Covering index
CREATE INDEX idx_game_results_covering 
ON game_results(timestamp, result, shoe_number, hand_number)
INCLUDE (prediction, true_count, edge);

-- Partial index for active data
CREATE INDEX idx_game_results_recent 
ON game_results(timestamp DESC)
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days';
```

**Index creation script**:

```bash
# Generate index recommendations
python scripts/generate_index_recommendations.py

# Create indexes via migration
alembic revision -m "add_advanced_indexes"
```

#### Query Result Caching

**Implement result caching**:

```python
# Cache expensive query results
@cached(ttl=600, key_prefix="query_results")
async def get_expensive_query_result(params):
    # Expensive query
    result = await execute_expensive_query(params)
    return result

# Cache query plans
@cached(ttl=3600, key_prefix="query_plans")
def get_query_plan(query_hash):
    # Cache EXPLAIN results
    return explain_query(query)
```

### 2. Cache Strategy Enhancement

#### Implement Cache Warming on Deploy

**Cache warming script**:

```python
# scripts/warm_cache_on_deploy.py
async def warm_cache_comprehensive(optimizer):
    """Warm up all critical caches."""
    
    # 1. Popular game results
    popular_games = get_popular_games(limit=50)
    for game_id in popular_games:
        await warm_game_results(game_id)
    
    # 2. Pattern statistics
    patterns = ["B", "P", "T", "all"]
    for pattern in patterns:
        await warm_pattern_stats(pattern)
    
    # 3. User sessions (if applicable)
    active_sessions = get_active_sessions()
    for session in active_sessions:
        await warm_user_session(session)
```

**Deploy integration**:

```bash
# In deployment script
python scripts/backup_utilities.py warm-cache
```

#### Add Predictive Pre-caching

**Predictive caching**:

```python
# Predict likely next requests
async def predictive_cache_warming():
    """Pre-cache likely next requests."""
    
    # 1. Based on time patterns
    current_hour = datetime.now().hour
    if current_hour in [20, 21, 22]:  # Peak hours
        await warm_peak_hour_data()
    
    # 2. Based on user patterns
    popular_patterns = get_popular_patterns()
    for pattern in popular_patterns:
        await pre_cache_pattern(pattern)
    
    # 3. Based on sequential access
    recent_games = get_recent_games(limit=10)
    for game in recent_games:
        await pre_cache_next_game(game.id + 1)
```

#### Optimize Cache Eviction Policy

**Eviction policy configuration**:

```python
# Redis eviction policy
# Options: allkeys-lru, allkeys-lfu, volatile-lru, volatile-lfu

# For our use case: allkeys-lru (Least Recently Used)
# - Evicts least recently used keys when memory limit reached
# - Good for mixed access patterns

# Configuration
REDIS_MAXMEMORY = "2gb"
REDIS_MAXMEMORY_POLICY = "allkeys-lru"
```

**Cache eviction monitoring**:

```bash
# Monitor evictions
python scripts/monitor_cache_evictions.py

# Adjust policy if needed
# - High eviction rate: Increase memory or adjust TTLs
# - Low hit rate: Consider allkeys-lfu (Least Frequently Used)
```

### 3. Database Optimization

#### Analyze Table Statistics

**Table statistics analysis**:

```sql
-- PostgreSQL: Analyze tables
ANALYZE game_results;
ANALYZE pattern_statistics;

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

**Statistics analysis script**:

```bash
# Generate table statistics report
python scripts/analyze_table_statistics.py
```

#### Optimize Table Structure

**Table optimization**:

```sql
-- 1. Vacuum and analyze
VACUUM ANALYZE game_results;

-- 2. Reindex if needed
REINDEX TABLE game_results;

-- 3. Check for bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public';
```

#### Consider Read Replicas

**Read replica setup** (for heavy load):

```python
# Database configuration with read replicas
DATABASE_URL = "postgresql://user:pass@master:5432/db"
DATABASE_READ_REPLICA_URL = "postgresql://user:pass@replica:5432/db"

# Use read replica for read-only queries
def get_read_session():
    if is_read_query():
        return get_session_from_replica()
    return get_session_from_master()
```

**Read replica benefits**:
- Distribute read load
- Reduce master database load
- Improve query performance
- Better scalability

---

## Month 2+: Scale Preparation

**Focus**: Horizontal scaling, advanced features, cost optimization

### 1. Horizontal Scaling

#### Load Balancer Setup

**Load balancer configuration**:

```nginx
# nginx.conf
upstream baccarat_backend {
    least_conn;  # Use least connections algorithm
    server app1:8000;
    server app2:8000;
    server app3:8000;
}

server {
    listen 80;
    server_name api.example.com;
    
    location / {
        proxy_pass http://baccarat_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://baccarat_backend/health;
    }
}
```

**Load balancer features**:
- Health checks
- Session affinity (if needed)
- SSL termination
- Rate limiting

#### Session Management

**Stateless session management**:

```python
# Use JWT tokens instead of server-side sessions
from jose import jwt

def create_session_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# Store minimal state in token
# All session data in database/cache
```

**Session synchronization** (if needed):

```python
# Use Redis for shared session storage
def get_session(session_id: str):
    return cache_manager.get(f"session:{session_id}")

def set_session(session_id: str, data: dict):
    cache_manager.set(f"session:{session_id}", data, ttl=3600)
```

#### Cache Synchronization

**Distributed cache**:

```python
# Use Redis as shared cache
# All instances share the same Redis instance

# Cache invalidation across instances
def invalidate_cache_pattern(pattern: str):
    # Invalidate in local cache
    cache_manager.delete_pattern(pattern)
    
    # Publish invalidation event to other instances
    redis_client.publish("cache_invalidation", pattern)
```

**Cache synchronization strategy**:
- Shared Redis instance
- Cache invalidation events
- Consistent cache keys across instances

### 2. Advanced Features

#### Circuit Breaker Pattern

**Circuit breaker implementation**:

```python
from app.services.circuit_breaker import CircuitBreaker

# Protect external dependencies
@CircuitBreaker(failure_threshold=5, recovery_timeout=60)
async def call_external_api():
    # External API call
    response = await httpx.get("https://external-api.com")
    return response.json()

# Automatic fallback on failure
```

**Circuit breaker benefits**:
- Prevent cascade failures
- Fast failure detection
- Automatic recovery
- Graceful degradation

#### Rate Limiting Per User

**User-based rate limiting**:

```python
from app.middleware.rate_limit import RateLimiter

# Per-user rate limits
rate_limiter = RateLimiter(
    requests_per_minute=100,
    requests_per_hour=1000,
    key_func=lambda request: request.state.user_id
)

@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    if not await rate_limiter.is_allowed(request):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"}
        )
    return await call_next(request)
```

#### Request Prioritization

**Priority queue**:

```python
# Priority levels
PRIORITY_HIGH = 1    # Real-time predictions
PRIORITY_MEDIUM = 2  # Statistics
PRIORITY_LOW = 3     # Historical data

async def process_request(request, priority: int):
    # Add to priority queue
    await priority_queue.put((priority, request))
    
    # Process high priority first
    while True:
        priority, request = await priority_queue.get()
        await handle_request(request)
```

#### Adaptive Timeout

**Dynamic timeout adjustment**:

```python
# Adjust timeout based on current load
def get_adaptive_timeout(base_timeout: float) -> float:
    current_load = get_current_load()
    
    if current_load > 0.8:
        # High load: reduce timeout
        return base_timeout * 0.7
    elif current_load < 0.3:
        # Low load: increase timeout
        return base_timeout * 1.5
    else:
        return base_timeout
```

### 3. Cost Optimization

#### Right-size Connection Pools

**Connection pool optimization**:

```python
# Calculate optimal pool size
def calculate_optimal_pool_size(
    avg_queries_per_second: float,
    avg_query_time_ms: float,
    target_utilization: float = 0.7
) -> int:
    """
    Calculate optimal connection pool size.
    
    Formula:
    pool_size = (queries_per_second * query_time_seconds) / target_utilization
    """
    query_time_seconds = avg_query_time_ms / 1000
    pool_size = (avg_queries_per_second * query_time_seconds) / target_utilization
    return max(int(pool_size), 5)  # Minimum 5 connections

# Example
optimal_size = calculate_optimal_pool_size(
    avg_queries_per_second=50,
    avg_query_time_ms=100,
    target_utilization=0.7
)
# Result: ~8 connections
```

#### Optimize Cache Memory Usage

**Cache memory optimization**:

```python
# Monitor cache memory usage
def optimize_cache_memory():
    cache_stats = cache_manager.get_stats()
    memory_usage = cache_stats.get("memory_mb", 0)
    
    if memory_usage > 500:  # 500MB limit
        # Reduce TTLs for less critical data
        adjust_ttls_for_memory_pressure()
        
        # Evict old data
        evict_old_cache_entries()
        
        # Compress large values
        compress_cache_values()
```

**Cache compression**:

```python
import gzip
import json

def compress_cache_value(value: Any) -> bytes:
    """Compress large cache values."""
    json_str = json.dumps(value)
    return gzip.compress(json_str.encode())

def decompress_cache_value(compressed: bytes) -> Any:
    """Decompress cache values."""
    json_str = gzip.decompress(compressed).decode()
    return json.loads(json_str)
```

#### Review and Cleanup Unused Indexes

**Index cleanup**:

```sql
-- Find unused indexes
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Drop unused indexes
DROP INDEX IF EXISTS unused_index_name;
```

**Index cleanup script**:

```bash
# Generate unused index report
python scripts/find_unused_indexes.py

# Review and drop unused indexes
# (Be careful - verify they're truly unused)
```

---

## 📊 Progress Tracking

### Metrics Dashboard

Track optimization progress:

```bash
# Weekly optimization metrics
python scripts/weekly_optimization_metrics.py
```

**Key metrics to track**:
- Response time improvement
- Cache hit rate improvement
- Query time reduction
- Cost reduction
- Error rate reduction

### Monthly Review

**Monthly optimization review**:

```bash
# Generate monthly report
python scripts/monthly_optimization_report.py
```

**Review checklist**:
- [ ] Goals achieved
- [ ] Metrics improved
- [ ] Issues resolved
- [ ] New optimizations identified
- [ ] Next month priorities set

---

## 🔗 Related Files

- `scripts/daily_metrics_report.py` - Daily metrics report
- `scripts/weekly_optimization_report.py` - Weekly optimization report
- `scripts/analyze_slow_queries.py` - Slow query analysis
- `scripts/query_optimization_recommendations.py` - Query optimization recommendations
- `scripts/monitor_connection_pool.py` - Connection pool monitoring
- `scripts/analyze_cache_patterns.py` - Cache pattern analysis
- `scripts/generate_index_recommendations.py` - Index recommendations
- `scripts/find_unused_indexes.py` - Unused index finder

