#!/usr/bin/env bash
set -euo pipefail

# Clay Webhook OS — Backup Script
# Backs up data, clients, knowledge base, and skills to timestamped archives.
# Retains the last 7 backups. Run via cron for daily backups:
#   0 3 * * * /opt/clay-webhook-os/scripts/backup.sh >> /var/log/clay-backup.log 2>&1

PROJECT_DIR="/opt/clay-webhook-os"
BACKUP_DIR="/opt/backups/clay-webhook-os"
RETENTION_DAYS=7
TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')
ARCHIVE="$BACKUP_DIR/clay-backup-$TIMESTAMP.tar.gz"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# Create backup directory
mkdir -p "$BACKUP_DIR"

log "=== Starting backup ==="

# Create archive of critical directories
tar -czf "$ARCHIVE" \
    -C "$PROJECT_DIR" \
    data/ \
    clients/ \
    knowledge_base/ \
    skills/ \
    pipelines/ \
    functions/ \
    2>/dev/null || true

ARCHIVE_SIZE=$(du -h "$ARCHIVE" | cut -f1)
log "Backup created: $ARCHIVE ($ARCHIVE_SIZE)"

# Prune old backups
DELETED=$(find "$BACKUP_DIR" -name "clay-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    log "Pruned $DELETED backup(s) older than $RETENTION_DAYS days"
fi

REMAINING=$(find "$BACKUP_DIR" -name "clay-backup-*.tar.gz" | wc -l)
log "=== Backup complete ($REMAINING archives retained) ==="
