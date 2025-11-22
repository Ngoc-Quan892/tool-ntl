#!/bin/bash
# ==================== ROLLBACK SCRIPT ====================
# Manual rollback script for production deployment
# Usage: ./rollback.sh [backup_directory]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${1:-latest}"

echo "=========================================="
echo "  BACCARAT PREDICTOR - ROLLBACK SCRIPT"
echo "=========================================="
echo ""

# Change to deployment directory
cd "$DEPLOYMENT_DIR/.." || exit 1

# Find latest backup if not specified
if [ "$BACKUP_DIR" == "latest" ]; then
    if [ ! -d "deployment/backups" ]; then
        echo "❌ No backups directory found!"
        exit 1
    fi
    
    BACKUP_DIR=$(ls -t deployment/backups/ 2>/dev/null | head -1)
    if [ -z "$BACKUP_DIR" ]; then
        echo "❌ No backups found!"
        exit 1
    fi
    echo "📦 Using latest backup: $BACKUP_DIR"
else
    if [ ! -d "deployment/backups/$BACKUP_DIR" ]; then
        echo "❌ Backup directory not found: deployment/backups/$BACKUP_DIR"
        echo "Available backups:"
        ls -lt deployment/backups/ 2>/dev/null | head -10 || echo "  (none)"
        exit 1
    fi
    echo "📦 Using backup: $BACKUP_DIR"
fi

echo ""
echo "⚠️  WARNING: This will rollback to a previous version!"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Rollback cancelled"
    exit 0
fi

echo ""
echo "🔄 Starting rollback process..."

# Show current deployment status
echo ""
echo "📊 Current deployment status:"
docker-compose -f deployment/docker-compose.prod.yml ps || true

# Stop current services gracefully
echo ""
echo "🛑 Stopping current services..."
docker-compose -f deployment/docker-compose.prod.yml stop backend frontend || true

# Backup current state before rollback (in case we need to rollback the rollback)
CURRENT_BACKUP="deployment/backups/pre_rollback_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$CURRENT_BACKUP"
docker-compose -f deployment/docker-compose.prod.yml config > "$CURRENT_BACKUP/compose-config.yaml" || true
docker-compose -f deployment/docker-compose.prod.yml ps > "$CURRENT_BACKUP/containers.txt" || true
echo "💾 Current state backed up to: $CURRENT_BACKUP"

# Restore from backup
echo ""
echo "📥 Restoring from backup: deployment/backups/$BACKUP_DIR"

# Check if we have image tags to restore
if [ -f "deployment/backups/$BACKUP_DIR/image-tags.txt" ]; then
    echo "📋 Previous image tags:"
    cat "deployment/backups/$BACKUP_DIR/image-tags.txt"
fi

# Restart services (they will use previous images if available)
echo ""
echo "🚀 Restarting services..."
docker-compose -f deployment/docker-compose.prod.yml up -d backend frontend

# Wait for health checks
echo ""
echo "⏳ Waiting for health checks..."
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
    echo "⚠️  Services may not be fully operational"
    echo ""
    echo "Current container status:"
    docker-compose -f deployment/docker-compose.prod.yml ps
    exit 1
fi

# Verify all services
echo ""
echo "🔍 Verifying all services..."
docker-compose -f deployment/docker-compose.prod.yml ps

# Check backend health specifically
echo ""
echo "🔍 Checking backend health..."
BACKEND_HEALTH=$(docker-compose -f deployment/docker-compose.prod.yml exec -T backend curl -s http://localhost:8000/health || echo "failed")
if [[ "$BACKEND_HEALTH" == *"healthy"* ]] || [[ "$BACKEND_HEALTH" == *"status"* ]]; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend health check returned: $BACKEND_HEALTH"
fi

echo ""
echo "=========================================="
echo "✅ Rollback completed successfully!"
echo "=========================================="
echo ""
echo "Rolled back to: deployment/backups/$BACKUP_DIR"
echo "Pre-rollback state saved to: $CURRENT_BACKUP"
echo ""
echo "To verify deployment:"
echo "  curl http://localhost/health"
echo "  docker-compose -f deployment/docker-compose.prod.yml ps"
echo ""

