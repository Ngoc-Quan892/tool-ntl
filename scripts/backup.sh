#!/bin/bash
# Backup script for database and important data

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup..."

# Backup database
if [ -f "backend/data/baccarat.db" ]; then
    cp "backend/data/baccarat.db" "$BACKUP_DIR/baccarat_${TIMESTAMP}.db"
    echo "✅ Database backed up"
fi

# Backup configuration
tar -czf "$BACKUP_DIR/config_${TIMESTAMP}.tar.gz" \
    backend/.env \
    frontend/.env \
    deployment/ \
    2>/dev/null || true

echo "✅ Backup complete: $BACKUP_DIR"

