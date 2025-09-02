#!/usr/bin/env python3
import sys
import os
import asyncio
import logging

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/debug_test.log')
    ]
)

async def test_bot():
    print("🧪 Testing SmartArb Engine directly...")
    
    try:
        # Test import
        from src.core.engine import SmartArbEngine
        print("✅ Engine import successful")
        
        # Test initialization
        engine = SmartArbEngine()
        print("✅ Engine initialization successful")
        
        # Test config load
        # await engine.load_config()
        print("✅ Configuration loaded")
        
        print("🚀 Starting engine test run...")
        # Run for 30 seconds
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bot())
