#!/usr/bin/env python3
"""
Simple test dashboard to verify the setup
"""
try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    import uvicorn
    import json
    import time
    
    app = FastAPI(title="SmartArb Test Dashboard")
    
    @app.get("/")
    async def root():
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>SmartArb Test Dashboard</title></head>
        <body style="font-family: Arial; background: #000; color: #fff; padding: 20px;">
            <h1>🚀 SmartArb Test Dashboard</h1>
            <p>✅ Dashboard server is working!</p>
            <p>📊 <a href="/api/metrics" style="color: #00ff88;">View Metrics API</a></p>
            <script>
                setTimeout(() => {
                    fetch('/api/metrics')
                        .then(r => r.json())
                        .then(data => {
                            document.body.innerHTML += '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        });
                }, 1000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)
    
    @app.get("/api/metrics")
    async def metrics():
        return {
            "status": "OK",
            "timestamp": time.time(),
            "trades_executed": 47,
            "success_rate": 87.3,
            "total_profit": 156.43,
            "daily_pnl": 32.18,
            "memory_usage": 45.2,
            "cpu_usage": 15.8,
            "message": "SmartArb Dashboard Test - All systems operational!"
        }
    
    if __name__ == "__main__":
        print("🧪 Starting SmartArb Test Dashboard on port 8001...")
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Try: pip3 install fastapi uvicorn")
