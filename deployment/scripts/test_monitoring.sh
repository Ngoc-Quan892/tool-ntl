#!/bin/bash
# ==================== TEST MONITORING SCRIPT ====================
# Test real-time monitoring setup
# Usage: ./test_monitoring.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  TEST MONITORING SETUP"
echo "=========================================="
echo ""

cd "$DEPLOYMENT_DIR/.." || exit 1

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check Prometheus is running
echo "📊 Test 1: Checking Prometheus..."
if curl -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Prometheus is running${NC}"
else
    echo -e "${RED}❌ Prometheus is not running${NC}"
    echo "   Start with: docker-compose -f deployment/docker-compose.prod.yml up -d prometheus"
    exit 1
fi

# Test 2: Check Grafana is running
echo ""
echo "📊 Test 2: Checking Grafana..."
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Grafana is running${NC}"
else
    echo -e "${RED}❌ Grafana is not running${NC}"
    echo "   Start with: docker-compose -f deployment/docker-compose.prod.yml up -d grafana"
    exit 1
fi

# Test 3: Check backend metrics endpoint
echo ""
echo "📊 Test 3: Checking backend metrics endpoint..."
if curl -f http://localhost:8000/api/v2/metrics/prometheus > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend metrics endpoint is accessible${NC}"
    
    # Show sample metrics
    echo ""
    echo "   Sample metrics:"
    curl -s http://localhost:8000/api/v2/metrics/prometheus | head -20 | sed 's/^/   /'
else
    echo -e "${RED}❌ Backend metrics endpoint is not accessible${NC}"
    echo "   Check if backend is running: docker-compose -f deployment/docker-compose.prod.yml ps backend"
    exit 1
fi

# Test 4: Check Prometheus can scrape backend
echo ""
echo "📊 Test 4: Checking Prometheus targets..."
PROMETHEUS_TARGETS=$(curl -s http://localhost:9090/api/v1/targets | grep -o '"health":"[^"]*"' | head -5)
if echo "$PROMETHEUS_TARGETS" | grep -q "up"; then
    echo -e "${GREEN}✅ Prometheus can scrape backend${NC}"
    echo "   Targets status:"
    curl -s http://localhost:9090/api/v1/targets | grep -o '"health":"[^"]*"' | sed 's/^/   /'
else
    echo -e "${YELLOW}⚠️  Prometheus targets may not be up yet${NC}"
    echo "   Check Prometheus UI: http://localhost:9090/targets"
fi

# Test 5: Check Grafana can connect to Prometheus
echo ""
echo "📊 Test 5: Checking Grafana datasource..."
GRAFANA_DS=$(curl -s -u admin:admin http://localhost:3000/api/datasources 2>/dev/null | grep -o '"name":"[^"]*"' | head -1)
if [ -n "$GRAFANA_DS" ]; then
    echo -e "${GREEN}✅ Grafana datasource configured${NC}"
    echo "   Datasource: $GRAFANA_DS"
else
    echo -e "${YELLOW}⚠️  Grafana datasource may need configuration${NC}"
    echo "   Access Grafana: http://localhost:3000"
    echo "   Default credentials: admin/admin"
fi

# Test 6: Real-time monitoring test
echo ""
echo "📊 Test 6: Real-time monitoring test..."
echo "   Generating some load to test metrics collection..."
for i in {1..10}; do
    curl -s http://localhost:8000/health > /dev/null 2>&1 || true
    sleep 0.5
done

echo "   Waiting 5 seconds for metrics to update..."
sleep 5

# Check if metrics are updating
METRICS_COUNT=$(curl -s http://localhost:8000/api/v2/metrics/prometheus | wc -l)
if [ "$METRICS_COUNT" -gt 5 ]; then
    echo -e "${GREEN}✅ Metrics are being collected (found $METRICS_COUNT metric lines)${NC}"
else
    echo -e "${YELLOW}⚠️  Few metrics found. Check if metrics are being exported.${NC}"
fi

# Summary
echo ""
echo "=========================================="
echo -e "${GREEN}✅ MONITORING TEST COMPLETE${NC}"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo "  - Backend Metrics: http://localhost:8000/api/v2/metrics/prometheus"
echo ""
echo "Next steps:"
echo "  1. Open Grafana and import dashboard from: deployment/monitoring/grafana/dashboards/"
echo "  2. Configure alerts in Prometheus (optional)"
echo "  3. Set up Grafana alerting rules (optional)"
echo ""

