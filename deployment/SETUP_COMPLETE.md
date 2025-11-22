# Setup Complete - Monitoring, Alerting & Deployment Prep

Tài liệu tổng hợp về việc setup monitoring, alerting và deployment preparation đã hoàn thành.

## ✅ Tổng quan

Đã hoàn thành 3 bước chính:

1. **Step 1: Setup Monitoring (2 giờ)** ✅
2. **Step 2: Setup Alerting (1 giờ)** ✅
3. **Step 3: Deployment Prep (1 giờ)** ✅

## 📊 Step 1: Monitoring Setup

### Đã hoàn thành

- [x] **Prometheus & Grafana trong Docker Compose**
  - Thêm services vào `deployment/docker-compose.prod.yml`
  - Cấu hình volumes và networks
  - Health checks cho cả 2 services

- [x] **Prometheus Configuration**
  - File: `deployment/monitoring/prometheus.yml`
  - Scrape config cho backend API
  - Retention: 30 days
  - Scrape interval: 15s

- [x] **Grafana Configuration**
  - Datasource provisioning: `deployment/monitoring/grafana/provisioning/datasources/prometheus.yml`
  - Dashboard provisioning: `deployment/monitoring/grafana/provisioning/dashboards/dashboards.yml`
  - Sample dashboard: `deployment/monitoring/grafana/dashboards/baccarat-dashboard.json`

- [x] **Prometheus Metrics Endpoint**
  - Endpoint: `/api/v2/metrics/prometheus`
  - Implementation: `backend/app/services/monitoring.py`
  - Metrics: HTTP requests, database queries, cache, connections, system resources

- [x] **Test Script**
  - File: `deployment/scripts/test_monitoring.sh`
  - Test Prometheus, Grafana, backend metrics
  - Verify real-time monitoring

### Files Created

- `deployment/docker-compose.prod.yml` (updated)
- `deployment/monitoring/prometheus.yml`
- `deployment/monitoring/grafana/provisioning/datasources/prometheus.yml`
- `deployment/monitoring/grafana/provisioning/dashboards/dashboards.yml`
- `deployment/monitoring/grafana/dashboards/baccarat-dashboard.json`
- `backend/app/services/monitoring.py` (updated)
- `backend/app/api/v2/metrics.py` (updated)
- `deployment/scripts/test_monitoring.sh`

### Usage

```bash
# Start monitoring stack
docker-compose -f deployment/docker-compose.prod.yml up -d prometheus grafana

# Test monitoring
./deployment/scripts/test_monitoring.sh

# Access URLs
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
# - Metrics: http://localhost:8000/api/v2/metrics/prometheus
```

## 🚨 Step 2: Alerting Setup

### Đã hoàn thành

- [x] **Alert Thresholds Configuration**
  - Default thresholds trong `backend/app/services/alerting.py`
  - Cache hit rate < 70% (warning)
  - Query time > 200ms (critical)
  - Connection pool > 90% (critical)
  - Memory > 90% (warning)

- [x] **Notification Channels**
  - Slack webhook support
  - Email (SMTP) support
  - Logging integration
  - Sentry integration (critical alerts)

- [x] **Test Script**
  - File: `deployment/scripts/test_alerting.sh`
  - Test Slack notifications
  - Test Email notifications
  - Verify configuration

- [x] **Alert Procedures Document**
  - File: `deployment/ALERT_PROCEDURES.md`
  - Chi tiết về thresholds
  - Quy trình xử lý alerts
  - Troubleshooting guide

### Files Created

- `deployment/scripts/test_alerting.sh`
- `deployment/ALERT_PROCEDURES.md`
- `backend/app/services/alerting.py` (already existed, verified)

### Usage

```bash
# Configure environment variables
export SLACK_WEBHOOK_URL="https://REDACTED_SLACK_HOOKS_DOMAIN/services/..."
export SMTP_HOST="smtp.gmail.com"
export SMTP_USER="alerts@yourdomain.com"
export SMTP_PASSWORD="your-password"
export ALERT_EMAIL="ops@yourdomain.com"

# Test alerting
./deployment/scripts/test_alerting.sh
```

## 🚀 Step 3: Deployment Prep

### Đã hoàn thành

- [x] **Deployment Checklist**
  - File: `deployment/DEPLOYMENT_CHECKLIST_COMPLETE.md`
  - Pre-deployment checklist
  - Deployment steps
  - Post-deployment verification
  - Emergency procedures

- [x] **Backup/Restore Test Script**
  - File: `deployment/scripts/test_backup_restore.sh`
  - Test backup creation
  - Verify backup contents
  - Test restore procedure

- [x] **Rollback Plan**
  - File: `deployment/ROLLBACK_PLAN.md`
  - Khi nào cần rollback
  - Rollback procedures
  - Verification steps
  - Troubleshooting

### Files Created

- `deployment/DEPLOYMENT_CHECKLIST_COMPLETE.md`
- `deployment/scripts/test_backup_restore.sh`
- `deployment/ROLLBACK_PLAN.md`
- `deployment/scripts/backup.sh` (already existed, verified)
- `deployment/scripts/rollback.sh` (already existed, verified)

### Usage

```bash
# Run deployment checklist
cat deployment/DEPLOYMENT_CHECKLIST_COMPLETE.md

# Test backup/restore
./deployment/scripts/test_backup_restore.sh

# Create backup before deployment
./deployment/scripts/backup.sh pre_deployment_$(date +%Y%m%d_%H%M%S)

# Rollback if needed
./deployment/scripts/rollback.sh
```

## 📋 Quick Start Guide

### 1. Start Monitoring Stack

```bash
# Start all services including monitoring
docker-compose -f deployment/docker-compose.prod.yml up -d

# Verify monitoring
./deployment/scripts/test_monitoring.sh
```

### 2. Configure Alerting

```bash
# Set environment variables in .env.production
cat >> deployment/.env.production << EOF
SLACK_WEBHOOK_URL=https://REDACTED_SLACK_HOOKS_DOMAIN/services/YOUR/WEBHOOK/URL
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@yourdomain.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=ops@yourdomain.com
EOF

# Test alerting
./deployment/scripts/test_alerting.sh
```

### 3. Prepare for Deployment

```bash
# Run pre-deployment checklist
cd backend
python scripts/pre_deployment_checklist.py

# Create backup
./deployment/scripts/backup.sh pre_deployment_$(date +%Y%m%d_%H%M%S)

# Test backup/restore
./deployment/scripts/test_backup_restore.sh
```

## 🔗 Documentation Links

### Monitoring
- [Monitoring Setup Guide](./MONITORING.md)
- [Prometheus Config](./monitoring/prometheus.yml)
- [Grafana Dashboard](./monitoring/grafana/dashboards/baccarat-dashboard.json)

### Alerting
- [Alert Procedures](./ALERT_PROCEDURES.md)
- [Test Script](./scripts/test_alerting.sh)

### Deployment
- [Deployment Checklist](./DEPLOYMENT_CHECKLIST_COMPLETE.md)
- [Rollback Plan](./ROLLBACK_PLAN.md)
- [Backup Test Script](./scripts/test_backup_restore.sh)

## ✅ Verification Checklist

Trước khi deploy production, verify:

- [ ] Prometheus running và scraping metrics
- [ ] Grafana accessible và dashboard loaded
- [ ] Metrics endpoint returning data
- [ ] Slack notifications working
- [ ] Email notifications working
- [ ] Alert thresholds configured
- [ ] Backup script tested
- [ ] Rollback script tested
- [ ] Deployment checklist reviewed
- [ ] Team trained on procedures

## 📊 Monitoring URLs

Sau khi start services:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Backend Metrics**: http://localhost:8000/api/v2/metrics/prometheus
- **Monitoring Dashboard**: http://localhost:8000/api/monitoring/dashboard
- **Health Check**: http://localhost:8000/health

## 🎯 Next Steps

1. **Import Grafana Dashboard:**
   - Access Grafana: http://localhost:3000
   - Import dashboard từ `deployment/monitoring/grafana/dashboards/baccarat-dashboard.json`

2. **Configure Alerts:**
   - Set Slack webhook URL
   - Configure SMTP settings
   - Test notifications

3. **Practice Rollback:**
   - Test rollback trong staging
   - Verify backup/restore
   - Document any issues

4. **Monitor First Deployment:**
   - Watch metrics dashboard
   - Monitor alerts
   - Be ready to rollback

## 📝 Notes

- **Total setup time**: ~4 giờ (2h monitoring + 1h alerting + 1h deployment prep)
- **Monitoring**: Should be running before first production deploy
- **Alerts**: Test all notification channels before going live
- **Backups**: Automate daily backups
- **Rollback**: Practice rollback procedure in staging

## 🆘 Support

Nếu gặp vấn đề:

1. Check logs: `docker-compose -f deployment/docker-compose.prod.yml logs`
2. Review documentation trong các file đã tạo
3. Test scripts để verify configuration
4. Check troubleshooting sections trong docs

---

**Setup completed on:** $(date)
**Version:** 1.0.0
**Status:** ✅ Ready for Production Deployment

