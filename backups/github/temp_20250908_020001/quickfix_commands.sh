#!/bin/bash

# SmartArb Engine Quick Fix Commands
# Riattiva il bot quando è in modalità statica

echo "🚀 SmartArb Engine Quick Fix"
echo "============================="
echo

PROJECT_DIR="$HOME/smartarb_engine"  # Auto-detect current user path

# Colori
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cd "$PROJECT_DIR" || exit 1

echo -e "${YELLOW}1. 🔧 Fixing Exchange Configurations...${NC}"

# Backup della configurazione attuale
cp config/settings.yaml config/settings.yaml.backup 2>/dev/null || echo "No existing settings.yaml found"

# Crea configurazione base se non esiste
if [ ! -f "config/settings.yaml" ]; then
    echo "Creating settings.yaml from example..."
    cp config/settings.yaml.example config/settings.yaml
fi

# Abilita tutti gli exchange
sed -i 's/enabled: false/enabled: true/g' config/settings.yaml

# Imposta parametri più aggressivi per testing
cat >> config/settings.yaml << 'EOF'

# Quick fix overrides
strategies:
  spatial_arbitrage:
    enabled: true
    min_spread_percent: 0.10  # Lowered for testing
    scan_frequency: 3         # More frequent scanning
    max_position_size: 50     # Smaller position for testing
    confidence_threshold: 0.5 # Lower threshold
EOF

echo -e "${GREEN}✅ Exchange configurations updated${NC}"

echo
echo -e "${YELLOW}2. 🗝️ Setting up Environment Variables...${NC}"

# Crea .env se non esiste
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# SmartArb Engine Environment Variables
# Add your actual API keys here

# Trading Mode
TRADING_MODE=PAPER
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# Kraken API
KRAKEN_API_KEY=your_kraken_api_key_here
KRAKEN_API_SECRET=your_kraken_api_secret_here

# Bybit API
BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_API_SECRET=your_bybit_api_secret_here

# MEXC API
MEXC_API_KEY=your_mexc_api_key_here
MEXC_API_SECRET=your_mexc_api_secret_here

# Claude AI (optional)
CLAUDE_API_KEY=your_claude_api_key_here

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=smartarb
POSTGRES_USERNAME=smartarb_user
POSTGRES_PASSWORD=smartarb_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password
EOF
    
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${RED}⚠️  IMPORTANT: Edit .env file with your real API keys!${NC}"
else
    echo "✅ .env file exists"
fi

echo
echo -e "${YELLOW}3. 🐳 Restarting Services...${NC}"

# Stop existing containers
docker-compose down 2>/dev/null || echo "No existing containers to stop"

# Clean up old containers
docker container prune -f 2>/dev/null

echo "Starting services in paper trading mode..."

# Start in development mode first
docker-compose -f docker-compose.yml up -d 2>/dev/null || {
    echo "Docker compose failed, trying direct Python run..."
    
    # Install/update dependencies
    pip install -r requirements.txt
    
    # Run directly
    python -m src.main &
    PYTHON_PID=$!
    echo "Started Python process with PID: $PYTHON_PID"
}

echo
echo -e "${YELLOW}4. 🔍 Quick System Check...${NC}"

sleep 5  # Wait for services to start

# Check if container is running
if docker ps | grep -q smartarb; then
    echo -e "✅ ${GREEN}Container is running${NC}"
    
    # Show logs
    echo "Recent logs:"
    docker logs --tail 10 $(docker ps | grep smartarb | awk '{print $1}') | sed 's/^/  /'
else
    echo -e "⚠️ ${YELLOW}Container not running, checking Python process...${NC}"
    
    if pgrep -f "smartarb" > /dev/null; then
        echo -e "✅ ${GREEN}Python process is running${NC}"
    else
        echo -e "❌ ${RED}No SmartArb process found${NC}"
    fi
fi

echo
echo -e "${YELLOW}5. 📊 Testing Market Data Connection...${NC}"

# Simple test script
cat > test_connection.py << 'EOF'
#!/usr/bin/env python3
import asyncio
import os
import sys
sys.path.append('src')

async def test_exchanges():
    print("🧪 Testing exchange connections...")
    
    # Test imports
    try:
        from src.exchanges.kraken_client import KrakenClient
        from src.exchanges.bybit_client import BybitClient
        from src.exchanges.mexc_client import MEXCClient
        print("✅ Exchange modules imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return
    
    # Test basic connectivity (without real API keys)
    exchanges = {
        'kraken': 'https://api.kraken.com/0/public/Time',
        'bybit': 'https://api.bybit.com/v5/announcements/index',
        'mexc': 'https://api.mexc.com/api/v3/ping'
    }
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        for name, url in exchanges.items():
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        print(f"✅ {name.capitalize()}: API reachable")
                    else:
                        print(f"⚠️ {name.capitalize()}: API returned {response.status}")
            except Exception as e:
                print(f"❌ {name.capitalize()}: {str(e)[:50]}...")

if __name__ == "__main__":
    asyncio.run(test_exchanges())
EOF

python test_connection.py
rm test_connection.py

echo
echo "================================="
echo -e "${GREEN}🎉 QUICK FIX COMPLETED!${NC}"
echo "================================="

echo
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo "1. 🔧 Edit .env file with your real API keys:"
echo "   nano .env"
echo
echo "2. 🚀 Monitor the bot activity:"
echo "   tail -f logs/smartarb.log"
echo "   # OR"
echo "   docker logs -f \$(docker ps | grep smartarb | awk '{print \$1}')"
echo
echo "3. 📊 Check the dashboard:"
echo "   http://$(hostname -I | awk '{print $1}'):3000"
echo
echo "4. 🔍 If still static, check:"
echo "   - API keys are correct"
echo "   - Exchange accounts have trading enabled"
echo "   - Minimum balances are met (>$200 per exchange)"
echo "   - Network connectivity is stable"

echo
echo -e "${GREEN}The bot should now be more active!${NC}"
echo -e "${YELLOW}Monitor logs for 2-3 minutes to see trading activity${NC}"

echo
echo "🆘 If problems persist, run: ./diagnose_smartarb.sh"
