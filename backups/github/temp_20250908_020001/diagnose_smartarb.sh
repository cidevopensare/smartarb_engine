#!/bin/bash

# SmartArb Engine Diagnostic Script
# Verifica perché il bot è in modalità statica

echo "🔍 SmartArb Engine Diagnostic Tool"
echo "================================="
echo

PROJECT_DIR="$HOME/smartarb_engine"  # Auto-detect current user path
LOG_DIR="$PROJECT_DIR/logs"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
    fi
}

echo "1. 📁 Checking project structure..."
if [ -d "$PROJECT_DIR" ]; then
    echo -e "   Project directory: ${GREEN}Found${NC}"
else
    echo -e "   Project directory: ${RED}NOT Found${NC}"
    echo "   Please update PROJECT_DIR variable in script"
    exit 1
fi

echo
echo "2. 🔧 Checking configuration files..."

# Check settings.yaml
if [ -f "$PROJECT_DIR/config/settings.yaml" ]; then
    echo -e "   settings.yaml: ${GREEN}Found${NC}"
    
    # Check if exchanges are enabled
    enabled_exchanges=$(grep -A 20 "exchanges:" "$PROJECT_DIR/config/settings.yaml" | grep "enabled: true" | wc -l)
    if [ $enabled_exchanges -gt 0 ]; then
        echo -e "   Enabled exchanges: ${GREEN}$enabled_exchanges${NC}"
    else
        echo -e "   Enabled exchanges: ${RED}0 (PROBLEM!)${NC}"
        echo -e "   ${YELLOW}Solution: Set enabled: true for your exchanges${NC}"
    fi
else
    echo -e "   settings.yaml: ${RED}NOT Found${NC}"
    echo -e "   ${YELLOW}Solution: Copy from settings.yaml.example${NC}"
fi

# Check .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    echo -e "   .env file: ${GREEN}Found${NC}"
    
    # Check API keys (without showing values)
    api_keys_count=$(grep -c "API_KEY=" "$PROJECT_DIR/.env" | grep -v "^#" | wc -l)
    if [ $api_keys_count -gt 0 ]; then
        echo -e "   API Keys configured: ${GREEN}Yes${NC}"
    else
        echo -e "   API Keys configured: ${RED}No${NC}"
    fi
else
    echo -e "   .env file: ${RED}NOT Found${NC}"
    echo -e "   ${YELLOW}Solution: Create .env file with API keys${NC}"
fi

echo
echo "3. 🐳 Checking Docker/Container status..."

# Check if container is running
if docker ps | grep -q "smartarb"; then
    echo -e "   SmartArb container: ${GREEN}Running${NC}"
    
    # Get container logs (last 20 lines)
    echo "   Recent container logs:"
    docker logs --tail 20 $(docker ps | grep smartarb | awk '{print $1}') 2>/dev/null | sed 's/^/     /'
else
    echo -e "   SmartArb container: ${RED}Not Running${NC}"
    
    # Check if Python process is running
    if pgrep -f "smartarb" > /dev/null; then
        echo -e "   Python process: ${GREEN}Running${NC}"
    else
        echo -e "   Python process: ${RED}Not Running${NC}"
    fi
fi

echo
echo "4. 📋 Checking log files..."

if [ -d "$LOG_DIR" ]; then
    echo -e "   Log directory: ${GREEN}Found${NC}"
    
    # Find most recent log file
    recent_log=$(find "$LOG_DIR" -name "*.log" -type f -exec ls -lt {} + | head -1 | awk '{print $NF}')
    
    if [ -n "$recent_log" ]; then
        echo "   Most recent log: $recent_log"
        echo "   Last 10 log entries:"
        tail -10 "$recent_log" 2>/dev/null | sed 's/^/     /' || echo "     Cannot read log file"
        
        # Check for error patterns
        error_count=$(grep -i "error\|exception\|fail" "$recent_log" 2>/dev/null | wc -l)
        if [ $error_count -gt 0 ]; then
            echo -e "   ${RED}Found $error_count errors in logs${NC}"
            echo "   Recent errors:"
            grep -i "error\|exception\|fail" "$recent_log" | tail -5 | sed 's/^/     /'
        fi
    else
        echo -e "   Log files: ${RED}No log files found${NC}"
    fi
else
    echo -e "   Log directory: ${RED}NOT Found${NC}"
fi

echo
echo "5. 🔄 Checking process activity..."

# Check if there are recent trades or activities
if [ -n "$recent_log" ]; then
    # Look for trading activity in logs
    trade_activity=$(grep -i "trade\|order\|arbitrage\|opportunity" "$recent_log" 2>/dev/null | wc -l)
    if [ $trade_activity -gt 0 ]; then
        echo -e "   Trading activity: ${GREEN}$trade_activity entries${NC}"
    else
        echo -e "   Trading activity: ${RED}No trading activity found${NC}"
        echo -e "   ${YELLOW}This suggests the bot is in static mode${NC}"
    fi
    
    # Check for market data updates
    market_data=$(grep -i "price\|market\|websocket\|ticker" "$recent_log" 2>/dev/null | wc -l)
    if [ $market_data -gt 0 ]; then
        echo -e "   Market data updates: ${GREEN}$market_data entries${NC}"
    else
        echo -e "   Market data updates: ${RED}No market data found${NC}"
        echo -e "   ${YELLOW}Market data feed might be disconnected${NC}"
    fi
fi

echo
echo "6. 🌐 Checking network connectivity to exchanges..."

# Test connectivity to exchanges
exchanges=("api.kraken.com" "api.bybit.com" "api.mexc.com")
for exchange in "${exchanges[@]}"; do
    if ping -c 1 -W 3 "$exchange" &> /dev/null; then
        echo -e "   $exchange: ${GREEN}Reachable${NC}"
    else
        echo -e "   $exchange: ${RED}Unreachable${NC}"
    fi
done

echo
echo "================================="
echo "🎯 DIAGNOSIS SUMMARY:"
echo "================================="

# Provide recommendations
echo -e "${YELLOW}Likely causes of static mode:${NC}"
echo "1. Exchange configurations disabled (enabled: false)"
echo "2. Missing or incorrect API keys"
echo "3. Bot in PAPER mode instead of LIVE mode"
echo "4. Strategies not enabled or misconfigured"
echo "5. Network connectivity issues"
echo "6. Insufficient minimum spread thresholds"

echo
echo -e "${GREEN}QUICK FIXES:${NC}"
echo "1. Edit config/settings.yaml - set enabled: true for exchanges"
echo "2. Add API keys to .env file"
echo "3. Set TRADING_MODE=LIVE (if you want real trading)"
echo "4. Lower min_spread_percent in strategy config"
echo "5. Check logs for specific error messages"

echo
echo "🚀 Run 'make logs' to see live logs"
echo "🔧 Run 'make status' to check system status"
echo "📊 Visit dashboard at http://$(hostname -I | awk '{print $1}'):3000"
