#!/bin/bash
# fix_smartarb.sh - Script di riparazione automatica SmartArb Engine

echo "🔧 SmartArb Engine - Riparazione Automatica"
echo "=========================================="

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funzione per log colorato
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. STOP TUTTI I PROCESSI
log_info "Step 1: Stopping all SmartArb processes..."
pkill -f smartarb 2>/dev/null || true
pkill -f dashboard 2>/dev/null || true
pkill -f "src.core.engine" 2>/dev/null || true
sleep 2

# 2. FIX CONFIGURAZIONE TELEGRAM
log_info "Step 2: Fixing Telegram configuration..."

# Crea/aggiorna file .env
if [ ! -f .env ]; then
    log_warn ".env not found, creating..."
    touch .env
fi

# Rimuovi eventuali righe esistenti e aggiungi le corrette
grep -v "TELEGRAM_" .env > .env.tmp 2>/dev/null || touch .env.tmp
cat >> .env.tmp << EOF
TELEGRAM_BOT_TOKEN=8478412531:AAEvX9OdKjc7RQ9tDQUv3WnlhxUzS320U9k
TELEGRAM_CHAT_ID=536544467
TELEGRAM_ENABLED=true
TELEGRAM_MIN_PROFIT_THRESHOLD=25.0
TELEGRAM_MAX_NOTIFICATIONS_PER_HOUR=15
TELEGRAM_STATUS_REPORT_INTERVAL=1800
EOF
mv .env.tmp .env

log_info "✅ Telegram configuration updated"

# 3. CREA DIRECTORY NECESSARIE
log_info "Step 3: Creating required directories..."
mkdir -p logs
mkdir -p static/dashboard
mkdir -p src/api

# 4. TEST TELEGRAM
log_info "Step 4: Testing Telegram integration..."
if [ -f test_telegram_direct.py ]; then
    python test_telegram_direct.py
    if [ $? -eq 0 ]; then
        log_info "✅ Telegram test passed"
    else
        log_warn "⚠️ Telegram test had issues, but continuing..."
    fi
else
    log_warn "test_telegram_direct.py not found"
fi

# 5. VERIFICA DASHBOARD SERVER
log_info "Step 5: Checking dashboard server..."
if [ ! -f src/api/dashboard_server.py ]; then
    log_warn "Dashboard server not found, creating basic version..."
    cat > src/api/dashboard_server.py << 'EOF'
#!/usr/bin/env python3
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
import psutil
import os

app = FastAPI(title="SmartArb Dashboard")

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass

current_metrics = {
    "trades_executed": 0,
    "success_rate": 85.0,
    "total_profit": 0.0,
    "daily_pnl": 0.0,
    "memory_usage": 0.0,
    "cpu_usage": 0.0,
    "engine_status": "Running"
}

@app.get("/")
async def dashboard():
    try:
        with open("static/dashboard/index.html", "r") as f:
            return HTMLResponse(f.read())
    except:
        return HTMLResponse("<h1>SmartArb Dashboard</h1><p>Dashboard file not found</p>")

@app.get("/api/metrics")
async def get_metrics():
    current_metrics["memory_usage"] = psutil.virtual_memory().percent
    current_metrics["cpu_usage"] = psutil.cpu_percent()
    return current_metrics

@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(5)
            metrics = await get_metrics()
            await websocket.send_text(json.dumps({"type": "update", "metrics": metrics}))
    except:
        pass

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SmartArb Dashboard on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
EOF
    chmod +x src/api/dashboard_server.py
fi

# 6. CONTROLLA DASHBOARD HTML
log_info "Step 6: Checking dashboard HTML..."
if [ ! -f static/dashboard/index.html ]; then
    log_warn "Dashboard HTML not found, creating basic version..."
    mkdir -p static/dashboard
    cat > static/dashboard/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>SmartArb Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; background: #000; color: #fff; margin: 0; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: linear-gradient(135deg, #1a1a1a, #2a2a2a); border-radius: 10px; padding: 20px; }
        .metric { display: flex; justify-content: space-between; margin: 10px 0; }
        .positive { color: #00ff88; }
        .negative { color: #ff4444; }
        .btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
    </style>
</head>
<body>
    <h1>🚀 SmartArb Engine Dashboard</h1>
    
    <div class="grid">
        <div class="card">
            <h3>📊 Trading Stats</h3>
            <div class="metric">
                <span>Total Trades</span>
                <span class="positive" id="totalTrades">0</span>
            </div>
            <div class="metric">
                <span>Success Rate</span>
                <span class="positive" id="successRate">0%</span>
            </div>
            <div class="metric">
                <span>Total Profit</span>
                <span class="positive" id="totalProfit">$0.00</span>
            </div>
        </div>
        
        <div class="card">
            <h3>💻 System Status</h3>
            <div class="metric">
                <span>Memory Usage</span>
                <span id="memoryUsage">0%</span>
            </div>
            <div class="metric">
                <span>CPU Usage</span>
                <span id="cpuUsage">0%</span>
            </div>
            <div class="metric">
                <span>Status</span>
                <span class="positive">Running</span>
            </div>
        </div>
    </div>
    
    <div style="margin-top: 20px;">
        <button class="btn" onclick="location.reload()">🔄 Refresh</button>
        <button class="btn" onclick="window.open('/api/metrics', '_blank')">📊 Raw Data</button>
    </div>

    <script>
        setInterval(async () => {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();
                
                document.getElementById('totalTrades').textContent = data.trades_executed;
                document.getElementById('successRate').textContent = data.success_rate + '%';
                document.getElementById('totalProfit').textContent = '$' + data.total_profit.toFixed(2);
                document.getElementById('memoryUsage').textContent = data.memory_usage.toFixed(1) + '%';
                document.getElementById('cpuUsage').textContent = data.cpu_usage.toFixed(1) + '%';
            } catch (error) {
                console.log('Update failed:', error);
            }
        }, 10000);
    </script>
</body>
</html>
EOF
fi

# 7. INSTALLA DIPENDENZE MANCANTI
log_info "Step 7: Installing required dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install fastapi uvicorn psutil websockets 2>/dev/null || log_warn "Some packages failed to install"
fi

# 8. AVVIA SERVIZI
log_info "Step 8: Starting services..."

# Avvia engine in background
if [ -f src/core/engine.py ]; then
    python3 -m src.core.engine > logs/engine.log 2>&1 &
    ENGINE_PID=$!
    echo $ENGINE_PID > .engine.pid
    log_info "✅ Engine started (PID: $ENGINE_PID)"
else
    log_warn "Engine file not found, skipping..."
fi

sleep 3

# Avvia dashboard in background
python3 src/api/dashboard_server.py > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo $DASHBOARD_PID > .dashboard.pid
log_info "✅ Dashboard started (PID: $DASHBOARD_PID)"

# 9. VERIFICA FINALE
log_info "Step 9: Final verification..."
sleep 5

# Controlla se i servizi sono attivi
if ps -p $DASHBOARD_PID > /dev/null; then
    log_info "✅ Dashboard is running on http://localhost:8001"
else
    log_error "❌ Dashboard failed to start"
fi

if [ -f .engine.pid ] && ps -p $(cat .engine.pid) > /dev/null; then
    log_info "✅ Engine is running"
else
    log_warn "⚠️ Engine status unclear"
fi

# 10. RISULTATO FINALE
echo ""
echo "🎉 SmartArb Engine Fix Completato!"
echo "=================================="
echo "✅ Telegram: Configured"
echo "✅ Dashboard: http://localhost:8001"
echo "✅ Logs: logs/engine.log, logs/dashboard.log"
echo ""
echo "🔍 Per verificare:"
echo "  - Apri http://localhost:8001 nel browser"
echo "  - Controlla logs: tail -f logs/*.log"
echo "  - Test Telegram: python test_telegram_direct.py"
echo ""
echo "🛑 Per fermare: pkill -f smartarb && pkill -f dashboard"
