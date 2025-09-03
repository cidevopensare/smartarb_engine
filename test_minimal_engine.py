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
