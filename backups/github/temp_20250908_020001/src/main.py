#!/usr/bin/env python3
"""
SmartArb Engine - Main Entry Point
Professional Cryptocurrency Arbitrage Trading Bot

Author: SmartArb Team
Version: 1.0.0
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Configuration
from src.config.config_manager import ConfigManager
from src.core.logger import setup_logging
from src.core.engine import SmartArbEngine

# Global variables
engine: Optional[SmartArbEngine] = None
logger: Optional[logging.Logger] = None

async def setup_signal_handlers():
    """Setup graceful shutdown handlers"""
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        if engine:
            asyncio.create_task(engine.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main application entry point"""
    global engine, logger
    
    try:
        # Print startup banner
        print("🚀 SmartArb Engine Starting...")
        print("=" * 50)
        print("📊 Professional Cryptocurrency Arbitrage Bot")
        print("🔗 Multi-Exchange Trading System")
        print("🧠 AI-Powered Optimization")
        print("=" * 50)
        print()
        
        # Load configuration
        print("🔧 Loading configuration...")
        config_manager = ConfigManager()
        config = await config_manager.load_config()
        
        # Setup logging
        print("📋 Setting up logging system...")
        logger = setup_logging(config)
        logger.info("🎯 SmartArb Engine initialization started")
        
        # Display configuration summary
        trading_mode = os.getenv('TRADING_MODE', 'PAPER')
        debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        
        logger.info(f"💼 Trading Mode: {trading_mode}")
        logger.info(f"🔍 Debug Mode: {debug_mode}")
        logger.info(f"📈 Log Level: {logging.getLevelName(logger.level)}")
        
        # Setup signal handlers
        await setup_signal_handlers()
        
        # Initialize and start engine
        logger.info("⚡ Initializing SmartArb Engine...")
        engine = SmartArbEngine(config)
        
        # Start the engine
        logger.info("🚀 Starting trading engine...")
        await engine.start()
        
        # Keep running
        logger.info("✅ SmartArb Engine is now running!")
        logger.info("📊 Monitor dashboard: http://localhost:3000")
        logger.info("🔍 Health endpoint: http://localhost:8000/health")
        logger.info("🛑 Press Ctrl+C to stop")
        
        # Main loop
        while True:
            try:
                await asyncio.sleep(1)
                
                # Health check every 60 seconds
                if hasattr(engine, 'last_health_check'):
                    import time
                    if time.time() - engine.last_health_check > 60:
                        await engine.health_check()
                        
            except KeyboardInterrupt:
                break
                
    except Exception as e:
        if logger:
            logger.error(f"❌ Fatal error in main loop: {str(e)}")
            logger.exception("Full error details:")
        else:
            print(f"❌ Fatal error before logging setup: {str(e)}")
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    finally:
        if engine:
            logger.info("🛑 Shutting down SmartArb Engine...")
            await engine.shutdown()
        if logger:
            logger.info("👋 SmartArb Engine stopped gracefully")
        print("👋 Goodbye!")

if __name__ == "__main__":
    # Ensure we're running Python 3.11+
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 or higher is required!")
        sys.exit(1)
    
    # Set environment variables if not set
    if not os.getenv('TRADING_MODE'):
        os.environ['TRADING_MODE'] = 'PAPER'
    
    if not os.getenv('DEBUG_MODE'):
        os.environ['DEBUG_MODE'] = 'true'
    
    if not os.getenv('LOG_LEVEL'):
        os.environ['LOG_LEVEL'] = 'DEBUG'
    
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Application failed to start: {str(e)}")
        sys.exit(1)
