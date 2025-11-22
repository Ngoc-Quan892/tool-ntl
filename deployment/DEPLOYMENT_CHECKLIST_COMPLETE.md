# Production Deployment Checklist - Complete Guide

Checklist đầy đủ và chi tiết cho production deployment của Baccarat Predictor Pro.

## 📋 Mục lục

- [Pre-Deployment](#pre-deployment)
- [Deployment Steps](#deployment-steps)
- [Post-Deployment](#post-deployment)
- [Rollback Plan](#rollback-plan)
- [Emergency Procedures](#emergency-procedures)

## ✅ Pre-Deployment

### 1. Code & Testing (30 phút)

- [ ] **All tests passing:**
  ```bash
  cd backend
  pytest tests/ -v
  ```

- [ ] **Performance benchmark:**
  ```bash
  python benchmarks/performance_benchmark.py
  ```
  - [ ] Success rate: 100%
  - [ ] All metrics meet targets

- [ ] **Load test:**
  ```bash
  pytest tests/load/ -v
  ```
  - [ ] Handles 100+ concurrent users
  - [ ] Response time < 200ms (p95)

- [ ] **Security scan:**
  ```bash
  # Check for vulnerabilities
  pip-audit
  npm audit  # for frontend
  ```

- [ ] **Code review completed:**
  - [ ] All PRs reviewed
  - [ ] No critical issues
  - [ ] Documentation updated

### 2. Environment Preparation (15 phút)

- [ ] **Environment variables set:**
  ```bash
  # Check required variables
  cat deployment/.env.production | grep -E "(DATABASE_URL|REDIS_URL|SECRET_KEY)"
  ```

- [ ] **Secrets in secure vault:**
  - [ ] Database credentials
  - [ ] Redis password
  - [ ] JWT secret key
  - [ ] SMTP credentials
  - [ ] Slack webhook URL
  - [ ] Sentry DSN

- [ ] **Database migrations ready:**
  ```bash
  cd backend
  alembic current
  alembic heads
  ```

- [ ] **Docker images built:**
  ```bash
  docker-compose -f deployment/docker-compose.prod.yml build
  ```

### 3. Monitoring & Alerting (15 phút)

- [ ] **Monitoring configured:**
  ```bash
  # Test monitoring
  ./deployment/scripts/test_monitoring.sh
  ```
  - [ ] Prometheus running
  - [ ] Grafana accessible
  - [ ] Metrics being collected

- [ ] **Alerting configured:**
  ```bash
  # Test alerting
  ./deployment/scripts/test_alerting.sh
  ```
  - [ ] Slack webhook working
  - [ ] Email notifications working
  - [ ] Alert thresholds set

- [ ] **Dashboard ready:**
  - [ ] Grafana dashboard imported
  - [ ] Key metrics visible
  - [ ] Alerts configured

### 4. Backup & Recovery (15 phút)

- [ ] **Backup current state:**
  ```bash
  ./deployment/scripts/backup.sh pre_deployment_$(date +%Y%m%d_%H%M%S)
  ```

- [ ] **Test backup/restore:**
  ```bash
  ./deployment/scripts/test_backup_restore.sh
  ```

- [ ] **Backup location verified:**
  - [ ] Database backup accessible
  - [ ] Config backup saved
  - [ ] Image tags recorded

### 5. Automated Checklist (5 phút)

- [ ] **Run automated checklist:**
  ```bash
  cd backend
  python scripts/pre_deployment_checklist.py
  ```
  - [ ] All checks passing
  - [ ] No critical warnings

## 🚀 Deployment Steps

### Step 1: Deploy to Staging (30 phút)

**Nếu có staging environment:**

1. **Deploy to staging:**
   ```bash
   ./deployment/scripts/deploy.sh staging
   ```

2. **Run smoke tests:**
   ```bash
   pytest tests/integration/test_smoke.py
   ```

3. **Monitor for 1 hour:**
   ```bash
   watch -n 5 'curl http://staging.example.com/api/monitoring/dashboard | jq'
   ```

4. **Verify:**
   - [ ] All endpoints working
   - [ ] No errors in logs
   - [ ] Metrics normal
   - [ ] No alerts triggered

### Step 2: Production Deployment (30 phút)

1. **Final backup:**
   ```bash
   ./deployment/scripts/backup.sh pre_production_$(date +%Y%m%d_%H%M%S)
   ```

2. **Deploy to production:**
   ```bash
   ./deployment/scripts/deploy.sh production
   ```

3. **Wait for health checks:**
   ```bash
   # Monitor health
   watch -n 2 'curl -s http://localhost/health | jq'
   ```

4. **Verify services:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml ps
   ```
   - [ ] All services healthy
   - [ ] No restart loops

5. **Warm up cache:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml exec backend \
     python scripts/backup_utilities.py warm-cache
   ```

6. **Run post-deployment checks:**
   ```bash
   # Health check
   curl http://localhost/health
   
   # API check
   curl http://localhost/api/v2/health
   
   # Metrics check
   curl http://localhost/api/v2/metrics/prometheus | head -20
   ```

## ✅ Post-Deployment

### Immediate Checks (15 phút)

- [ ] **Service health:**
  ```bash
  curl http://localhost/health
  curl http://localhost/api/v2/health
  ```

- [ ] **Metrics dashboard:**
  ```bash
  curl http://localhost/api/monitoring/dashboard | jq
  ```
  - [ ] All metrics green
  - [ ] No alerts active

- [ ] **Error logs:**
  ```bash
  docker-compose -f deployment/docker-compose.prod.yml logs backend --tail=100 | grep -i error
  ```

- [ ] **Database connectivity:**
  ```bash
  curl http://localhost/api/v2/health/db
  ```

- [ ] **Cache status:**
  ```bash
  curl http://localhost/api/v2/metrics/dashboard | jq '.cache'
  ```

### Extended Monitoring (24 giờ)

- [ ] **Monitor for 24 hours:**
  - [ ] Check metrics every hour
  - [ ] Review error logs
  - [ ] Watch for alerts
  - [ ] Verify performance

- [ ] **Key metrics to watch:**
  - Response time (p95 < 200ms)
  - Error rate (< 1%)
  - Cache hit rate (> 70%)
  - Database query time (< 100ms)
  - Connection pool utilization (< 80%)

- [ ] **Alert review:**
  - [ ] No false positives
  - [ ] All alerts acknowledged
  - [ ] Issues resolved

### Documentation (15 phút)

- [ ] **Update deployment log:**
  - [ ] Deployment date/time
  - [ ] Version deployed
  - [ ] Issues encountered
  - [ ] Resolution steps

- [ ] **Notify team:**
  - [ ] Deployment complete
  - [ ] Version information
  - [ ] Known issues (if any)

- [ ] **Update changelog:**
  - [ ] Features added
  - [ ] Bugs fixed
  - [ ] Breaking changes

## 🔄 Rollback Plan

### When to Rollback

Rollback ngay lập tức nếu:

- [ ] Service không start được
- [ ] Health check fails sau 5 phút
- [ ] Error rate > 5%
- [ ] Critical functionality broken
- [ ] Database connection failures

### Rollback Procedure

1. **Stop current deployment:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml stop backend frontend
   ```

2. **Execute rollback:**
   ```bash
   ./deployment/scripts/rollback.sh
   ```

3. **Verify rollback:**
   ```bash
   curl http://localhost/health
   curl http://localhost/api/v2/health
   ```

4. **Monitor:**
   - [ ] Service healthy
   - [ ] No errors
   - [ ] Metrics normal

5. **Document:**
   - [ ] Rollback reason
   - [ ] Time taken
   - [ ] Issues found

Xem chi tiết: [Rollback Script Documentation](./scripts/rollback.sh)

## 🆘 Emergency Procedures

### Service Down

1. **Check service status:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml ps
   docker-compose -f deployment/docker-compose.prod.yml logs backend --tail=50
   ```

2. **Restart service:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml restart backend
   ```

3. **If still down, rollback:**
   ```bash
   ./deployment/scripts/rollback.sh
   ```

### Database Issues

1. **Check database:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml exec postgres psql -U baccarat_user -d baccarat -c "SELECT 1"
   ```

2. **Check connections:**
   ```bash
   curl http://localhost/api/v2/health/db
   ```

3. **Restart if needed:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml restart postgres
   ```

### High Error Rate

1. **Check error logs:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml logs backend --tail=100 | grep -i error
   ```

2. **Check metrics:**
   ```bash
   curl http://localhost/api/monitoring/dashboard | jq '.alerts'
   ```

3. **Scale up if needed:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml up -d --scale backend=2
   ```

4. **Rollback if critical:**
   ```bash
   ./deployment/scripts/rollback.sh
   ```

## 📊 Success Criteria

Deployment được coi là thành công nếu:

- [ ] All services healthy
- [ ] Health checks passing
- [ ] No critical errors
- [ ] Response time < 200ms (p95)
- [ ] Error rate < 1%
- [ ] Cache hit rate > 70%
- [ ] No alerts triggered
- [ ] All tests passing

## 🔗 Related Files

- `deployment/scripts/deploy.sh` - Deployment script
- `deployment/scripts/rollback.sh` - Rollback script
- `deployment/scripts/backup.sh` - Backup script
- `deployment/scripts/test_backup_restore.sh` - Backup test script
- `backend/scripts/pre_deployment_checklist.py` - Automated checklist
- `deployment/ALERT_PROCEDURES.md` - Alert procedures

## 📝 Notes

- **Total time estimate**: 2-3 giờ cho full deployment
- **Rollback time**: < 5 phút
- **Monitoring period**: 24 giờ sau deployment
- **Backup frequency**: Trước mỗi deployment

## ✅ Final Checklist

Trước khi đánh dấu deployment hoàn thành:

- [ ] All pre-deployment checks passed
- [ ] Deployment successful
- [ ] Post-deployment checks passed
- [ ] Monitoring active
- [ ] Alerts configured
- [ ] Team notified
- [ ] Documentation updated
- [ ] Backup verified

