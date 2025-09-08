# Script backup completo (versione corretta per il tuo path)
#!/bin/bash

# Configurazione
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_ONLY=$(date +%Y%m%d)
BACKUP_DIR="/home/smartarb/smartarb_engine/backups"
PROJECT_DIR="/home/smartarb/smartarb_engine"
GITHUB_BACKUP_DIR="$BACKUP_DIR/github"

# Logging
LOG_FILE="$PROJECT_DIR/logs/backup.log"
mkdir -p "$(dirname "$LOG_FILE")"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "🔄 Starting backup process: $TIMESTAMP"

# 1. BACKUP LOCALE COMPLETO
echo "💾 Creating local backup..."
tar -czf "$BACKUP_DIR/daily/smartarb_complete_$TIMESTAMP.tar.gz" \
    --exclude="backups" \
    --exclude="logs/*.log" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude=".git" \
    "$PROJECT_DIR/"

# Backup configurazioni critiche
cp "$PROJECT_DIR/.env" "$BACKUP_DIR/daily/env_$TIMESTAMP.backup" 2>/dev/null || true
cp -r "$PROJECT_DIR/config/" "$BACKUP_DIR/daily/config_$TIMESTAMP/" 2>/dev/null || true

echo "✅ Local backup completed"

# 2. CLEANUP VECCHI BACKUP
echo "🧹 Cleaning old backups..."
find "$BACKUP_DIR/daily" -name "*.tar.gz" -mtime +7 -delete 2>/dev/null || true
find "$BACKUP_DIR/daily" -name "*.backup" -mtime +7 -delete 2>/dev/null || true
find "$BACKUP_DIR/daily" -type d -name "config_*" -mtime +7 -exec rm -rf {} \; 2>/dev/null || true

# 3. VERIFICA INTEGRITÀ
echo "🔍 Verifying backup integrity..."
if tar -tzf "$BACKUP_DIR/daily/smartarb_complete_$TIMESTAMP.tar.gz" >/dev/null 2>&1; then
    echo "✅ Backup integrity verified"
else
    echo "❌ Backup corrupted!"
    exit 1
fi

# 4. STATISTICHE
BACKUP_SIZE=$(du -sh "$BACKUP_DIR/daily/smartarb_complete_$TIMESTAMP.tar.gz" | cut -f1)
TOTAL_BACKUPS=$(ls -1 "$BACKUP_DIR/daily"/*.tar.gz 2>/dev/null | wc -l)

echo "📊 Backup Stats:"
echo "   Size: $BACKUP_SIZE"
echo "   Total backups: $TOTAL_BACKUPS"
echo "   Status: ✅ SUCCESS"
echo "🏁 Backup process completed: $(date)"

# 5. Optional: Telegram notification
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import os
import requests
import json
from datetime import datetime

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

if token and chat_id:
    try:
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        data = {
            'chat_id': chat_id,
            'text': f'🔄 Daily backup completed\nSize: $BACKUP_SIZE\nTime: {datetime.now().strftime(\"%H:%M\")}\nSystem: SmartArb Engine'
        }
        requests.post(url, json=data, timeout=5)
    except:
        pass
" 2>/dev/null || true
fi
