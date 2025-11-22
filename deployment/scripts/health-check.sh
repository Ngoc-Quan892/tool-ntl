#!/bin/bash
# ==================== HEALTH CHECK SCRIPT ====================
# Comprehensive health check for all services
# Usage: ./health-check.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  BACCARAT PREDICTOR - HEALTH CHECK"
echo "=========================================="
echo ""

cd "$DEPLOYMENT_DIR/.." || exit 1

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker Compose
echo "🔍 Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose available${NC}"

# Check if services are running
echo ""
echo "🔍 Checking container status..."
if ! docker-compose -f deployment/docker-compose.prod.yml ps | grep -q "Up"; then
    echo -e "${RED}❌ No services are running${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Services are running${NC}"

# Check PostgreSQL
echo ""
echo "🔍 Checking PostgreSQL..."
if docker-compose -f deployment/docker-compose.prod.yml exec -T postgres pg_isready -U baccarat_user > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is healthy${NC}"
else
    echo -e "${RED}❌ PostgreSQL is not responding${NC}"
    exit 1
fi

# Check Redis
echo ""
echo "🔍 Checking Redis..."
if docker-compose -f deployment/docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is healthy${NC}"
else
    echo -e "${RED}❌ Redis is not responding${NC}"
    exit 1
fi

# Check Backend
echo ""
echo "🔍 Checking Backend..."
BACKEND_HEALTH=$(docker-compose -f deployment/docker-compose.prod.yml exec -T backend curl -s http://localhost:8000/health 2>/dev/null || echo "failed")
if [[ "$BACKEND_HEALTH" == *"healthy"* ]] || [[ "$BACKEND_HEALTH" == *"status"* ]]; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
    echo "   Response: $BACKEND_HEALTH"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    echo "   Response: $BACKEND_HEALTH"
    exit 1
fi

# Check Frontend
echo ""
echo "🔍 Checking Frontend..."
if curl -f http://localhost/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is accessible${NC}"
else
    echo -e "${RED}❌ Frontend is not accessible${NC}"
    exit 1
fi

# Check Nginx
echo ""
echo "🔍 Checking Nginx..."
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Nginx is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Nginx health endpoint not accessible (may be normal)${NC}"
fi

# Check API endpoint
echo ""
echo "🔍 Checking API endpoint..."
if curl -f http://localhost/api/v2/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API endpoint is accessible${NC}"
else
    echo -e "${RED}❌ API endpoint is not accessible${NC}"
    exit 1
fi

# Summary
echo ""
echo "=========================================="
echo -e "${GREEN}✅ All health checks passed!${NC}"
echo "=========================================="
echo ""
echo "Service Status:"
docker-compose -f deployment/docker-compose.prod.yml ps
echo ""

