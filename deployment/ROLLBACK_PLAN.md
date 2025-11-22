# Rollback Plan - Baccarat Predictor Pro

Kế hoạch rollback chi tiết cho production deployment.

## 📋 Mục lục

- [Khi nào cần rollback](#khi-nào-cần-rollback)
- [Rollback Procedure](#rollback-procedure)
- [Rollback Scripts](#rollback-scripts)
- [Verification Steps](#verification-steps)
- [Post-Rollback](#post-rollback)
- [Troubleshooting](#troubleshooting)

## 🚨 Khi nào cần rollback

Rollback ngay lập tức nếu gặp một trong các tình huống sau:

### Critical Issues

- [ ] **Service không start được**
  - Container không thể start
  - Health check fails liên tục
  - Application crash ngay sau khi start

- [ ] **Health check fails sau 5 phút**
  - `/health` endpoint trả về error
  - `/api/v2/health` fails
  - Database health check fails

- [ ] **Error rate > 5%**
  - Tỷ lệ lỗi cao bất thường
  - Nhiều 500 errors
  - Critical endpoints failing

- [ ] **Database connection failures**
  - Không thể kết nối database
  - Connection pool exhausted
  - Query timeouts

- [ ] **Critical functionality broken**
  - Core features không hoạt động
  - Data corruption
  - Security issues

### Performance Issues

- [ ] **Response time > 1s (p95)**
  - API chậm bất thường
  - Timeout errors
  - User complaints

- [ ] **Memory/CPU exhaustion**
  - Memory usage > 95%
  - CPU usage > 90%
  - OOM kills

## 🔄 Rollback Procedure

### Quick Rollback (< 5 phút)

**Sử dụng rollback script tự động:**

```bash
cd deployment
./scripts/rollback.sh
```

Script sẽ:
1. Tìm backup mới nhất
2. Dừng services hiện tại
3. Backup trạng thái hiện tại (pre-rollback backup)
4. Restore từ backup
5. Restart services
6. Verify health checks

### Manual Rollback

**Nếu script không hoạt động:**

1. **Stop current services:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml stop backend frontend
   ```

2. **Find latest backup:**
   ```bash
   ls -lt deployment/backups/ | head -5
   ```

3. **Backup current state:**
   ```bash
   ./deployment/scripts/backup.sh pre_rollback_$(date +%Y%m%d_%H%M%S)
   ```

4. **Restore from backup:**
   ```bash
   # Restore Docker images (if tagged)
   docker-compose -f deployment/docker-compose.prod.yml pull backend frontend
   
   # Or use previous image tags
   if [ -f "deployment/backups/LATEST_BACKUP/image-tags.txt" ]; then
       cat deployment/backups/LATEST_BACKUP/image-tags.txt
       # Manually set image tags in docker-compose.prod.yml
   fi
   ```

5. **Restart services:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml up -d backend frontend
   ```

6. **Wait for health checks:**
   ```bash
   MAX_RETRIES=30
   RETRY_COUNT=0
   
   while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
       if curl -f http://localhost/health > /dev/null 2>&1; then
           echo "✅ Health check passed!"
           break
       fi
       RETRY_COUNT=$((RETRY_COUNT + 1))
       echo "   Retry $RETRY_COUNT/$MAX_RETRIES..."
       sleep 2
   done
   ```

### Database Rollback

**Nếu cần rollback database:**

1. **Stop application:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml stop backend
   ```

2. **Restore database:**
   ```bash
   # Find database backup
   ls -lt deployment/backups/*/database.sql | head -1
   
   # Restore
   docker-compose -f deployment/docker-compose.prod.yml exec -T postgres \
     psql -U baccarat_user -d baccarat < deployment/backups/BACKUP_NAME/database.sql
   ```

3. **Verify database:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml exec postgres \
     psql -U baccarat_user -d baccarat -c "SELECT COUNT(*) FROM game_results;"
   ```

4. **Restart application:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml start backend
   ```

### Cache Rollback

**Nếu cần rollback cache:**

1. **Clear current cache:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml exec backend \
     python scripts/backup_utilities.py clear-cache
   ```

2. **Restore cache (if backup exists):**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml exec backend \
     python scripts/backup_utilities.py restore-cache \
     --file deployment/backups/BACKUP_NAME/cache_backup.json
   ```

3. **Warm up cache:**
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml exec backend \
     python scripts/backup_utilities.py warm-cache
   ```

## 📜 Rollback Scripts

### Main Rollback Script

**Location:** `deployment/scripts/rollback.sh`

**Usage:**
```bash
# Rollback to latest backup
./deployment/scripts/rollback.sh

# Rollback to specific backup
./deployment/scripts/rollback.sh BACKUP_NAME
```

**Features:**
- Automatic backup discovery
- Pre-rollback backup creation
- Health check verification
- Error handling

### Backup Script

**Location:** `deployment/scripts/backup.sh`

**Usage:**
```bash
# Create backup
./deployment/scripts/backup.sh backup_name

# Create timestamped backup
./deployment/scripts/backup.sh
```

**What it backs up:**
- Docker Compose configuration
- Container status
- Image tags
- Database (if PostgreSQL)
- Environment configuration (sanitized)

## ✅ Verification Steps

Sau khi rollback, verify các bước sau:

### 1. Service Health (2 phút)

```bash
# Health check
curl http://localhost/health
# Expected: {"status": "healthy", ...}

# API health
curl http://localhost/api/v2/health
# Expected: {"status": "ok", ...}

# Database health
curl http://localhost/api/v2/health/db
# Expected: {"status": "connected", ...}
```

### 2. Service Status (1 phút)

```bash
docker-compose -f deployment/docker-compose.prod.yml ps
# Expected: All services "Up" and healthy
```

### 3. Metrics Check (2 phút)

```bash
# Check metrics
curl http://localhost/api/monitoring/dashboard | jq

# Verify:
# - No critical alerts
# - Response time normal
# - Error rate < 1%
# - Cache hit rate > 70%
```

### 4. Functional Test (5 phút)

```bash
# Test critical endpoints
curl http://localhost/api/v2/shoes
curl http://localhost/api/v2/predictions

# Test WebSocket (if applicable)
# Test frontend loads correctly
```

### 5. Logs Check (2 phút)

```bash
# Check for errors
docker-compose -f deployment/docker-compose.prod.yml logs backend --tail=100 | grep -i error

# Check for warnings
docker-compose -f deployment/docker-compose.prod.yml logs backend --tail=100 | grep -i warn
```

## 📝 Post-Rollback

### Immediate Actions (15 phút)

1. **Document rollback:**
   - [ ] Record rollback time
   - [ ] Note reason for rollback
   - [ ] Document issues found
   - [ ] Save rollback logs

2. **Notify team:**
   - [ ] Send notification (Slack/Email)
   - [ ] Include rollback reason
   - [ ] Share timeline
   - [ ] Update status page (if applicable)

3. **Monitor closely:**
   - [ ] Watch metrics for 1 hour
   - [ ] Check for alerts
   - [ ] Monitor error logs
   - [ ] Verify user reports

### Investigation (1-2 giờ)

1. **Root cause analysis:**
   - [ ] Review deployment logs
   - [ ] Check code changes
   - [ ] Review configuration changes
   - [ ] Analyze error patterns

2. **Fix issues:**
   - [ ] Identify root cause
   - [ ] Create fix
   - [ ] Test fix in staging
   - [ ] Prepare for re-deployment

3. **Update procedures:**
   - [ ] Update deployment checklist
   - [ ] Improve rollback procedures
   - [ ] Document lessons learned
   - [ ] Update runbooks

### Re-deployment Preparation

Trước khi deploy lại:

- [ ] Root cause identified và fixed
- [ ] Fix tested trong staging
- [ ] All tests passing
- [ ] Monitoring verified
- [ ] Backup taken
- [ ] Team notified
- [ ] Rollback plan ready

## 🔧 Troubleshooting

### Rollback Script Fails

**Issue:** Script không chạy được

**Solutions:**
1. Check permissions:
   ```bash
   chmod +x deployment/scripts/rollback.sh
   ```

2. Check backup directory:
   ```bash
   ls -la deployment/backups/
   ```

3. Run manually (xem Manual Rollback section)

### Services Won't Start

**Issue:** Services không start sau rollback

**Solutions:**
1. Check logs:
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml logs backend
   ```

2. Check dependencies:
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml ps
   ```

3. Check resources:
   ```bash
   docker stats
   ```

4. Restart dependencies:
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml restart postgres redis
   ```

### Health Check Fails

**Issue:** Health check fails sau rollback

**Solutions:**
1. Check service logs:
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml logs backend --tail=50
   ```

2. Check database connection:
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml exec backend \
     python -c "from app.models.database import db_manager; print(db_manager.health_check())"
   ```

3. Check Redis connection:
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml exec redis redis-cli ping
   ```

4. Restart service:
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml restart backend
   ```

### Database Issues

**Issue:** Database errors sau rollback

**Solutions:**
1. Check database status:
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml exec postgres \
     psql -U baccarat_user -d baccarat -c "SELECT 1"
   ```

2. Check migrations:
   ```bash
   docker-compose -f deployment/docker-compose.prod.yml exec backend \
     alembic current
   ```

3. Restore database nếu cần (xem Database Rollback section)

## 📊 Rollback Metrics

Theo dõi rollback metrics:

- **Rollback time:** < 5 phút (target)
- **Service recovery time:** < 2 phút
- **Health check pass time:** < 1 phút
- **Total downtime:** < 10 phút

## 🔗 Related Files

- `deployment/scripts/rollback.sh` - Main rollback script
- `deployment/scripts/backup.sh` - Backup script
- `deployment/scripts/test_backup_restore.sh` - Backup test script
- `deployment/DEPLOYMENT_CHECKLIST_COMPLETE.md` - Deployment checklist

## 📝 Best Practices

1. **Always backup before deployment:**
   - Automatic backup trong deploy script
   - Manual backup trước critical changes

2. **Test rollback procedure:**
   - Test trong staging environment
   - Verify backup/restore scripts
   - Practice rollback procedure

3. **Monitor during deployment:**
   - Watch metrics dashboard
   - Monitor error logs
   - Be ready to rollback quickly

4. **Document everything:**
   - Record rollback reasons
   - Document issues found
   - Update procedures

5. **Learn from rollbacks:**
   - Root cause analysis
   - Improve deployment process
   - Prevent future issues

## ✅ Rollback Checklist

Trước khi đánh dấu rollback hoàn thành:

- [ ] Services healthy
- [ ] Health checks passing
- [ ] No critical errors
- [ ] Metrics normal
- [ ] Functional tests passing
- [ ] Team notified
- [ ] Rollback documented
- [ ] Root cause identified
- [ ] Fix prepared

