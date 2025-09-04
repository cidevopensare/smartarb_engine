#!/bin/bash

# SmartArb Engine - Auto Git Push Script v3.0
# Gestisce branch divergenti automaticamente

PROJECT_DIR="/home/smartarb/smartarb_engine"
LOG_DIR="/home/smartarb/logs"

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$LOG_DIR"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_DIR/git_auto_push.log"
}

echo -e "${BLUE}🚀 SmartArb Engine - Git Auto Push v3.0${NC}"
echo "========================================"

cd "$PROJECT_DIR" || {
    echo -e "${RED}❌ Directory progetto non trovata${NC}"
    log_message "ERROR: Directory $PROJECT_DIR non trovata"
    exit 1
}

# Configura Git per gestire branch divergenti
echo -e "${YELLOW}⚙️  Configurazione Git...${NC}"
git config pull.rebase true
git config push.default simple
log_message "INFO: Configurazione Git completata"

# Fetch delle modifiche remote
echo -e "${YELLOW}🔄 Fetch repository remota...${NC}"
if ! git fetch origin main; then
    echo -e "${RED}❌ Errore durante fetch${NC}"
    log_message "ERROR: Errore durante git fetch"
    exit 1
fi

# Verifica stato repository
LOCAL_CHANGES=$(git status --porcelain | wc -l)
BEHIND=$(git rev-list HEAD..origin/main --count)
AHEAD=$(git rev-list origin/main..HEAD --count)

echo -e "${BLUE}📊 Stato repository:${NC}"
echo "   Modifiche locali: $LOCAL_CHANGES"
echo "   Commit da scaricare: $BEHIND"
echo "   Commit da caricare: $AHEAD"

# Se non ci sono modifiche locali E non siamo avanti
if [ "$LOCAL_CHANGES" -eq 0 ] && [ "$AHEAD" -eq 0 ]; then
    if [ "$BEHIND" -gt 0 ]; then
        echo -e "${YELLOW}📥 Solo aggiornamenti remoti - fast forward${NC}"
        git pull origin main
        echo -e "${GREEN}✅ Repository aggiornata${NC}"
    else
        echo -e "${GREEN}✅ Repository già sincronizzata${NC}"
    fi
    log_message "INFO: Repository sincronizzata senza modifiche locali"
    exit 0
fi

# Se ci sono modifiche locali, salvale temporaneamente
if [ "$LOCAL_CHANGES" -gt 0 ]; then
    echo -e "${YELLOW}💾 Salvataggio modifiche locali...${NC}"
    git add .
    if ! git stash push -m "Auto-stash $(date '+%Y-%m-%d %H:%M:%S')"; then
        echo -e "${RED}❌ Errore durante stash${NC}"
        log_message "ERROR: Errore durante git stash"
        exit 1
    fi
    STASHED=true
fi

# Se siamo indietro, aggiorna
if [ "$BEHIND" -gt 0 ]; then
    echo -e "${YELLOW}📥 Aggiornamento con $BEHIND commit remoti...${NC}"
    if ! git pull origin main; then
        echo -e "${RED}❌ Errore durante pull${NC}"
        log_message "ERROR: Errore durante git pull"
        
        # Ripristina stash in caso di errore
        if [ "$STASHED" = true ]; then
            echo -e "${YELLOW}🔄 Ripristino modifiche locali...${NC}"
            git stash pop
        fi
        exit 1
    fi
    echo -e "${GREEN}✅ Pull completato${NC}"
fi

# Ripristina modifiche locali se erano state salvate
if [ "$STASHED" = true ]; then
    echo -e "${YELLOW}🔄 Ripristino modifiche locali...${NC}"
    if ! git stash pop; then
        echo -e "${RED}❌ Conflitti durante ripristino - risoluzione manuale necessaria${NC}"
        echo -e "${YELLOW}💡 Usa: git status per vedere i conflitti${NC}"
        echo -e "${YELLOW}💡 Dopo risoluzione: git add . && git stash drop${NC}"
        log_message "WARNING: Conflitti durante stash pop - risoluzione manuale necessaria"
        exit 1
    fi
fi

# Controlla di nuovo se ci sono modifiche da committare
if [ -z "$(git status --porcelain)" ]; then
    echo -e "${GREEN}✅ Nessuna modifica da sincronizzare${NC}"
    log_message "INFO: Nessuna modifica dopo sincronizzazione"
    exit 0
fi

# Commit delle modifiche
echo -e "${YELLOW}📝 Creazione commit...${NC}"
FILES_CHANGED=$(git diff --cached --name-only 2>/dev/null | wc -l)
UNSTAGED_FILES=$(git diff --name-only | wc -l)
TOTAL_FILES=$((FILES_CHANGED + UNSTAGED_FILES))

git add .
COMMIT_MSG="Auto-update: $(date '+%Y-%m-%d %H:%M:%S') - $TOTAL_FILES files"

if git commit -m "$COMMIT_MSG"; then
    echo -e "${GREEN}✅ Commit creato: $COMMIT_MSG${NC}"
    log_message "SUCCESS: Commit creato - $COMMIT_MSG"
else
    echo -e "${RED}❌ Errore durante commit${NC}"
    log_message "ERROR: Errore durante git commit"
    exit 1
fi

# Push su GitHub
echo -e "${YELLOW}📤 Upload su GitHub...${NC}"
if git push origin main; then
    echo -e "${GREEN}🎉 Upload completato!${NC}"
    log_message "SUCCESS: Upload completato - $COMMIT_MSG"
else
    echo -e "${RED}❌ Errore durante push${NC}"
    log_message "ERROR: Errore durante git push"
    exit 1
fi

# Statistiche finali
echo -e "${BLUE}📊 Upload completato:${NC}"
echo "   Commit: $(git log -1 --format='%h - %s')"
echo "   Data: $(git log -1 --format='%cd' --date=format:'%Y-%m-%d %H:%M:%S')"
echo "   Files totali: $(git ls-files | wc -l)"

log_message "SUCCESS: Processo completato - Repository sincronizzata"
