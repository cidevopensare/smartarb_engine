#!/usr/bin/env python3
"""
SmartArb Engine Dashboard Server
Serves web dashboard and API endpoints
"""

import uvicorn
import sys
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Create main dashboard app
app = FastAPI(
    title="SmartArb Engine Dashboard",
    description="Web dashboard for SmartArb cryptocurrency arbitrage bot",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to static files
static_path = project_root / "static" / "dashboard"

# Mount static files if directory exists
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Basic API endpoints (simplified version)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2025-08-30T20:00:00",
        "version": "1.0.0",
        "uptime_seconds": 3600,
        "database_connected": True,
        "exchanges_connected": 3,
        "active_strategies": 2
    }

@app.get("/api/status")
async def get_status():
    """Get engine status"""
    return {
        "engine_state": "running",
        "is_running": True,
        "uptime": 3600,
        "memory_usage": 45.2,
        "cpu_usage": 12.8,
        "error_count": 0
    }

@app.get("/api/metrics")
async def get_metrics():
    """Get trading metrics"""
    return {
        "trades_executed": 23,
        "success_rate": 85.2,
        "total_profit": 145.75,
        "daily_pnl": 24.50,
        "memory_usage": 45.2,
        "cpu_usage": 12.8
    }

@app.get("/api/exchanges")
async def get_exchanges():
    """Get exchange status"""
    return [
        {
            "name": "Kraken",
            "connected": True,
            "last_ping_ms": 45,
            "error_count": 0,
            "reliability_score": 0.98,
            "enabled": True,
            "balance": 200.00
        },
        {
            "name": "Bybit", 
            "connected": True,
            "last_ping_ms": 62,
            "error_count": 1,
            "reliability_score": 0.95,
            "enabled": True,
            "balance": 200.00
        },
        {
            "name": "MEXC",
            "connected": True,
            "last_ping_ms": 78,
            "error_count": 0,
            "reliability_score": 0.92,
            "enabled": True,
            "balance": 200.00
        }
    ]

@app.get("/api/opportunities")
async def get_opportunities():
    """Get active arbitrage opportunities"""
    return [
        {
            "opportunity_id": "btc_kraken_bybit_001",
            "strategy_name": "Spatial Arbitrage",
            "symbol": "BTC/USDT",
            "status": "active",
            "amount": 0.1,
            "expected_profit": 24.50,
            "expected_profit_percent": 0.82,
            "risk_score": 0.3,
            "confidence_level": 0.85,
            "detected_at": "2025-08-30T19:55:30",
            "buy_exchange": "Kraken",
            "sell_exchange": "Bybit"
        },
        {
            "opportunity_id": "eth_mexc_kraken_002",
            "strategy_name": "Spatial Arbitrage", 
            "symbol": "ETH/USDT",
            "status": "analyzing",
            "amount": 0.5,
            "expected_profit": 15.20,
            "expected_profit_percent": 0.64,
            "risk_score": 0.4,
            "confidence_level": 0.78,
            "detected_at": "2025-08-30T19:56:15",
            "buy_exchange": "MEXC",
            "sell_exchange": "Kraken"
        }
    ]

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve main dashboard"""
    dashboard_file = static_path / "index.html"
    if dashboard_file.exists():
        return HTMLResponse(content=dashboard_file.read_text())
    else:
        # Return basic dashboard if file not found
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SmartArb Engine Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0f1419; color: white; }
                .container { max-width: 800px; margin: 0 auto; }
                .status { color: #00ff88; font-size: 1.2em; margin: 20px 0; }
                .api-links { margin-top: 40px; }
                .api-links a { color: #00d2ff; text-decoration: none; margin: 0 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 SmartArb Engine Dashboard</h1>
                <div class="status">✅ System Online</div>
                <p>Dashboard is running on your Raspberry Pi!</p>
                
                <div class="api-links">
                    <h3>API Endpoints:</h3>
                    <a href="/health">Health Check</a>
                    <a href="/api/status">Status</a>
                    <a href="/api/metrics">Metrics</a>
                    <a href="/api/exchanges">Exchanges</a>
                    <a href="/api/opportunities">Opportunities</a>
                </div>
                
                <p style="margin-top: 40px;">
                    <strong>Next Steps:</strong><br>
                    1. Run: ./deploy_dashboard.sh<br>
                    2. Refresh this page<br>
                    3. Enjoy your full dashboard!
                </p>
            </div>
        </body>
        </html>
        """)

@app.get("/manifest.json")
async def manifest():
    """Serve PWA manifest"""
    return {
        "name": "SmartArb Engine Dashboard",
        "short_name": "SmartArb",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f1419",
        "theme_color": "#00d2ff",
        "icons": [
            {"src": "/static/icon-192x192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512x512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting SmartArb Engine Dashboard...")
    print(f"📁 Static files path: {static_path}")
    print(f"📊 Dashboard will be available at: http://0.0.0.0:8000")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
