# Production Deployment Checklist

Checklist đầy đủ trước khi deploy production.

## ✅ 1. Monitoring Setup (1 giờ)

### Key Metrics to Monitor

- **API response times** (p50, p95, p99)
- **Cache hit rate**
- **Database query times**
- **Connection pool utilization**
- **Error rates**
- **Request throughput**

### Tools

- **Prometheus + Grafana** (recommended)
- DataDog
- New Relic
- Hoặc custom dashboard với `/monitoring/dashboard`

### Setup Steps

1. **Configure Prometheus** (if using):

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'baccarat-api'
    scrape_interval: 5s
    static_configs:
      - targets: ['localhost:8000']
```

2. **Access Dashboard**:

```bash
# Real-time dashboard
curl http://localhost:8000/api/monitoring/dashboard

# Metrics endpoint
curl http://localhost:8000/api/monitoring/metrics

# Health check
curl http://localhost:8000/api/monitoring/health
```

3. **Verify Dashboard**:

- Check that metrics are updating every 5 seconds
- Verify trends show last 1 hour of data
- Confirm alerts are being detected

## ✅ 2. Alerting Setup (1 giờ)

### Critical Alerts (PagerDuty/SMS)

Configure alerts for:

- **API error rate >1%**
- **Database connection failures**
- **Cache completely down**
- **Response time >1s**

### Warning Alerts (Slack/Email)

Configure alerts for:

- **Cache hit rate <70%**
- **Response time >200ms**
- **Query time >100ms**
- **Connection pool >80% utilized**

### Setup Steps

1. **Configure Environment Variables**:

```bash
# Slack webhook
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Email (SMTP)
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="alerts@example.com"
export SMTP_PASSWORD="..."
export ALERT_EMAIL="ops@example.com"
```

2. **Verify AlertManager**:

```python
from app.services.alerting import AlertManager
from app.services.performance_optimizer import OptimizationStack

optimizer = OptimizationStack(...)
alert_manager = AlertManager(optimizer=optimizer)

# Check thresholds
for threshold in alert_manager.thresholds:
    print(f"{threshold.metric_name}: {threshold.comparison} {threshold.threshold}")
```

3. **Test Alerts**:

```bash
# Trigger test alert
curl -X POST http://localhost:8000/api/monitoring/test-alert
```

### Default Thresholds

The system comes with these default thresholds:

| Metric | Threshold | Severity | Cooldown |
|--------|-----------|----------|----------|
| Cache hit rate | < 70% | Warning | 5 min |
| Avg query time | > 200ms | Critical | 3 min |
| Connection pool | > 90% | Critical | 5 min |
| Memory usage | > 90% | Warning | 10 min |

## ✅ 3. Backup & Recovery (1 giờ)

### Database Backups

**Daily full backup**:

```bash
python scripts/backup_utilities.py backup-db --output-dir ./backups
```

**Hourly incremental backup** (set up cron):

```bash
# Add to crontab
0 * * * * cd /path/to/app && python scripts/backup_utilities.py backup-db
```

**Test restore procedure**:

```bash
# Restore from backup
pg_restore -d database_name backups/postgres_backup_YYYYMMDD_HHMMSS.sql
```

### Cache Backups

**Before deploy**:

```bash
python scripts/backup_utilities.py backup-cache
```

**After deploy** (if needed):

```bash
python scripts/backup_utilities.py restore-cache --file cache_backup_YYYYMMDD_HHMMSS.json
```

**Cache warming after restart**:

```bash
python scripts/backup_utilities.py warm-cache
```

### Redis Persistence

Configure Redis persistence:

```conf
# redis.conf
save 900 1      # Save after 900s if at least 1 key changed
save 300 10     # Save after 300s if at least 10 keys changed
save 60 10000   # Save after 60s if at least 10000 keys changed

appendonly yes  # Enable AOF
appendfsync everysec
```

### Config Backup

```bash
python scripts/backup_utilities.py backup-config
```

## ✅ 4. Deployment Checklist

### Pre-deployment

Run automated checklist:

```bash
python scripts/pre_deployment_checklist.py
```

Manual checks:

- [ ] All tests passing
- [ ] Benchmark shows 100% success rate
- [ ] Load test passed (100+ users)
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Backup taken
- [ ] Rollback plan ready
- [ ] Environment variables set
- [ ] Secrets in secure vault
- [ ] Documentation updated

### Deployment Steps

1. **Deploy to staging first**:

```bash
# Deploy to staging
./deployment/scripts/deploy.sh staging

# Run smoke tests
pytest tests/integration/test_smoke.py

# Monitor for 1 hour
watch -n 5 'curl http://staging.example.com/api/monitoring/dashboard'
```

2. **Verify staging**:

- [ ] Check metrics dashboard
- [ ] Verify no alerts
- [ ] Test critical endpoints
- [ ] Check error logs
- [ ] Validate cache hit rate

3. **Deploy to production**:

```bash
# Deploy to production
./deployment/scripts/deploy.sh production

# Warm up cache
python scripts/backup_utilities.py warm-cache

# Monitor for 24 hours
```

### Post-deployment

- [ ] Verify all metrics green
- [ ] Check error logs
- [ ] Validate cache hit rate
- [ ] Review performance reports
- [ ] Update documentation
- [ ] Notify team of deployment

## 🔧 Automated Checklist

Run the automated pre-deployment checklist:

```bash
# Run all checks
python scripts/pre_deployment_checklist.py

# Skip tests (if already verified)
python scripts/pre_deployment_checklist.py --skip-tests

# Save results to file
python scripts/pre_deployment_checklist.py --output checklist_results.json
```

## 📊 Monitoring Dashboard

Access the real-time dashboard:

```bash
# Get dashboard data
curl http://localhost:8000/api/monitoring/dashboard | jq

# Response includes:
# - current: Current metrics
# - trends: Last 1 hour trends
# - alerts: Active alerts
# - timestamp: Current timestamp
```

## 🚨 Alert Configuration

### Custom Alerts

Add custom alerts in code:

```python
from app.services.alerting import AlertManager

alert_manager = AlertManager(optimizer=optimizer)

# Add custom threshold
alert_manager.add_threshold(
    metric_name="error_rate",
    threshold=0.01,  # 1%
    comparison="gt",
    severity="critical",
    callback=lambda v: send_pagerduty_alert(f"Error rate: {v:.2%}"),
    cooldown_seconds=300,
)
```

### Alert Channels

Configure multiple alert channels:

1. **Slack**: Set `SLACK_WEBHOOK_URL`
2. **Email**: Set `SMTP_*` variables
3. **PagerDuty**: Integrate via webhook
4. **Sentry**: Automatic for critical alerts

## 🔄 Rollback Plan

If deployment fails:

1. **Immediate rollback**:

```bash
./deployment/scripts/rollback.sh
```

2. **Restore cache**:

```bash
python scripts/backup_utilities.py restore-cache --file cache_backup_YYYYMMDD_HHMMSS.json
```

3. **Restore database** (if needed):

```bash
pg_restore -d database_name backups/postgres_backup_YYYYMMDD_HHMMSS.sql
```

4. **Verify rollback**:

```bash
# Check health
curl http://localhost:8000/api/monitoring/health

# Check metrics
curl http://localhost:8000/api/monitoring/metrics
```

## 📝 Notes

- **Total time estimate**: 3-4 hours for full setup
- **Monitoring**: Should be set up before first production deploy
- **Alerts**: Test alerts before going live
- **Backups**: Automate daily backups
- **Documentation**: Keep deployment checklist updated

## 🔗 Related Files

- `scripts/pre_deployment_checklist.py` - Automated checklist
- `scripts/backup_utilities.py` - Backup utilities
- `app/api/endpoints/dashboard.py` - Dashboard endpoint
- `app/services/alerting.py` - Alerting system
- `app/api/endpoints/monitoring.py` - Monitoring endpoints

