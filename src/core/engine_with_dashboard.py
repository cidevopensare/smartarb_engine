#!/usr/bin/env python3
"""
SmartArb Engine with Integrated Dashboard
Main engine that includes web dashboard
"""

import asyncio
import threading
import uvicorn
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import components directly
from src.core.engine import SmartArbEngine
from src.api.dashboard_server import app as dashboard_app

# Try to import AppConfig
try:
    from src.utils.config import AppConfig
except ImportError:
    # Create a simple config class if not found
    class AppConfig:
        def __init__(self):
            self.config_path = "config/settings.yaml"

def start_dashboard():
    """Start dashboard in separate thread"""
    print("Starting integrated dashboard on port 8001...")
    try:
        uvicorn.run(dashboard_app, host="0.0.0.0", port=8001, log_level="warning")
    except Exception as e:
        print(f"Dashboard error: {e}")

async def main_with_dashboard():
    """Main function that starts both engine and dashboard"""
    
    print("🚀 Starting SmartArb Engine with Integrated Dashboard...")
    
    # Start dashboard in background thread
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()
    
    print("📊 Dashboard started in background on port 8001")
    print("🌐 Access at: http://localhost:8001")
    
    # Give dashboard time to start
    await asyncio.sleep(3)
    
    # Create config and engine
    print("🤖 Starting main trading engine...")
    
    try:
        # Create config object
        config = AppConfig()
        
        # Create engine with config
        engine = SmartArbEngine(config)
        
        # Initialize and start engine
        if not await engine.initialize():
            print("❌ Engine initialization failed")
            return 1
        
        if not await engine.start():
            print("❌ Engine start failed")
            return 1
        
        print("✅ SmartArb Engine is running!")
        print("📊 Dashboard available at: http://localhost:8001")
        
        # Keep running until shutdown
        while engine.is_running:
            await asyncio.sleep(1)
        
        return 0
        
    except KeyboardInterrupt:
        print("🛑 Keyboard interrupt received")
        if 'engine' in locals():
            await engine.shutdown()
        return 0
        
    except Exception as e:
        print(f"❌ Unexpected engine error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import logging
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the integrated system
    try:
        exit_code = asyncio.run(main_with_dashboard())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
