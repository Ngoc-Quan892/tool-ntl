# Monitoring Setup Guide

Hướng dẫn thiết lập monitoring cho Baccarat Predictor Pro.

## 📋 Table of Contents

- [Overview](#overview)
- [Error Tracking (Sentry)](#error-tracking-sentry)
- [Analytics](#analytics)
- [Uptime Monitoring](#uptime-monitoring)
- [Alerts](#alerts)
- [Performance Monitoring](#performance-monitoring)

## 🌐 Overview

Monitoring stack bao gồm:

- **Sentry**: Error tracking và performance monitoring
- **Analytics**: Google Analytics hoặc Plausible
- **Uptime Monitoring**: Health check monitoring
- **Prometheus**: Metrics collection
- **Alerts**: Email/Slack notifications

## 🐛 Error Tracking (Sentry)

### Backend Setup

1. **Install Sentry SDK**:
```bash
cd backend
pip install sentry-sdk[fastapi]
```

2. **Configure environment variable**:
```bash
# .env.production
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
ENVIRONMENT=production
```

3. **Sentry tự động initialize** trong `app/main.py`

### Frontend Setup

1. **Install Sentry SDK**:
```bash
cd frontend
npm install @sentry/react
```

2. **Configure environment variable**:
```bash
# .env.production
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
VITE_APP_VERSION=1.0.0
```

3. **Sentry tự động initialize** từ `src/lib/sentry.ts`

### Usage

**Backend:**
```python
from app.services.monitoring import capture_exception, capture_message

try:
    # Your code
    pass
except Exception as e:
    capture_exception(e, context={"user_id": "123"})
```

**Frontend:**
```typescript
import { captureException, captureMessage } from '@/lib/sentry';

try {
  // Your code
} catch (error) {
  captureException(error as Error, { component: 'MyComponent' });
}
```

### Sentry Dashboard

- Access tại: https://sentry.io
- View errors, performance, releases
- Set up alerts và notifications

## 📊 Analytics

### Google Analytics Setup

1. **Get GA4 Measurement ID** từ Google Analytics

2. **Configure environment variable**:
```bash
# .env.production
VITE_ANALYTICS_ENABLED=true
VITE_GA_ID=G-XXXXXXXXXX
```

3. **Analytics tự động initialize** từ `src/lib/analytics.ts`

### Plausible Setup

1. **Get domain** từ Plausible

2. **Configure environment variable**:
```bash
# .env.production
VITE_ANALYTICS_ENABLED=true
VITE_PLAUSIBLE_DOMAIN=yourdomain.com
```

### Usage

```typescript
import { trackEvent, trackPageView } from '@/lib/analytics';

// Track page view
trackPageView('/dashboard');

// Track event
trackEvent('button_click', 'ui', 'new_shoe_button');

// Track custom event
trackCustomEvent('shoe_created', {
  decks: 8,
  reshuffle_point: 20,
});
```

## ⏱️ Uptime Monitoring

### Health Check Endpoints

- **Root**: `GET /health`
- **API**: `GET /api/v2/health`
- **Database**: `GET /api/v2/health/db`

### Uptime Robot Setup

1. **Create account** tại https://uptimerobot.com

2. **Add monitor**:
   - Type: HTTP(s)
   - URL: `https://yourdomain.com/health`
   - Interval: 5 minutes
   - Alert contacts: Email/Slack

3. **Configure alerts**:
   - Email notifications
   - Slack webhook
   - SMS (optional)

### Custom Uptime Monitoring

```bash
# Script để check uptime
#!/bin/bash
HEALTH_URL="https://yourdomain.com/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -ne 200 ]; then
    # Send alert
    echo "Health check failed: $RESPONSE"
    # Send notification
fi
```

## 🚨 Alerts

### Sentry Alerts

1. **Go to Sentry Dashboard**
2. **Alerts → Create Alert Rule**
3. **Configure**:
   - Trigger: Error rate > threshold
   - Actions: Email/Slack/PagerDuty

### Prometheus Alerts

1. **Configure Alertmanager**:
```yaml
# alertmanager.yml
route:
  receiver: 'slack'
  routes:
    - match:
        severity: critical
      receiver: 'slack-critical'

receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
```

2. **Alert Rules**:
```yaml
# alerts.yml
groups:
  - name: baccarat_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
```

### Email Alerts

1. **Configure SMTP** trong environment:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
ALERT_EMAIL=alerts@yourdomain.com
```

2. **Send alerts**:
```python
from app.utils.email import send_alert

send_alert(
    subject="Health Check Failed",
    message="Service is down",
    recipients=["admin@yourdomain.com"]
)
```

## 📈 Performance Monitoring

### Prometheus Metrics

- **Endpoint**: `GET /api/v2/metrics/prometheus`
- **Metrics**:
  - `http_requests_total`: Total requests
  - `http_request_duration_seconds`: Request duration
  - `cache_hits_total`: Cache hits
  - `cache_misses_total`: Cache misses
  - `database_queries_total`: Database queries
  - `slow_queries_total`: Slow queries

### Grafana Dashboard

1. **Install Grafana**
2. **Add Prometheus data source**
3. **Import dashboard** hoặc tạo custom dashboard

### Performance Targets

- **API Response Time**: < 100ms (95th percentile)
- **Database Queries**: < 50ms (95th percentile)
- **Cache Hit Rate**: > 80%
- **Error Rate**: < 1%
- **Uptime**: > 99.9%

## 🔧 Configuration

### Environment Variables

```bash
# Error Tracking
SENTRY_DSN=https://...
ENVIRONMENT=production

# Analytics
VITE_ANALYTICS_ENABLED=true
VITE_GA_ID=G-...
VITE_PLAUSIBLE_DOMAIN=...

# Alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
ALERT_EMAIL=alerts@...

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

## 📊 Monitoring Checklist

- [ ] Sentry configured và working
- [ ] Analytics tracking events
- [ ] Uptime monitoring active
- [ ] Alerts configured và tested
- [ ] Prometheus metrics collected
- [ ] Grafana dashboard created
- [ ] Performance targets monitored
- [ ] Error notifications working

## 🆘 Troubleshooting

### Sentry Not Working

1. Check DSN is correct
2. Check network connectivity
3. Check Sentry project settings
4. View browser console cho errors

### Analytics Not Tracking

1. Check environment variables
2. Check browser console
3. Verify script loading
4. Test với browser extensions disabled

### Alerts Not Sending

1. Check SMTP configuration
2. Test email sending manually
3. Check Slack webhook URL
4. Verify alert rules are active

## 🔗 Resources

- [Sentry Documentation](https://docs.sentry.io/)
- [Google Analytics](https://analytics.google.com/)
- [Plausible Analytics](https://plausible.io/)
- [Uptime Robot](https://uptimerobot.com/)
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)

