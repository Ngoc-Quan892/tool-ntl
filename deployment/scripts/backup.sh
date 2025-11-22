#!/bin/bash
# ==================== BACKUP SCRIPT ====================
# Create backup of current deployment state
# Usage: ./backup.sh [backup_name]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"

BACKUP_NAME="${1:-manual_$(date +%Y%m%d_%H%M%S)}"
BACKUP_DIR="deployment/backups/$BACKUP_NAME"

echo "=========================================="
echo "  BACCARAT PREDICTOR - BACKUP SCRIPT"
echo "=========================================="
echo ""

cd "$DEPLOYMENT_DIR/.." || exit 1

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup: $BACKUP_DIR"
echo ""

# Backup Docker Compose configuration
echo "💾 Saving Docker Compose configuration..."
docker-compose -f deployment/docker-compose.prod.yml config > "$BACKUP_DIR/compose-config.yaml" 2>/dev/null || true

# Backup container status
echo "💾 Saving container status..."
docker-compose -f deployment/docker-compose.prod.yml ps > "$BACKUP_DIR/containers.txt" 2>/dev/null || true

# Backup image information
echo "💾 Saving image information..."
docker images | grep -E "(baccarat|backend|frontend)" > "$BACKUP_DIR/images.txt" 2>/dev/null || true
docker-compose -f deployment/docker-compose.prod.yml config | grep -E "image:" > "$BACKUP_DIR/image-tags.txt" 2>/dev/null || true

# Backup environment file (if exists)
if [ -f "deployment/.env.production" ]; then
    echo "💾 Saving environment configuration (without secrets)..."
    # Remove sensitive values for backup
    grep -v -E "(PASSWORD|SECRET|KEY)" deployment/.env.production > "$BACKUP_DIR/env-example.txt" 2>/dev/null || true
fi

# Backup database (if PostgreSQL is running)
if docker-compose -f deployment/docker-compose.prod.yml ps postgres | grep -q "Up"; then
    echo "💾 Backing up database..."
    docker-compose -f deployment/docker-compose.prod.yml exec -T postgres pg_dump -U baccarat_user baccarat > "$BACKUP_DIR/database.sql" 2>/dev/null || echo "⚠️  Database backup failed (may be normal if using SQLite)"
fi

# Create backup info file
cat > "$BACKUP_DIR/backup-info.txt" << EOF
Backup created: $(date)
Backup name: $BACKUP_NAME
Git commit: $(git rev-parse HEAD 2>/dev/null || echo "N/A")
Git branch: $(git branch --show-current 2>/dev/null || echo "N/A")
EOF

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

echo ""
echo "=========================================="
echo "✅ Backup completed successfully!"
echo "=========================================="
echo ""
echo "Backup location: $BACKUP_DIR"
echo "Backup size: $BACKUP_SIZE"
echo ""
echo "Backup contents:"
ls -lh "$BACKUP_DIR"
echo ""

