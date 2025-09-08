#!/bin/bash
# diagnose_engine_crash.sh - Scopri perché l'engine crasha

echo "🔍 SmartArb Engine - Crash Analysis"
echo "===================================="

# 1. Controlla tutti i possibili log files
echo "1. 📋 Checking all log files for crash info..."
echo ""

if [ -f "logs/engine.log" ]; then
    echo "--- Engine Log (last 20 lines) ---"
    tail -20 logs/engine.log
    echo ""
else
    echo "⚠️ No engine.log found"
fi

if [ -f "logs/smartarb.log" ]; then
    echo "--- SmartArb Log (recent errors) ---"
    grep -i "error\|exception\|traceback\|failed" logs/smartarb.log | tail -10
    echo ""
    
    echo "--- SmartArb Log (last 20 lines) ---"
    tail -20 logs/smartarb.log
    echo ""
else
    echo "⚠️ No smartarb.log found"
fi

# 2. Test engine con output diretto (senza background)
echo "2. 🧪 Testing engine with direct output..."
echo ""

cd /home/smartarb/smartarb_engine
source venv/bin/activate

echo "Starting engine in foreground for 10 seconds to capture errors..."
timeout 10s python3 src/core/engine.py 2>&1 | head -50

echo ""
echo "3. 🔍 Checking configuration files..."
echo ""

# Controlla se esistono file di configurazione
if [ -f "config/settings.yaml" ]; then
    echo "✅ config/settings.yaml exists"
    echo "   Size: $(ls -lh config/settings.yaml | awk '{print $5}')"
else
    echo "❌ config/settings.yaml MISSING - This could cause crash!"
    echo "💡 Creating basic config..."
    
    mkdir -p config
    cat > config/settings.yaml << 'EOF'
# SmartArb Engine Configuration
app:
  name: "SmartArb Engine"
  version: "1.0"
  mode: "paper"

exchanges:
  kraken:
    enabled: true
  bybit: 
    enabled: true
  mexc:
    enabled: true

risk_management:
  max_position_size: 1000
  max_daily_loss: 200

telegram:
  enabled: true
  min_profit_threshold: 25.0
EOF
    
    echo "✅ Created basic config/settings.yaml"
fi

if [ -f ".env" ]; then
    echo "✅ .env exists"
    echo "   Telegram config: $(grep -c "TELEGRAM_" .env) entries"
else
    echo "❌ .env MISSING"
fi

# 4. Test dipendenze specifiche
echo ""
echo "4. 📦 Testing engine-specific dependencies..."
echo ""

python3 -c "
import sys
print('Testing specific imports that engine needs...')

try:
    from src.config.config_manager import AppConfig
    print('✅ AppConfig import: OK')
except ImportError as e:
    print(f'❌ AppConfig import: {e}')

try:
    from src.core.logger import get_logger
    print('✅ Logger import: OK')
except ImportError as e:
    print(f'❌ Logger import: {e}')

try:
    from src.notifications.telegram_notifier import TelegramNotifier
    print('✅ TelegramNotifier import: OK')
except ImportError as e:
    print(f'❌ TelegramNotifier import: {e}')
    
print('\\nTesting basic library imports...')
    
libraries = ['asyncio', 'logging', 'time', 'os', 'datetime', 'json', 'yaml']
for lib in libraries:
    try:
        __import__(lib)
        print(f'✅ {lib}: OK')
    except ImportError:
        print(f'❌ {lib}: MISSING')
"

# 5. Controlla se mancano directory o file critici
echo ""
echo "5. 📁 Checking critical directories and files..."
echo ""

critical_dirs=("src/config" "src/core" "src/notifications" "logs" "config")
for dir in "${critical_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir/ exists"
    else
        echo "❌ $dir/ missing - creating..."
        mkdir -p "$dir"
        touch "$dir/__init__.py" 2>/dev/null || true
    fi
done

critical_files=("src/config/config_manager.py" "src/core/logger.py" "src/notifications/telegram_notifier.py")
for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists ($(ls -lh "$file" | awk '{print $5}'))"
    else
        echo "❌ $file MISSING - this will cause crash!"
    fi
done

# 6. Test veloce con minimal config
echo ""
echo "6. 🚀 Testing with minimal configuration..."
echo ""

echo "Creating minimal test engine..."
cat > test_minimal_engine.py << 'EOF'
#!/usr/bin/env python3
"""
Minimal test engine to isolate crash cause
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_engine')

async def minimal_engine():
    """Minimal engine test"""
    logger.info("🚀 Minimal test engine starting...")
    
    try:
        # Test basic functionality
        logger.info("📊 Testing basic operations...")
        await asyncio.sleep(1)
        
        logger.info("🔗 Testing configuration...")
        # Minimal config test
        config = {"mode": "test"}
        
        logger.info("✅ Minimal engine working!")
        
        # Keep running for a bit
        for i in range(5):
            logger.info(f"💚 Heartbeat {i+1}/5")
            await asyncio.sleep(2)
            
        logger.info("🏁 Minimal engine test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Minimal engine error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(minimal_engine())
    except KeyboardInterrupt:
        logger.info("👋 Minimal engine stopped")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
EOF

echo "Testing minimal engine..."
timeout 15s python3 test_minimal_engine.py

echo ""
echo "📊 Diagnosis Summary:"
echo "===================="
echo "If minimal engine works but real engine crashes,"
echo "the issue is likely:"
echo "  1. Missing configuration files"
echo "  2. Missing dependencies (config_manager, logger, etc.)"
echo "  3. Invalid .env variables"
echo "  4. Database connection issues"
echo ""
echo "Next steps:"
echo "  - Fix missing files shown above"
echo "  - Check logs/engine.log for specific errors"
echo "  - Try: python3 test_minimal_engine.py"
