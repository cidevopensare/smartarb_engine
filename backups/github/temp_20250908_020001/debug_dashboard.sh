#!/bin/bash
# debug_dashboard.sh - Debug e riavvio dashboard

echo "🔍 SmartArb Dashboard - Debug e Fix"
echo "==================================="

# Colori
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Controlla processo attuale
echo "1. 📊 Checking dashboard process..."
if ps aux | grep -q "dashboard_server.py"; then
    echo -e "${GREEN}✅ Dashboard process found${NC}"
    ps aux | grep "dashboard_server.py" | grep -v grep
else
    echo -e "${RED}❌ Dashboard process not running${NC}"
fi

# 2. Controlla porta 8001
echo ""
echo "2. 🔌 Checking port 8001..."
if sudo netstat -tlnp | grep -q ":8001"; then
    echo -e "${GREEN}✅ Port 8001 is occupied${NC}"
    sudo netstat -tlnp | grep ":8001"
else
    echo -e "${RED}❌ Port 8001 is free${NC}"
fi

# 3. Controlla logs
echo ""
echo "3. 📋 Dashboard logs (last 10 lines)..."
if [ -f logs/dashboard.log ]; then
    echo -e "${YELLOW}--- Dashboard Log ---${NC}"
    tail -10 logs/dashboard.log
else
    echo -e "${RED}❌ Dashboard log not found${NC}"
fi

# 4. Termina processi esistenti
echo ""
echo "4. 🛑 Killing existing dashboard processes..."
pkill -f "dashboard_server.py" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
sleep 2

# 5. Test semplice per vedere se Python può importare le librerie
echo ""
echo "5. 🐍 Testing Python imports..."
python3 -c "
try:
    import fastapi
    print('✅ FastAPI: OK')
except ImportError:
    print('❌ FastAPI: NOT FOUND')

try:
    import uvicorn
    print('✅ Uvicorn: OK')
except ImportError:
    print('❌ Uvicorn: NOT FOUND')
    
try:
    import psutil
    print('✅ psutil: OK')
except ImportError:
    print('⚠️ psutil: NOT FOUND (will use mock data)')
"

# 6. Crea una dashboard semplificata per test
echo ""
echo "6. 🔧 Creating simplified dashboard for testing..."
cat > test_simple_dashboard.py << 'EOF'
#!/usr/bin/env python3
"""
Simple test dashboard to verify the setup
"""
try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    import uvicorn
    import json
    import time
    
    app = FastAPI(title="SmartArb Test Dashboard")
    
    @app.get("/")
    async def root():
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>SmartArb Test Dashboard</title></head>
        <body style="font-family: Arial; background: #000; color: #fff; padding: 20px;">
            <h1>🚀 SmartArb Test Dashboard</h1>
            <p>✅ Dashboard server is working!</p>
            <p>📊 <a href="/api/metrics" style="color: #00ff88;">View Metrics API</a></p>
            <script>
                setTimeout(() => {
                    fetch('/api/metrics')
                        .then(r => r.json())
                        .then(data => {
                            document.body.innerHTML += '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        });
                }, 1000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)
    
    @app.get("/api/metrics")
    async def metrics():
        return {
            "status": "OK",
            "timestamp": time.time(),
            "trades_executed": 47,
            "success_rate": 87.3,
            "total_profit": 156.43,
            "daily_pnl": 32.18,
            "memory_usage": 45.2,
            "cpu_usage": 15.8,
            "message": "SmartArb Dashboard Test - All systems operational!"
        }
    
    if __name__ == "__main__":
        print("🧪 Starting SmartArb Test Dashboard on port 8001...")
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Try: pip3 install fastapi uvicorn")
EOF

# 7. Testa la dashboard semplice
echo ""
echo "7. 🧪 Testing simple dashboard..."
chmod +x test_simple_dashboard.py

echo "Starting test dashboard in background..."
python3 test_simple_dashboard.py > logs/test_dashboard.log 2>&1 &
TEST_PID=$!
echo "Test dashboard PID: $TEST_PID"

# Aspetta che si avvii
sleep 5

# 8. Testa se risponde
echo ""
echo "8. 🔍 Testing dashboard response..."
if curl -s http://localhost:8001/api/metrics > /dev/null; then
    echo -e "${GREEN}✅ Dashboard responds on port 8001!${NC}"
    echo "📊 API Response:"
    curl -s http://localhost:8001/api/metrics | python3 -m json.tool
    echo ""
    echo -e "${GREEN}🎉 Dashboard is working! Try: firefox http://localhost:8001${NC}"
else
    echo -e "${RED}❌ Dashboard still not responding${NC}"
    echo "📋 Test dashboard logs:"
    tail -5 logs/test_dashboard.log
fi

# 9. Risultato finale
echo ""
echo "📊 Final Status:"
echo "==============="
echo "🌐 Dashboard URL: http://localhost:8001"
echo "📋 Logs: logs/test_dashboard.log"
echo "🔧 Test PID: $TEST_PID (kill $TEST_PID to stop)"
echo ""
echo "🔍 To debug further:"
echo "  - Check logs: tail -f logs/test_dashboard.log"
echo "  - Test API: curl http://localhost:8001/api/metrics"
echo "  - Test browser: firefox http://localhost:8001"
