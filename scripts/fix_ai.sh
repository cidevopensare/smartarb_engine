#!/bin/bash
# fix_ai.sh - Ripristina il sistema AI dal backup

echo "🔧 SmartArb Engine - AI System Recovery"
echo "======================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if we're in the right directory
if [ ! -f "Makefile" ]; then
    echo -e "${RED}❌ Error: Please run this script from the smartarb_engine directory${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Checking AI system status...${NC}"

# 1. Check AI directory
if [ ! -d "src/ai" ]; then
    echo -e "${YELLOW}⚠️ Creating src/ai directory...${NC}"
    mkdir -p src/ai
fi

# 2. Restore ai_integration.py from backup
if [ -f "src/ai/ai_integration.py.backup" ]; then
    echo -e "${BLUE}📋 Restoring ai_integration.py from backup...${NC}"
    cp src/ai/ai_integration.py.backup src/ai/ai_integration.py
    echo -e "${GREEN}✅ ai_integration.py restored${NC}"
else
    echo -e "${YELLOW}⚠️ No backup found, creating minimal AI integration...${NC}"
    
    cat > src/ai/ai_integration.py << 'EOF'
#!/usr/bin/env python3
"""
SmartArb Engine - AI Integration
Claude AI integration for automated analysis and optimization
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

class SmartArbAI:
    """AI system for SmartArb Engine"""
    
    def __init__(self):
        self.initialized = False
        self.config = {}
        self.analysis_count = 0
        self.last_analysis = None
        
    async def initialize(self):
        """Initialize AI system"""
        try:
            self.initialized = True
            self.last_analysis = datetime.now()
            print("🧠 AI System initialized (Basic Mode)")
            return True
        except Exception as e:
            print(f"❌ AI initialization failed: {e}")
            return False
    
    async def analyze_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trading performance"""
        try:
            self.analysis_count += 1
            self.last_analysis = datetime.now()
            
            # Basic analysis
            total_trades = data.get('total_trades', 0)
            win_rate = data.get('win_rate', 0.0)
            total_profit = data.get('total_profit', 0.0)
            
            # Generate recommendations
            recommendations = []
            if win_rate < 0.6:
                recommendations.append("Consider adjusting risk parameters")
            if total_profit < 0:
                recommendations.append("Review trading strategy performance")
            if total_trades == 0:
                recommendations.append("Monitor for trading opportunities")
            
            return {
                'analysis': f'Analyzed {total_trades} trades with {win_rate:.1%} win rate',
                'recommendations': recommendations,
                'confidence': 0.7,
                'timestamp': datetime.now().isoformat(),
                'analysis_id': self.analysis_count
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get AI system status"""
        return {
            'initialized': self.initialized,
            'analysis_count': self.analysis_count,
            'last_analysis': self.last_analysis.isoformat() if self.last_analysis else None,
            'mode': 'advisory_only',
            'version': '1.0.0-basic'
        }

# Export main class
__all__ = ['SmartArbAI']
EOF
    
    echo -e "${GREEN}✅ Minimal AI integration created${NC}"
fi

# 3. Ensure __init__.py exists
if [ ! -f "src/ai/__init__.py" ]; then
    echo -e "${BLUE}📝 Creating src/ai/__init__.py...${NC}"
    echo "# SmartArb AI Module" > src/ai/__init__.py
fi

# 4. Create AI config directory and files
echo -e "${BLUE}📁 Setting up AI configuration...${NC}"
mkdir -p config/ai

# Create basic AI settings if they don't exist
if [ ! -f "config/ai/ai_settings.yaml" ]; then
    cat > config/ai/ai_settings.yaml << 'EOF'
# SmartArb Engine - AI Configuration
ai:
  enabled: true
  mode: "advisory_only"
  model: "claude-sonnet-4-20250514"
  temperature: 0.7
  max_tokens: 1000
  
  analysis:
    auto_analysis: true
    analysis_schedule: "0 */2 * * *"
    min_confidence: 0.6
    
  telegram:
    ai_notifications: true
    analysis_reports: true
    
logging:
  ai_log_level: "INFO"
  ai_log_file: "logs/ai_system.log"
EOF
    echo -e "${GREEN}✅ AI configuration created${NC}"
fi

# 5. Create start_with_ai.py script (already created in artifacts)
if [ ! -f "scripts/start_with_ai.py" ]; then
    echo -e "${YELLOW}⚠️ scripts/start_with_ai.py not found${NC}"
    echo -e "${BLUE}📝 Please create this file from the artifacts provided${NC}"
fi

# 6. Set permissions
echo -e "${BLUE}🔧 Setting permissions...${NC}"
chmod +x scripts/*.py 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true

# 7. Final check
echo -e "${BLUE}🔍 Final AI system check...${NC}"

if [ -f "src/ai/ai_integration.py" ]; then
    echo -e "${GREEN}✅ AI Integration: OK${NC}"
else
    echo -e "${RED}❌ AI Integration: Missing${NC}"
fi

if [ -f "config/ai/ai_settings.yaml" ]; then
    echo -e "${GREEN}✅ AI Configuration: OK${NC}"
else
    echo -e "${RED}❌ AI Configuration: Missing${NC}"
fi

if [ -f "scripts/start_with_ai.py" ]; then
    echo -e "${GREEN}✅ AI Startup Script: OK${NC}"
else
    echo -e "${YELLOW}⚠️ AI Startup Script: Please create from artifacts${NC}"
fi

echo ""
echo -e "${GREEN}🎉 AI System Recovery Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Run: make start-with-ai"
echo "2. Check: make ai-status"
echo "3. Test: make test-ai"
echo ""
echo -e "${BLUE}📊 Dashboard will be available at: http://localhost:8001${NC}"
