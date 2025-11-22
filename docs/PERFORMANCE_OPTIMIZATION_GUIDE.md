# Performance Optimization Guide

Hướng dẫn tối ưu performance cho Baccarat Predictor Pro.

## 📋 Table of Contents

- [Frontend Optimization](#frontend-optimization)
- [Backend Optimization](#backend-optimization)
- [Database Optimization](#database-optimization)
- [Caching Strategy](#caching-strategy)
- [CDN Setup](#cdn-setup)
- [Monitoring](#monitoring)

## 🎨 Frontend Optimization

### Bundle Optimization

Đã được cấu hình trong `vite.config.ts`:

- **Code Splitting**: Manual chunks cho vendors
- **Tree Shaking**: Automatic với Vite
- **Minification**: Terser với drop console
- **Source Maps**: Disabled trong production

### Optimization Features

1. **Manual Chunks**:
   - React vendor chunk
   - UI library chunk (Radix UI)
   - Chart library chunk (Recharts)
   - State management chunk (Zustand, React Query)
   - Utils chunk

2. **Asset Optimization**:
   - Optimized file names với hashes
   - Separate directories cho assets
   - Chunk size warnings

### Best Practices

```typescript
// Lazy load components
const HeavyComponent = React.lazy(() => import('./HeavyComponent'));

// Use React.memo for expensive components
export const ExpensiveComponent = React.memo(({ data }) => {
  // Component code
});

// Use useMemo for expensive calculations
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data);
}, [data]);
```

## ⚙️ Backend Optimization

### Query Optimization

1. **Use Indexes**: Đã thêm composite indexes
2. **Limit Results**: Always use pagination
3. **Selective Loading**: Only load needed fields
4. **Batch Operations**: Use bulk insert/update

### Example Optimized Query

```python
from app.services.performance import QueryOptimizer

# Optimized count
count = QueryOptimizer.get_count_optimized(
    session, 
    GameResult, 
    filters={"result": "B"}
)

# Optimized query với pagination
query = QueryOptimizer.optimize_query(
    session.query(GameResult),
    limit=100,
    offset=0
)
```

### Async Processing

```python
from app.services.performance import BatchProcessor

# Batch process với concurrency control
results = await BatchProcessor.process_batch(
    items,
    processor_function,
    batch_size=100,
    max_concurrent=10
)
```

## 🗄️ Database Optimization

### Indexes

Đã thêm các indexes tối ưu:

1. **Composite Indexes**:
   - `idx_game_results_shoe_result`: For filtering by shoe and result
   - `idx_game_results_shoe_timestamp`: For time-range queries
   - `idx_game_results_result_timestamp`: For result-based queries

2. **Partial Indexes**:
   - `idx_game_results_true_count`: Only indexes non-null values
   - `idx_game_results_edge`: Only indexes non-null values

3. **Descending Indexes**:
   - `idx_game_results_timestamp_desc`: For recent results queries

### Query Patterns

**Optimized:**
```python
# Uses index
results = session.query(GameResult).filter(
    GameResult.shoe_number == shoe_id,
    GameResult.result == "B"
).all()

# Uses composite index
results = session.query(GameResult).filter(
    GameResult.shoe_number == shoe_id
).order_by(GameResult.timestamp.desc()).limit(100).all()
```

**Not Optimized:**
```python
# Full table scan
results = session.query(GameResult).all()

# No index usage
results = session.query(GameResult).filter(
    GameResult.prediction['confidence'] > 0.7
).all()
```

### Connection Pooling

Đã cấu hình trong `app/models/database.py`:

```python
# Optimized pool settings
pool_size=10
max_overflow=20
pool_timeout=30
pool_recycle=3600
```

## 💾 Caching Strategy

### Cache Layers

1. **Redis Cache**: For API responses
2. **Browser Cache**: For static assets
3. **CDN Cache**: For global distribution

### Cache Patterns

**API Response Caching:**
```python
from app.services.cache import cached

@cached(ttl=300, key_prefix="predictions")
async def get_prediction(shoe_id: str):
    return compute_prediction(shoe_id)
```

**Cache Invalidation:**
```python
from app.services.cache import cache_manager

# Invalidate on update
await cache_manager.invalidate("predictions:*")
```

### Cache TTL Strategy

- **Predictions**: 5 minutes (frequently changing)
- **Statistics**: 1 hour (less frequently changing)
- **Static Data**: 24 hours (rarely changing)

## 🌐 CDN Setup

### Configuration

CDN configuration trong `deployment/nginx/cdn.conf`:

1. **Static Assets**:
   - Cache-Control headers
   - Long TTL (1 year) cho immutable assets
   - Short TTL cho HTML

2. **Compression**:
   - Gzip cho text assets
   - Brotli support
   - Pre-compressed files

3. **CORS Headers**: For cross-origin requests

### CDN Providers

**Recommended:**
- **Cloudflare**: Free tier available
- **AWS CloudFront**: Integrated với AWS
- **Fastly**: High performance

### Setup Steps

1. **Configure CDN**:
   - Point to your domain
   - Enable caching
   - Configure headers

2. **Update Nginx**:
   - Include `cdn.conf`
   - Configure cache headers
   - Enable compression

3. **Test CDN**:
   - Verify cache headers
   - Check compression
   - Monitor performance

## 📊 Monitoring

### Performance Metrics

Monitor các metrics sau:

1. **API Response Time**: < 100ms (95th percentile)
2. **Database Query Time**: < 50ms (95th percentile)
3. **Cache Hit Rate**: > 80%
4. **Frontend Load Time**: < 2s
5. **Time to Interactive**: < 3s

### Tools

- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **Sentry**: Performance monitoring
- **Lighthouse**: Frontend performance

## 🎯 Performance Targets

### Backend

- API Response: < 100ms (p95)
- Database Queries: < 50ms (p95)
- Cache Hit Rate: > 80%
- Error Rate: < 1%

### Frontend

- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s
- Bundle Size: < 500KB (gzipped)
- Lighthouse Score: > 90

## 🔧 Optimization Checklist

- [ ] Frontend bundle optimized
- [ ] Code splitting configured
- [ ] Database indexes created
- [ ] Query optimization applied
- [ ] Caching strategy implemented
- [ ] CDN configured
- [ ] Performance monitoring active
- [ ] Metrics collected
- [ ] Alerts configured

## 🔗 Resources

- [Vite Optimization](https://vitejs.dev/guide/performance.html)
- [React Performance](https://react.dev/learn/render-and-commit)
- [PostgreSQL Indexing](https://www.postgresql.org/docs/current/indexes.html)
- [Redis Caching](https://redis.io/docs/manual/patterns/)

