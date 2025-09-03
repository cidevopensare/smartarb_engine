#!/bin/bash
# debug_engine_startup.sh - Diagnosi problemi avvio engine

echo "🔍 SmartArb Engine - Debug Startup"
echo "==================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Controlla struttura file
echo "1. 📁 Checking file structure..."
echo ""

if [ -f "src/core/engine.py" ]; then
    echo -e "${GREEN}✅ src/core/engine.py exists${NC}"
    echo "   Size: $(ls -lh src/core/engine.py | awk '{print $5}')"
else
    echo -e "${RED}❌ src/core/engine.py NOT FOUND${NC}"
fi

if [ -f "src/core/engine_with_dashboard.py" ]; then
    echo -e "${GREEN}✅ src/core/engine_with_dashboard.py exists${NC}"
else
    echo -e "${YELLOW}⚠️ src/core/engine_with_dashboard.py not found${NC}"
fi

if [ -f "src/__init__.py" ]; then
    echo -e "${GREEN}✅ src/__init__.py exists${NC}"
else
    echo -e "${RED}❌ src/__init__.py missing (needed for Python modules)${NC}"
    touch src/__init__.py
    echo -e "${GREEN}✅ Created src/__init__.py${NC}"
fi

if [ -f "src/core/__init__.py" ]; then
    echo -e "${GREEN}✅ src/core/__init__.py exists${NC}"
else
    echo -e "${RED}❌ src/core/__init__.py missing${NC}"
    touch src/core/__init__.py
    echo -e "${GREEN}✅ Created src/core/__init__.py${NC}"
fi

# 2. Controlla logs esistenti
echo ""
echo "2. 📋 Checking engine logs..."
echo ""

if [ -f "logs/engine.log" ]; then
    echo -e "${YELLOW}--- Last 10 lines of engine.log ---${NC}"
    tail -10 logs/engine.log
else
    echo -e "${YELLOW}⚠️ No engine.log found${NC}"
fi

if [ -f "logs/smartarb.log" ]; then
    echo ""
    echo -e "${YELLOW}--- Last 10 lines of smartarb.log ---${NC}"
    tail -10 logs/smartarb.log
else
    echo -e "${YELLOW}⚠️ No smartarb.log found${NC}"
fi

# 3. Test Python import
echo ""
echo "3. 🐍 Testing Python module import..."
echo ""

# Test con virtual env attivato
source venv/bin/activate

echo "Testing Python path and imports..."
python3 -c "
import sys
print('Python path:')
for p in sys.path[:3]:
    print(f'  {p}')

print('\\nTesting imports...')
try:
    import src
    print('✅ src module: OK')
except ImportError as e:
    print(f'❌ src module: {e}')

try:
    import src.core
    print('✅ src.core module: OK')
except ImportError as e:
    print(f'❌ src.core module: {e}')

try:
    from src.core import engine
    print('✅ engine import: OK')
except ImportError as e:
    print(f'❌ engine import: {e}')
    print('Error details:', str(e))
"

# 4. Test diretto del file engine
echo ""
echo "4. 🧪 Testing engine file directly..."
echo ""

echo "Running engine file directly..."
timeout 10s python3 src/core/engine.py &
ENGINE_TEST_PID=$!

sleep 5

if ps -p $ENGINE_TEST_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Engine starts successfully when run directly${NC}"
    kill $ENGINE_TEST_PID 2>/dev/null || true
else
    echo -e "${RED}❌ Engine fails to start even when run directly${NC}"
fi

# 5. Test con -m module
echo ""
echo "5. 🔧 Testing with -m module syntax..."
echo ""

echo "Testing: python3 -m src.core.engine"
timeout 10s python3 -m src.core.engine > /tmp/engine_test.log 2>&1 &
MODULE_TEST_PID=$!

sleep 5

if ps -p $MODULE_TEST_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Engine starts with -m syntax${NC}"
    kill $MODULE_TEST_PID 2>/dev/null || true
else
    echo -e "${RED}❌ Engine fails with -m syntax${NC}"
    echo "Error log:"
    cat /tmp/engine_test.log
fi

# 6. Check dependencies
echo ""
echo "6. 📦 Checking engine dependencies..."
echo ""

python3 -c "
required = ['asyncio', 'logging', 'time', 'os', 'datetime']
for module in required:
    try:
        __import__(module)
        print(f'✅ {module}: OK')
    except ImportError:
        print(f'❌ {module}: MISSING')
"

# 7. Raccomandazioni
echo ""
echo "7. 💡 Recommendations..."
echo ""

if [ ! -f "logs/engine.log" ]; then
    echo -e "${YELLOW}📝 Create engine log manually:${NC}"
    echo "   touch logs/engine.log"
fi

echo -e "${YELLOW}🔧 Try manual engine start:${NC}"
echo "   source venv/bin/activate"
echo "   python3 src/core/engine.py"
echo ""

echo -e "${YELLOW}📊 Try alternative engine:${NC}"
echo "   python3 src/core/engine_with_dashboard.py"
echo ""

echo -e "${YELLOW}🔍 Debug with verbose output:${NC}"
echo "   source venv/bin/activate"
echo "   python3 -v -m src.core.engine"
