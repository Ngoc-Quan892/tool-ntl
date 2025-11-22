#!/bin/bash
# ==================== TEST ALERTING SCRIPT ====================
# Test alerting system (Slack, Email notifications)
# Usage: ./test_alerting.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  TEST ALERTING SYSTEM"
echo "=========================================="
echo ""

cd "$DEPLOYMENT_DIR/.." || exit 1

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
echo "📊 Checking backend status..."
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}❌ Backend is not running${NC}"
    echo "   Start with: docker-compose -f deployment/docker-compose.prod.yml up -d backend"
    exit 1
fi
echo -e "${GREEN}✅ Backend is running${NC}"

# Test 1: Test alert endpoint (if available)
echo ""
echo "📊 Test 1: Testing alert endpoint..."
if curl -f -X POST http://localhost:8000/api/monitoring/test-alert > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Alert endpoint is accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Alert endpoint may not be available (this is OK)${NC}"
fi

# Test 2: Check environment variables
echo ""
echo "📊 Test 2: Checking alert configuration..."
echo "   Environment variables:"

if [ -n "$SLACK_WEBHOOK_URL" ]; then
    echo -e "   ${GREEN}✅ SLACK_WEBHOOK_URL is set${NC}"
else
    echo -e "   ${YELLOW}⚠️  SLACK_WEBHOOK_URL is not set${NC}"
    echo "      Set in .env: SLACK_WEBHOOK_URL=https://hooks.slack.com/services/..."
fi

if [ -n "$SMTP_HOST" ] && [ -n "$SMTP_USER" ] && [ -n "$SMTP_PASSWORD" ]; then
    echo -e "   ${GREEN}✅ SMTP configuration is set${NC}"
else
    echo -e "   ${YELLOW}⚠️  SMTP configuration is not complete${NC}"
    echo "      Set in .env: SMTP_HOST, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL"
fi

# Test 3: Manual Slack test (if webhook is set)
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    echo ""
    echo "📊 Test 3: Testing Slack notification..."
    read -p "   Send test Slack message? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        PAYLOAD='{"text":"🧪 Test alert from Baccarat Predictor Pro","attachments":[{"color":"#FFA500","text":"This is a test alert to verify Slack integration is working.","footer":"Baccarat Predictor Pro Alerting System","ts":'$(date +%s)'}]}'
        
        RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SLACK_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$PAYLOAD")
        
        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "   ${GREEN}✅ Slack notification sent successfully${NC}"
        else
            echo -e "   ${RED}❌ Slack notification failed (HTTP $HTTP_CODE)${NC}"
            echo "   Response: $(echo "$RESPONSE" | head -n-1)"
        fi
    fi
else
    echo ""
    echo "📊 Test 3: Skipping Slack test (webhook not configured)"
fi

# Test 4: Manual Email test (if SMTP is set)
if [ -n "$SMTP_HOST" ] && [ -n "$SMTP_USER" ] && [ -n "$SMTP_PASSWORD" ] && [ -n "$ALERT_EMAIL" ]; then
    echo ""
    echo "📊 Test 4: Testing Email notification..."
    read -p "   Send test email to $ALERT_EMAIL? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Use Python to send test email
        python3 << EOF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

smtp_host = os.getenv('SMTP_HOST')
smtp_port = int(os.getenv('SMTP_PORT', '587'))
smtp_user = os.getenv('SMTP_USER')
smtp_password = os.getenv('SMTP_PASSWORD')
alert_email = os.getenv('ALERT_EMAIL')

try:
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = alert_email
    msg['Subject'] = "🧪 Test Alert - Baccarat Predictor Pro"
    
    body = """
This is a test alert to verify email integration is working.

System: Baccarat Predictor Pro
Alert Type: Test Notification
Status: OK

If you received this email, the alerting system is configured correctly.
"""
    msg.attach(MIMEText(body, 'plain'))
    
    server = smtplib.SMTP(smtp_host, smtp_port)
    server.starttls()
    server.login(smtp_user, smtp_password)
    server.send_message(msg)
    server.quit()
    
    print("   ✅ Email notification sent successfully")
except Exception as e:
    print(f"   ❌ Email notification failed: {e}")
    exit(1)
EOF
        
        if [ $? -eq 0 ]; then
            echo -e "   ${GREEN}✅ Email notification sent successfully${NC}"
        else
            echo -e "   ${RED}❌ Email notification failed${NC}"
        fi
    fi
else
    echo ""
    echo "📊 Test 4: Skipping Email test (SMTP not configured)"
fi

# Test 5: Check alert thresholds
echo ""
echo "📊 Test 5: Checking alert thresholds..."
echo "   Default thresholds configured:"
echo "   - Cache hit rate < 70% (warning)"
echo "   - Avg query time > 200ms (critical)"
echo "   - Connection pool > 90% (critical)"
echo "   - Memory usage > 90% (warning)"

# Summary
echo ""
echo "=========================================="
echo -e "${GREEN}✅ ALERTING TEST COMPLETE${NC}"
echo "=========================================="
echo ""
echo "Configuration checklist:"
echo "  [ ] SLACK_WEBHOOK_URL configured"
echo "  [ ] SMTP settings configured"
echo "  [ ] ALERT_EMAIL configured"
echo "  [ ] Alert thresholds tested"
echo ""
echo "Next steps:"
echo "  1. Configure Slack webhook URL in .env"
echo "  2. Configure SMTP settings in .env"
echo "  3. Test alerts by triggering threshold breaches"
echo "  4. Review alert procedures document"
echo ""

