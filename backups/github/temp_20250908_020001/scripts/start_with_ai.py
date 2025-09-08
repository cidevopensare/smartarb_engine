#!/usr/bin/env python3
"""
SmartArb Engine - AI-Powered Startup Script
Starts the engine with full AI integration and monitoring
"""

import asyncio
import sys
import os
import time
import signal
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure environment for AI mode
os.environ['AI_ENABLED'] = 'true'
os.environ['AI_MODE'] = 'advisory_only'
os.environ['TELEGRAM_AI'] = 'true'

try:
    from src.core.unified_engine import UnifiedSmartArbEngine
    from src.ai.ai_integration import SmartArbAI
    from src.utils.logging import setup_logging, get_logger
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📦 Installing missing dependencies...")
    os.system("pip3 install -q structlog rich pyyaml")
    sys.exit(1)

# Setup logging
logger = get_logger("ai_startup")

class AIEnabledEngine:
    """Enhanced engine with AI capabilities"""
    
    def __init__(self):
        self.unified_engine = None
        self.ai_system = None
        self.is_running = False
        self.startup_time = time.time()
        
    async def initialize_ai(self) -> bool:
        """Initialize AI system"""
        try:
            logger.info("🧠 Initializing AI system...")
            
            # Check if AI files exist
            ai_integration_path = Path("src/ai/ai_integration.py")
            if not ai_integration_path.exists():
                # Try to restore from backup
                backup_path = Path("src/ai/ai_integration.py.backup")
                if backup_path.exists():
                    logger.info("📋 Restoring AI integration from backup...")
                    import shutil
                    shutil.copy(backup_path, ai_integration_path)
                else:
                    logger.warning("⚠️ AI integration file not found, creating minimal version...")
                    await self.create_minimal_ai_integration()
            
            # Initialize AI system
            from src.ai.ai_integration import SmartArbAI
            
            self.ai_system = SmartArbAI()
            await self.ai_system.initialize()
            
            logger.info("✅ AI system initialized successfully")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ AI initialization failed: {e}")
            logger.info("🔄 Continuing without AI features...")
            return False
    
    async def create_minimal_ai_integration(self):
        """Create minimal AI integration file"""
        ai_content = '''#!/usr/bin/env python3
"""
SmartArb Engine - AI Integration (Minimal Version)
Basic AI functionality for advisory analysis
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

class SmartArbAI:
    """Minimal AI integration for SmartArb Engine"""
    
    def __init__(self):
        self.initialized = False
        self.config = {}
        
    async def initialize(self):
        """Initialize AI system"""
        self.initialized = True
        return True
    
    async def analyze_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Basic performance analysis"""
        return {
            'analysis': 'Basic AI analysis - upgrade for full features',
            'recommendations': ['Monitor system performance', 'Check market conditions'],
            'confidence': 0.5,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_market_insights(self) -> Dict[str, Any]:
        """Basic market insights"""
        return {
            'insights': 'Basic market analysis - AI integration needed',
            'signals': [],
            'timestamp': datetime.now().isoformat()
        }
'''
        
        # Create AI directory if it doesn't exist
        os.makedirs("src/ai", exist_ok=True)
        
        # Write minimal AI integration
        with open("src/ai/ai_integration.py", "w") as f:
            f.write(ai_content)
        
        # Create __init__.py
        with open("src/ai/__init__.py", "w") as f:
            f.write("# SmartArb AI Module\n")
    
    async def start(self):
        """Start the AI-enabled engine"""
        try:
            logger.info("🚀 Starting SmartArb Engine with AI integration...")
            
            # Initialize AI system first
            ai_success = await self.initialize_ai()
            
            # Initialize unified engine
            self.unified_engine = UnifiedSmartArbEngine()
            
            # Add AI integration if available
            if ai_success and self.ai_system:
                self.unified_engine.ai_system = self.ai_system
                logger.info("🧠 AI system integrated with engine")
            
            # Start the unified engine
            self.is_running = True
            
            # Send startup notification
            await self.send_startup_notification(ai_enabled=ai_success)
            
            # Start the main engine
            await self.unified_engine.start()
            
        except Exception as e:
            logger.error(f"❌ AI-enabled engine startup failed: {e}")
            self.is_running = False
            raise
    
    async def send_startup_notification(self, ai_enabled: bool = False):
        """Send startup notification with AI status"""
        try:
            if hasattr(self.unified_engine, 'send_telegram_notification'):
                ai_status = "🧠 AI: Enabled" if ai_enabled else "🔄 AI: Basic Mode"
                
                message = (
                    "🚀 <b>SmartArb Engine Started with AI!</b>\n\n"
                    f"📊 <b>Dashboard:</b> http://localhost:8001\n"
                    f"🧠 <b>AI Status:</b> {'Advanced' if ai_enabled else 'Basic'}\n"
                    f"📱 <b>Telegram:</b> Active\n"
                    f"🔄 <b>Trading Mode:</b> Paper Trading\n"
                    f"⏰ <b>Started:</b> {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"{ai_status}"
                )
                
                await self.unified_engine.send_telegram_notification(message)
            
        except Exception as e:
            logger.warning(f"⚠️ Startup notification failed: {e}")
    
    async def stop(self):
        """Stop the AI-enabled engine"""
        logger.info("🛑 Stopping AI-enabled engine...")
        self.is_running = False
        
        if self.unified_engine:
            await self.unified_engine.stop()
        
        if self.ai_system:
            logger.info("🧠 Stopping AI system...")
            # Add AI cleanup if needed
            
        logger.info("✅ AI-enabled engine stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n📡 Received signal {signum}, shutting down AI-enabled engine...")
    # The main loop will handle the actual shutdown
    
async def main():
    """Main entry point for AI-enabled engine"""
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create AI-enabled engine
    engine = AIEnabledEngine()
    
    try:
        # Start the engine
        await engine.start()
        
        # Keep running
        while engine.is_running:
            await asyncio.sleep(1)
            
        return 0
        
    except KeyboardInterrupt:
        logger.info("👋 Shutdown requested by user")
        await engine.stop()
        return 0
        
    except Exception as e:
        logger.error(f"💥 Fatal error in AI-enabled engine: {e}")
        await engine.stop()
        return 1

if __name__ == "__main__":
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Setup basic logging for startup
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the AI-enabled engine
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
