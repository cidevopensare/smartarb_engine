#!/bin/bash
# diagnose_system.sh - Diagnosi completa del sistema SmartArb

echo "🔍 SmartArb Engine - System Diagnosis"
echo "====================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}1. 📊 Process Status${NC}"
echo "===================="

# Check if engine process is running
if [ -f .engine.pid ]; then
    PID=$(cat .engine.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Engine PID: $PID (running)${NC}"
        echo "   Memory: $(ps -p $PID -o rss= | awk '{print int($1/1024)"MB"}')"
        echo "   CPU: $(ps -p $PID -o %cpu=)%"
        echo "   Command: $(ps -p $PID -o comm=)"
    else
        echo -e "${RED}❌ Engine PID: $PID (dead process)${NC}"
        rm -f .engine.pid
    fi
else
    echo -e "${YELLOW}⚠️ No engine PID file found${NC}"
fi

# Check for any SmartArb processes
echo ""
echo "🔍 All SmartArb processes:"
ps aux | grep -E "(smartarb|unified_engine|src\.core)" | grep -v grep || echo "   No SmartArb processes found"

echo ""
echo -e "${BLUE}2. 🌐 Network Status${NC}"
echo "==================="

# Check ports
echo "Port status:"
if lsof -i:8001 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Port 8001 (Dashboard): Active${NC}"
    lsof -i:8001 | grep LISTEN || true
else
    echo -e "${RED}❌ Port 8001 (Dashboard): Not in use${NC}"
fi

if lsof -i:8000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Port 8000 (API): Active${NC}"  
    lsof -i:8000 | grep LISTEN || true
else
    echo -e "${YELLOW}⚠️ Port 8000 (API): Not in use${NC}"
fi

# Test dashboard connectivity
echo ""
echo "Dashboard connectivity test:"
if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:8001 | grep -q "200"; then
    echo -e "${GREEN}✅ Dashboard: Responding (HTTP 200)${NC}"
elif curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:8001 | grep -q "404\|500"; then
    echo -e "${YELLOW}⚠️ Dashboard: Server running but errors (HTTP $(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:8001))${NC}"
else
    echo -e "${RED}❌ Dashboard: Not responding${NC}"
fi

# Test API endpoint
echo ""
echo "API endpoint test:"
if curl -s --connect-timeout 5 http://localhost:8001/api/metrics | python3 -m json.tool > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API: Responding with valid JSON${NC}"
    echo "   Metrics preview:"
    curl -s --connect-timeout 5 http://localhost:8001/api/metrics | python3 -m json.tool | head -10 | sed 's/^/   /'
else
    echo -e "${RED}❌ API: Not responding or invalid JSON${NC}"
fi

echo ""
echo -e "${BLUE}3. 📱 Telegram Configuration${NC}"
echo "============================"

# Check Telegram credentials
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "   Create .env with your Telegram credentials"
else
    echo -e "${GREEN}✅ .env file exists${NC}"
    
    if grep -q "TELEGRAM_BOT_TOKEN" .env && [ -n "$(grep TELEGRAM_BOT_TOKEN .env | cut -d'=' -f2)" ]; then
        TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d'=' -f2 | tr -d '"'"'"' ')
        if [ ${#TOKEN} -gt 20 ]; then
            echo -e "${GREEN}✅ Bot token: Configured (${#TOKEN} chars)${NC}"
        else
            echo -e "${YELLOW}⚠️ Bot token: Too short, might be invalid${NC}"
        fi
    else
        echo -e "${RED}❌ Bot token: Not configured${NC}"
    fi
    
    if grep -q "TELEGRAM_CHAT_ID" .env && [ -n "$(grep TELEGRAM_CHAT_ID .env | cut -d'=' -f2)" ]; then
        CHAT_ID=$(grep TELEGRAM_CHAT_ID .env | cut -d'=' -f2 | tr -d '"'"'"' ')
        echo -e "${GREEN}✅ Chat ID: Configured ($CHAT_ID)${NC}"
    else
        echo -e "${RED}❌ Chat ID: Not configured${NC}"
    fi
fi

# Test Telegram connectivity
echo ""
echo "Telegram connectivity test:"
if [ -f "test_telegram_direct.py" ]; then
    echo "Running Telegram test..."
    timeout 10s python3 test_telegram_direct.py 2>&1 | head -5 | sed 's/^/   /'
else
    echo -e "${YELLOW}⚠️ test_telegram_direct.py not found${NC}"
fi

echo ""
echo -e "${BLUE}4. 📋 Log Analysis${NC}"
echo "=================="

# Check recent logs
echo "Recent engine logs:"
if [ -f "logs/unified_engine.log" ]; then
    echo -e "${GREEN}✅ unified_engine.log exists${NC}"
    echo "   Last 10 lines:"
    tail -10 logs/unified_engine.log | sed 's/^/   /' || echo "   Error reading log"
elif [ -f "logs/engine.log" ]; then
    echo -e "${YELLOW}⚠️ Using fallback engine.log${NC}"
    echo "   Last 10 lines:"
    tail -10 logs/engine.log | sed 's/^/   /' || echo "   Error reading log"
else
    echo -e "${RED}❌ No engine logs found${NC}"
fi

echo ""
echo "Error analysis:"
if find logs/ -name "*.log" -exec grep -l -i "error\|exception\|failed" {} \; 2>/dev/null | head -3; then
    echo "   Recent errors found in logs:"
    find logs/ -name "*.log" -exec grep -i "error\|exception\|failed" {} \; 2>/dev/null | tail -5 | sed 's/^/   /'
else
    echo -e "${GREEN}✅ No recent errors in logs${NC}"
fi

echo ""
echo -e "${BLUE}5. 🗂️ File Structure${NC}"  
echo "==================="

# Check critical files
critical_files=(
    "src/core/unified_engine.py"
    "src/ai/ai_integration.py"
    "src/ai/ai_advisor.py"
    ".env"
    "Makefile"
)

for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        size=$(ls -lh "$file" | awk '{print $5}')
        echo -e "${GREEN}✅ $file ($size)${NC}"
    else
        echo -e "${RED}❌ $file (missing)${NC}"
    fi
done

echo ""
echo -e "${BLUE}6. 💾 System Resources${NC}"
echo "====================="

# System resources
echo "System status:"
echo "   CPU: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}' 2>/dev/null || echo "N/A")"
echo "   Memory: $(free -m | awk 'NR==2{printf "%.1f%% (%d/%d MB)", $3*100/$2, $3, $2}' 2>/dev/null || echo "N/A")"
echo "   Disk: $(df -h . | awk 'NR==2{print $5 " (" $3"/" $2 ")"}')"
echo "   Load: $(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')"

echo ""
echo -e "${BLUE}7. 🔧 Recommendations${NC}"
echo "====================="

# Generate recommendations
recommendations=()

if ! ps aux | grep -E "(unified_engine|src\.core)" | grep -v grep > /dev/null; then
    recommendations+=("🚀 Start the engine: make start-with-ai")
fi

if ! lsof -i:8001 > /dev/null 2>&1; then
    recommendations+=("📊 Dashboard not running - check unified_engine.py")
fi

if [ ! -f ".env" ] || ! grep -q "TELEGRAM_BOT_TOKEN" .env; then
    recommendations+=("📱 Configure Telegram: Add TELEGRAM_BOT_TOKEN to .env")
fi

if find logs/ -name "*.log" -exec grep -l -i "error" {} \; 2>/dev/null | head -1 > /dev/null; then
    recommendations+=("📋 Check logs for errors: make logs")
fi

if [ ${#recommendations[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ System appears healthy!${NC}"
else
    echo "Recommended actions:"
    for rec in "${recommendations[@]}"; do
        echo "   $rec"
    done
fi

echo ""
echo -e "${GREEN}🎯 Quick Fix Commands:${NC}"
echo "======================"
echo "# Restart system:"
echo "make stop && make start-with-ai"
echo ""
echo "# Check detailed logs:"
echo "make logs-live"
echo ""
echo "# Test Telegram:"
echo "make test-telegram"
echo ""
echo "# System status:"
echo "make status"
