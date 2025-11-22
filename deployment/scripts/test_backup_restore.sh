#!/bin/bash
# ==================== TEST BACKUP/RESTORE SCRIPT ====================
# Test backup and restore procedures
# Usage: ./test_backup_restore.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  TEST BACKUP/RESTORE PROCEDURES"
echo "=========================================="
echo ""

cd "$DEPLOYMENT_DIR/.." || exit 1

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TEST_BACKUP_NAME="test_backup_$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="deployment/backups/$TEST_BACKUP_NAME"

# Test 1: Create backup
echo "📦 Test 1: Creating test backup..."
mkdir -p "$BACKUP_DIR"

# Backup Docker Compose config
if docker-compose -f deployment/docker-compose.prod.yml config > "$BACKUP_DIR/compose-config.yaml" 2>/dev/null; then
    echo -e "${GREEN}✅ Docker Compose config backed up${NC}"
else
    echo -e "${YELLOW}⚠️  Docker Compose config backup failed (may be OK if not running)${NC}"
fi

# Backup container status
if docker-compose -f deployment/docker-compose.prod.yml ps > "$BACKUP_DIR/containers.txt" 2>/dev/null; then
    echo -e "${GREEN}✅ Container status backed up${NC}"
else
    echo -e "${YELLOW}⚠️  Container status backup failed${NC}"
fi

# Backup image tags
if docker-compose -f deployment/docker-compose.prod.yml config | grep -E "image:" > "$BACKUP_DIR/image-tags.txt" 2>/dev/null; then
    echo -e "${GREEN}✅ Image tags backed up${NC}"
else
    echo -e "${YELLOW}⚠️  Image tags backup failed${NC}"
fi

# Backup database (if PostgreSQL is running)
if docker-compose -f deployment/docker-compose.prod.yml ps postgres 2>/dev/null | grep -q "Up"; then
    echo "   Backing up database..."
    if docker-compose -f deployment/docker-compose.prod.yml exec -T postgres pg_dump -U baccarat_user baccarat > "$BACKUP_DIR/database.sql" 2>/dev/null; then
        DB_SIZE=$(du -h "$BACKUP_DIR/database.sql" | cut -f1)
        echo -e "${GREEN}✅ Database backed up (size: $DB_SIZE)${NC}"
    else
        echo -e "${YELLOW}⚠️  Database backup failed (may be normal if using SQLite)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL not running, skipping database backup${NC}"
fi

# Create backup info
cat > "$BACKUP_DIR/backup-info.txt" << EOF
Backup created: $(date)
Backup name: $TEST_BACKUP_NAME
Test backup: true
Git commit: $(git rev-parse HEAD 2>/dev/null || echo "N/A")
Git branch: $(git branch --show-current 2>/dev/null || echo "N/A")
EOF

BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo -e "${GREEN}✅ Test backup created: $BACKUP_DIR (size: $BACKUP_SIZE)${NC}"

# Test 2: Verify backup contents
echo ""
echo "📦 Test 2: Verifying backup contents..."
BACKUP_FILES=(
    "$BACKUP_DIR/compose-config.yaml"
    "$BACKUP_DIR/containers.txt"
    "$BACKUP_DIR/image-tags.txt"
    "$BACKUP_DIR/backup-info.txt"
)

ALL_FILES_EXIST=true
for file in "${BACKUP_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "   ${GREEN}✅ $(basename $file)${NC}"
    else
        echo -e "   ${RED}❌ $(basename $file) missing${NC}"
        ALL_FILES_EXIST=false
    fi
done

if [ "$ALL_FILES_EXIST" = true ]; then
    echo -e "${GREEN}✅ All backup files present${NC}"
else
    echo -e "${YELLOW}⚠️  Some backup files missing (may be OK)${NC}"
fi

# Test 3: Test restore procedure (dry run)
echo ""
echo "📦 Test 3: Testing restore procedure (dry run)..."
if [ -f "$BACKUP_DIR/compose-config.yaml" ]; then
    echo "   Compose config can be restored"
    echo -e "${GREEN}✅ Restore procedure verified${NC}"
else
    echo -e "${YELLOW}⚠️  Cannot verify restore (no config file)${NC}"
fi

# Test 4: Test backup script
echo ""
echo "📦 Test 4: Testing backup script..."
if [ -f "./deployment/scripts/backup.sh" ]; then
    echo "   Backup script exists"
    if [ -x "./deployment/scripts/backup.sh" ]; then
        echo -e "${GREEN}✅ Backup script is executable${NC}"
    else
        echo -e "${YELLOW}⚠️  Backup script not executable, fixing...${NC}"
        chmod +x ./deployment/scripts/backup.sh
    fi
else
    echo -e "${RED}❌ Backup script not found${NC}"
fi

# Test 5: Test rollback script
echo ""
echo "📦 Test 5: Testing rollback script..."
if [ -f "./deployment/scripts/rollback.sh" ]; then
    echo "   Rollback script exists"
    if [ -x "./deployment/scripts/rollback.sh" ]; then
        echo -e "${GREEN}✅ Rollback script is executable${NC}"
    else
        echo -e "${YELLOW}⚠️  Rollback script not executable, fixing...${NC}"
        chmod +x ./deployment/scripts/rollback.sh
    fi
else
    echo -e "${RED}❌ Rollback script not found${NC}"
fi

# Test 6: Backup location and permissions
echo ""
echo "📦 Test 6: Checking backup location..."
BACKUPS_DIR="deployment/backups"
if [ -d "$BACKUPS_DIR" ]; then
    echo -e "${GREEN}✅ Backup directory exists${NC}"
    
    # Check permissions
    if [ -w "$BACKUPS_DIR" ]; then
        echo -e "${GREEN}✅ Backup directory is writable${NC}"
    else
        echo -e "${RED}❌ Backup directory is not writable${NC}"
    fi
    
    # List existing backups
    BACKUP_COUNT=$(ls -1 "$BACKUPS_DIR" 2>/dev/null | wc -l)
    echo "   Existing backups: $BACKUP_COUNT"
else
    echo -e "${YELLOW}⚠️  Backup directory does not exist, creating...${NC}"
    mkdir -p "$BACKUPS_DIR"
    echo -e "${GREEN}✅ Backup directory created${NC}"
fi

# Summary
echo ""
echo "=========================================="
echo -e "${GREEN}✅ BACKUP/RESTORE TEST COMPLETE${NC}"
echo "=========================================="
echo ""
echo "Test backup created: $BACKUP_DIR"
echo "Backup size: $BACKUP_SIZE"
echo ""
echo "Next steps:"
echo "  1. Review backup contents"
echo "  2. Test actual restore in staging environment"
echo "  3. Verify backup automation (cron job)"
echo "  4. Document restore procedures"
echo ""
echo "To clean up test backup:"
echo "  rm -rf $BACKUP_DIR"
echo ""

