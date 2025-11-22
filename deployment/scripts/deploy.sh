#!/bin/bash
# ==================== DEPLOYMENT SCRIPT ====================
# Production deployment script with backup and health checks
# Usage: ./deploy.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  BACCARAT PREDICTOR - DEPLOYMENT SCRIPT"
echo "=========================================="
echo ""

# Change to project root directory
cd "$DEPLOYMENT_DIR/.." || exit 1

# Check if .env.production exists
if [ ! -f "deployment/.env.production" ]; then
    echo "❌ Error: deployment/.env.production not found!"
    echo "   Please copy deployment/env.example to deployment/.env.production"
    echo "   and configure it with your production values."
    exit 1
fi

# Create backups directory
mkdir -p deployment/backups

# Create backup with timestamp
BACKUP_DIR="deployment/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup..."
docker-compose -f deployment/docker-compose.prod.yml ps > "$BACKUP_DIR/containers.txt" 2>/dev/null || true
docker-compose -f deployment/docker-compose.prod.yml config > "$BACKUP_DIR/compose-config.yaml" 2>/dev/null || true
docker images | grep -E "(baccarat|backend|frontend)" > "$BACKUP_DIR/images.txt" 2>/dev/null || true
docker-compose -f deployment/docker-compose.prod.yml config | grep -E "image:" > "$BACKUP_DIR/image-tags.txt" 2>/dev/null || true
echo "✅ Backup created: $BACKUP_DIR"

# Pull latest images
echo ""
echo "📥 Pulling latest images..."
docker-compose -f deployment/docker-compose.prod.yml --env-file deployment/.env.production pull

# Build and deploy
echo ""
echo "🔨 Building and deploying..."
docker-compose -f deployment/docker-compose.prod.yml --env-file deployment/.env.production up -d --build

# Wait for services to start
echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Health checks with retries
echo ""
echo "🔍 Running health checks..."
MAX_RETRIES=30
RETRY_COUNT=0
HEALTH_CHECK_PASSED=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost/health > /dev/null 2>&1; then
        echo "✅ Health check passed!"
        HEALTH_CHECK_PASSED=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "   Retry $RETRY_COUNT/$MAX_RETRIES..."
    sleep 2
done

if [ "$HEALTH_CHECK_PASSED" = false ]; then
    echo ""
    echo "❌ Health check failed after $MAX_RETRIES retries"
    echo "⚠️  Deployment may have issues"
    echo ""
    echo "Container status:"
    docker-compose -f deployment/docker-compose.prod.yml ps
    echo ""
    echo "Logs:"
    docker-compose -f deployment/docker-compose.prod.yml logs --tail=50
    echo ""
    echo "To rollback, run:"
    echo "  ./deployment/scripts/rollback.sh $BACKUP_DIR"
    exit 1
fi

# Verify all services
echo ""
echo "🔍 Verifying all services..."
docker-compose -f deployment/docker-compose.prod.yml ps

# Check backend health
echo ""
echo "🔍 Checking backend health..."
BACKEND_HEALTH=$(docker-compose -f deployment/docker-compose.prod.yml exec -T backend curl -s http://localhost:8000/health || echo "failed")
if [[ "$BACKEND_HEALTH" == *"healthy"* ]] || [[ "$BACKEND_HEALTH" == *"status"* ]]; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend health check returned: $BACKEND_HEALTH"
fi

# Clean up old images (keep last 5 backups)
echo ""
echo "🧹 Cleaning up old backups (keeping last 5)..."
cd deployment/backups && ls -t | tail -n +6 | xargs rm -rf 2>/dev/null || true
cd ../..

# Clean up old Docker images
echo "🧹 Cleaning up old Docker images..."
docker image prune -f

echo ""
echo "=========================================="
echo "✅ Deployment completed successfully!"
echo "=========================================="
echo ""
echo "Backup saved to: $BACKUP_DIR"
echo ""
echo "To verify deployment:"
echo "  curl http://localhost/health"
echo "  docker-compose -f deployment/docker-compose.prod.yml ps"
echo ""
echo "To rollback if needed:"
echo "  ./deployment/scripts/rollback.sh $BACKUP_DIR"
echo ""

