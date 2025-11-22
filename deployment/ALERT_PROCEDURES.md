# Alert Procedures - Baccarat Predictor Pro

Hướng dẫn chi tiết về hệ thống alerting và các quy trình xử lý alerts.

## 📋 Mục lục

- [Tổng quan](#tổng-quan)
- [Cấu hình Alerts](#cấu-hình-alerts)
- [Alert Thresholds](#alert-thresholds)
- [Notification Channels](#notification-channels)
- [Quy trình xử lý Alerts](#quy-trình-xử-lý-alerts)
- [Testing Alerts](#testing-alerts)
- [Troubleshooting](#troubleshooting)

## 🌐 Tổng quan

Hệ thống alerting tự động giám sát các metrics quan trọng và gửi thông báo khi có vấn đề. Hệ thống hỗ trợ:

- **Multiple notification channels**: Slack, Email, Logging, Sentry
- **Configurable thresholds**: Có thể tùy chỉnh ngưỡng cảnh báo
- **Cooldown periods**: Tránh spam alerts
- **Severity levels**: Warning và Critical

## ⚙️ Cấu hình Alerts

### Environment Variables

Thêm vào `.env` hoặc `.env.production`:

```bash
# Alerting
ALERT_ENABLED=true
ALERT_CHECK_INTERVAL=60  # seconds

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@yourdomain.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=ops@yourdomain.com

# Sentry (optional, for critical alerts)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### Khởi động Alert Manager

Alert Manager tự động khởi động khi ứng dụng start. Để kiểm tra:

```bash
# Check logs
docker-compose -f deployment/docker-compose.prod.yml logs backend | grep -i alert

# Check if alerts are enabled
curl http://localhost:8000/api/monitoring/metrics | jq '.alerts'
```

## 🎯 Alert Thresholds

### Default Thresholds

Hệ thống có các thresholds mặc định:

| Metric | Threshold | Severity | Cooldown | Mô tả |
|--------|-----------|----------|----------|-------|
| `cache_hit_rate` | < 70% | Warning | 5 min | Cache hit rate thấp |
| `avg_query_time_ms` | > 200ms | Critical | 3 min | Query chậm |
| `connection_pool_utilization` | > 90% | Critical | 5 min | Connection pool gần hết |
| `memory_percent` | > 90% | Warning | 10 min | Memory usage cao |

### Custom Thresholds

Thêm custom threshold trong code:

```python
from app.services.alerting import AlertManager

alert_manager = AlertManager(optimizer=optimizer)

# Thêm threshold mới
alert_manager.add_threshold(
    metric_name="error_rate",
    threshold=0.01,  # 1%
    comparison="gt",
    severity="critical",
    callback=lambda v, alert: send_pagerduty_alert(f"Error rate: {v:.2%}"),
    cooldown_seconds=300,
)
```

### Metric Names

Các metric có sẵn:

- `cache_hit_rate`: Cache hit rate (0-1)
- `cache.hit_rate`: Alternative format
- `avg_query_time_ms`: Average query time in milliseconds
- `queries.avg_time_ms`: Alternative format
- `connection_pool_utilization`: Connection pool utilization (0-1)
- `connections.utilization`: Alternative format
- `memory_percent`: Memory usage percentage (0-100)
- `cpu_percent`: CPU usage percentage (0-100)

## 📢 Notification Channels

### 1. Slack

**Setup:**

1. Tạo Slack webhook:
   - Vào https://api.slack.com/apps
   - Tạo app mới hoặc chọn app hiện có
   - Vào "Incoming Webhooks" → Enable
   - Tạo webhook cho channel (ví dụ: #alerts)
   - Copy webhook URL

2. Cấu hình:
   ```bash
   export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
   ```

**Format:**

Alerts được gửi dưới dạng Slack message với:
- Emoji: ⚠️ (warning) hoặc 🚨 (critical)
- Color: Orange (warning) hoặc Red (critical)
- Footer: "Baccarat Predictor Pro Alerting System"
- Timestamp

**Test:**

```bash
./deployment/scripts/test_alerting.sh
```

### 2. Email

**Setup:**

1. Cấu hình SMTP (ví dụ Gmail):
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=alerts@yourdomain.com
   SMTP_PASSWORD=your-app-password  # Use app password for Gmail
   ALERT_EMAIL=ops@yourdomain.com
   ```

2. Gmail App Password:
   - Vào Google Account → Security
   - Enable 2-Step Verification
   - Generate App Password
   - Sử dụng app password thay vì regular password

**Format:**

Email alerts bao gồm:
- Subject: "Alert: Baccarat Predictor Pro"
- Body: Chi tiết alert với metric name, current value, threshold
- Severity level

**Test:**

```bash
./deployment/scripts/test_alerting.sh
```

### 3. Logging

Tất cả alerts được log vào application logs:

```bash
# View alerts in logs
docker-compose -f deployment/docker-compose.prod.yml logs backend | grep -i "ALERT"

# Real-time alerts
docker-compose -f deployment/docker-compose.prod.yml logs -f backend | grep -i "ALERT"
```

Log format:
```
ALERT [CRITICAL]: avg_query_time_ms = 250.5 (gt 200)
```

### 4. Sentry

Critical alerts tự động được gửi đến Sentry (nếu đã cấu hình):

```python
# Automatic for critical alerts
if severity == "critical":
    capture_message(
        message,
        level="error",
        context={"alert_type": "performance_threshold", "severity": severity}
    )
```

## 🔄 Quy trình xử lý Alerts

### Warning Alerts

**Khi nhận được Warning Alert:**

1. **Đánh giá mức độ nghiêm trọng:**
   - Kiểm tra metric hiện tại
   - Xem xu hướng (trending up/down?)
   - Đánh giá impact

2. **Hành động:**
   - Monitor thêm 5-10 phút
   - Kiểm tra logs để tìm nguyên nhân
   - Nếu không tự khắc phục, escalate

3. **Documentation:**
   - Ghi lại alert trong incident log
   - Note root cause và resolution

### Critical Alerts

**Khi nhận được Critical Alert:**

1. **Immediate Response (0-5 phút):**
   - Kiểm tra service health: `curl http://localhost:8000/health`
   - Xem metrics dashboard: `curl http://localhost:8000/api/monitoring/dashboard`
   - Kiểm tra logs: `docker-compose logs backend --tail=100`

2. **Investigation (5-15 phút):**
   - Xác định root cause
   - Kiểm tra system resources (CPU, memory, disk)
   - Kiểm tra database connections
   - Kiểm tra cache status

3. **Resolution:**
   - Apply fix nếu có thể
   - Restart service nếu cần: `docker-compose restart backend`
   - Scale up nếu resource issue
   - Rollback nếu deployment issue

4. **Post-Incident:**
   - Document incident
   - Review và cải thiện thresholds nếu cần
   - Update runbook

### Alert Response Checklist

**Warning Alert:**
- [ ] Acknowledge alert
- [ ] Check current metrics
- [ ] Monitor for 5-10 minutes
- [ ] Investigate if persists
- [ ] Document if resolved

**Critical Alert:**
- [ ] Acknowledge alert immediately
- [ ] Check service health
- [ ] Check system resources
- [ ] Check logs for errors
- [ ] Identify root cause
- [ ] Apply fix
- [ ] Verify resolution
- [ ] Document incident

## 🧪 Testing Alerts

### Test Script

Chạy script test:

```bash
./deployment/scripts/test_alerting.sh
```

Script sẽ:
1. Kiểm tra backend status
2. Kiểm tra configuration
3. Test Slack notification (nếu configured)
4. Test Email notification (nếu configured)
5. Hiển thị thresholds

### Manual Testing

**Test Slack:**

```bash
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "🧪 Test Alert",
    "attachments": [{
      "color": "#FFA500",
      "text": "This is a test alert",
      "footer": "Baccarat Predictor Pro",
      "ts": '$(date +%s)'
    }]
  }'
```

**Test Email:**

```python
from app.services.alerting import NotificationService

service = NotificationService()
await service.send_email(
    subject="Test Alert",
    message="This is a test alert",
    severity="warning"
)
```

**Trigger Test Alert:**

```bash
# Trigger test alert via API (if endpoint exists)
curl -X POST http://localhost:8000/api/monitoring/test-alert
```

## 🔧 Troubleshooting

### Alerts không được gửi

**Kiểm tra:**

1. Alert Manager có đang chạy?
   ```bash
   docker-compose logs backend | grep -i "alert monitoring"
   ```

2. Configuration đúng chưa?
   ```bash
   docker-compose exec backend env | grep -E "(SLACK|SMTP|ALERT)"
   ```

3. Network connectivity?
   ```bash
   docker-compose exec backend curl -I https://hooks.slack.com
   docker-compose exec backend telnet smtp.gmail.com 587
   ```

4. Cooldown period?
   - Alerts có cooldown period để tránh spam
   - Kiểm tra `last_alert_times` trong logs

### Slack webhook không hoạt động

**Kiểm tra:**

1. Webhook URL đúng format?
   ```
   https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```

2. Webhook chưa bị revoke?
   - Vào Slack app settings kiểm tra

3. Channel permissions?
   - Đảm bảo bot có quyền post vào channel

### Email không được gửi

**Kiểm tra:**

1. SMTP credentials đúng?
   - Test với manual email client

2. App password (Gmail)?
   - Phải dùng app password, không phải regular password

3. Firewall/Network?
   - Kiểm tra port 587/465 có bị block không

4. TLS/SSL?
   - Đảm bảo `starttls()` được gọi

### Alerts quá nhiều (Alert Fatigue)

**Giải pháp:**

1. Tăng cooldown period:
   ```python
   alert_manager.add_threshold(
       ...,
       cooldown_seconds=600,  # 10 minutes
   )
   ```

2. Điều chỉnh thresholds:
   - Tăng threshold để giảm false positives
   - Chỉ alert khi thực sự critical

3. Group alerts:
   - Sử dụng alert aggregation
   - Batch notifications

## 📊 Alert Metrics

Theo dõi alert metrics:

```bash
# View alert history
curl http://localhost:8000/api/monitoring/dashboard | jq '.alerts'

# Check alert statistics
docker-compose logs backend | grep -i "ALERT" | wc -l
```

## 🔗 Related Files

- `backend/app/services/alerting.py` - Alert system implementation
- `backend/app/api/endpoints/monitoring.py` - Monitoring endpoints
- `deployment/scripts/test_alerting.sh` - Test script
- `deployment/MONITORING.md` - Monitoring setup guide

## 📝 Best Practices

1. **Set appropriate thresholds:**
   - Dựa trên baseline metrics
   - Không quá sensitive (tránh false positives)
   - Không quá loose (tránh miss real issues)

2. **Use cooldown periods:**
   - Tránh alert spam
   - 5-10 phút cho warnings
   - 3-5 phút cho criticals

3. **Document alert procedures:**
   - Runbook cho mỗi alert type
   - Escalation paths
   - Resolution steps

4. **Regular testing:**
   - Test alerts hàng tuần
   - Verify notification channels
   - Review và adjust thresholds

5. **Monitor alert effectiveness:**
   - Track alert-to-resolution time
   - Review false positive rate
   - Improve based on feedback

