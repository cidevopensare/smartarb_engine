#!/bin/bash
# fix_engine_imports.sh - Risolve import relativi nell'engine

echo "🔧 Fixing SmartArb Engine imports..."

# Backup del file originale
cp src/core/engine.py src/core/engine.py.bak

# Fix degli import relativi - cambia da relativi ad assoluti
sed -i 's/from \.\.config\.config_manager/from src.config.config_manager/g' src/core/engine.py
sed -i 's/from \.\.core\.logger/from src.core.logger/g' src/core/engine.py  
sed -i 's/from \.\.notifications\.telegram_notifier/from src.notifications.telegram_notifier/g' src/core/engine.py

echo "✅ Engine imports fixed!"

# Test se funziona ora
echo "🧪 Testing fixed engine..."
source venv/bin/activate

# Test diretto
timeout 10s python3 src/core/engine.py &
TEST_PID=$!
sleep 5

if ps -p $TEST_PID > /dev/null 2>&1; then
    echo "✅ Engine now starts successfully!"
    kill $TEST_PID 2>/dev/null || true
else
    echo "❌ Still having issues, trying alternative fix..."
    
    # Ripristina backup e prova fix alternativo
    cp src/core/engine.py.bak src/core/engine.py
    
    # Fix alternativo - aggiunge path
    cat > engine_fixed.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Resto del file engine originale con import assoluti
EOF
    
    tail -n +2 src/core/engine.py >> engine_fixed.py
    
    # Sostituisce gli import
    sed -i 's/from \.\.config\.config_manager/from src.config.config_manager/g' engine_fixed.py
    sed -i 's/from \.\.core\.logger/from src.core.logger/g' engine_fixed.py  
    sed -i 's/from \.\.notifications\.telegram_notifier/from src.notifications.telegram_notifier/g' engine_fixed.py
    
    mv engine_fixed.py src/core/engine.py
    chmod +x src/core/engine.py
    
    echo "🔄 Applied alternative fix"
fi

echo ""
echo "🎯 Now try: make start"
