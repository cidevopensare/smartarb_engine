“””
REST API for SmartArb Engine
FastAPI-based REST API for monitoring and controlling the trading bot
“””

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import structlog

from fastapi import FastAPI, HTTPException, Depends, Query, Path, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

from ..core.engine import SmartArbEngine, EngineStatus
from ..database.manager import DatabaseManager
from ..utils.config import ConfigManager

logger = structlog.get_logger(**name**)

# Pydantic models for API

class HealthResponse(BaseModel):
status: str
timestamp: datetime
version: str = “1.0.0”
uptime_seconds: float
database_connected: bool
exchanges_connected: int
active_strategies: int

class ExchangeStatus(BaseModel):
name: str
connected: bool
last_ping_ms: Optional[int]
error_count: int
reliability_score: float
enabled: bool

class TradingPairInfo(BaseModel):
symbol: str
base_asset: str
quote_asset: str
enabled: bool
min_trade_amount: float
max_trade_amount: float
min_spread_percent: float

class OpportunityInfo(BaseModel):
opportunity_id: str
strategy_name: str
symbol: str
status: str
amount: float
expected_profit: float
expected_profit_percent: float
risk_score: float
confidence_level: float
detected_at: datetime
buy_exchange: Optional[str] = None
sell_exchange: Optional[str] = None

class ExecutionInfo(BaseModel):
execution_id: str
opportunity_id: str
status: str
actual_profit: float
fees_paid: float
slippage: float
execution_time: Optional[float]
started_at: Optional[datetime]
completed_at: Optional[datetime]

class BalanceInfo(BaseModel):
exchange: str
asset: str
total_balance: float
available_balance: float
locked_balance: float
usd_value: Optional[float]

class StrategyMetrics(BaseModel):
name: str
enabled: bool
opportunities_found: int
opportunities_executed: int
success_rate: float
total_profit: float
avg_profit_per_trade: float
last_opportunity_at: Optional[datetime]

class RiskStatus(BaseModel):
circuit_breaker_active: bool
active_positions: int
daily_trades: int
daily_volume: float
daily_pnl: float
total_exposure: float
utilization: Dict[str, float]

class TradingSummary(BaseModel):
period_days: int
total_opportunities: int
executed_opportunities: int
opportunity_success_rate: float
total_executions: int
successful_executions: int
execution_success_rate: float
total_profit: float
average_profit: float

class ConfigUpdate(BaseModel):
section: str
key: str
value: Union[str, int, float, bool, Dict, List]

class CommandRequest(BaseModel):
command: str
parameters: Optional[Dict[str, Any]] = None

# FastAPI app

app = FastAPI(
title=“SmartArb Engine API”,
description=“REST API for SmartArb cryptocurrency arbitrage trading bot”,
version=“1.0.0”,
docs_url=”/docs”,
redoc_url=”/redoc”
)

# Middleware

app.add_middleware(
CORSMiddleware,
allow_origins=[”*”],  # In production, specify exact origins
allow_credentials=True,
allow_methods=[”*”],
allow_headers=[”*”],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security

security = HTTPBearer(auto_error=False)

# Global variables (would be dependency injection in production)

engine: Optional[SmartArbEngine] = None
db_manager: Optional[DatabaseManager] = None
config_manager: Optional[ConfigManager] = None
start_time: datetime = datetime.now()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
“”“Simple authentication (in production, use proper JWT validation)”””
if credentials is None:
return None  # Allow unauthenticated access for monitoring

```
# In production, validate JWT token here
# For now, just check for a simple token
if credentials.credentials == "smartarb_api_token":
    return {"user_id": "admin", "role": "admin"}

return None
```

def require_auth(user=Depends(get_current_user)):
“”“Require authentication for sensitive endpoints”””
if user is None:
raise HTTPException(status_code=401, detail=“Authentication required”)
return user

# Startup and shutdown events

@app.on_event(“startup”)
async def startup_event():
“”“Initialize API dependencies”””
global engine, db_manager, config_manager

```
try:
    # Initialize config manager
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    # Initialize database manager
    db_manager = DatabaseManager(config)
    await db_manager.initialize()
    
    # Initialize engine (but don't start it automatically)
    engine = SmartArbEngine()
    await engine.initialize()
    
    logger.info("api_started", port=8000)
    
except Exception as e:
    logger.error("api_startup_failed", error=str(e))
    raise
```

@app.on_event(“shutdown”)
async def shutdown_event():
“”“Cleanup on shutdown”””
global engine, db_manager

```
try:
    if engine:
        await engine.shutdown()
    
    if db_manager:
        await db_manager.shutdown()
    
    logger.info("api_shutdown_completed")
    
except Exception as e:
    logger.error("api_shutdown_error", error=str(e))
```

# Health and status endpoints

@app.get(”/health”, response_model=HealthResponse)
async def health_check():
“”“Health check endpoint”””
global engine, db_manager, start_time

```
uptime = (datetime.now() - start_time).total_seconds()

# Count connected exchanges
exchanges_connected = 0
if engine and engine.exchanges:
    exchanges_connected = len([ex for ex in engine.exchanges.values() if ex.is_connected])

# Count active strategies
active_strategies = 0
if engine and engine.strategy_manager:
    active_strategies = len(engine.strategy_manager.enabled_strategies)

return HealthResponse(
    status="healthy" if engine and engine.is_running else "stopped",
    timestamp=datetime.now(),
    uptime_seconds=uptime,
    database_connected=db_manager.is_connected if db_manager else False,
    exchanges_connected=exchanges_connected,
    active_strategies=active_strategies
)
```

@app.get(”/status”)
async def get_engine_status():
“”“Get detailed engine status”””
if not engine:
raise HTTPException(status_code=503, detail=“Engine not initialized”)

```
try:
    status = await engine.get_engine_status()
    return status
except Exception as e:
    logger.error("status_retrieval_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

@app.get(”/metrics”)
async def get_detailed_metrics():
“”“Get detailed system metrics”””
if not engine:
raise HTTPException(status_code=503, detail=“Engine not initialized”)

```
try:
    metrics = await engine.get_detailed_metrics()
    return metrics
except Exception as e:
    logger.error("metrics_retrieval_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

# Exchange endpoints

@app.get(”/exchanges”, response_model=List[ExchangeStatus])
async def get_exchanges():
“”“Get exchange status information”””
if not engine or not engine.exchanges:
return []

```
exchanges = []
for name, exchange in engine.exchanges.items():
    exchanges.append(ExchangeStatus(
        name=name,
        connected=exchange.is_connected,
        last_ping_ms=getattr(exchange, 'last_ping_ms', None),
        error_count=getattr(exchange, 'error_count', 0),
        reliability_score=getattr(exchange, 'reliability_score', 1.0),
        enabled=getattr(exchange, 'enabled', True)
    ))

return exchanges
```

@app.get(”/exchanges/{exchange_name}/test”)
async def test_exchange_connection(exchange_name: str):
“”“Test connection to specific exchange”””
if not engine or exchange_name not in engine.exchanges:
raise HTTPException(status_code=404, detail=“Exchange not found”)

```
exchange = engine.exchanges[exchange_name]

try:
    # Test basic connection
    is_connected = await exchange.connect()
    
    # Test API functionality
    test_results = {
        "connection": is_connected,
        "api_test": False,
        "latency_ms": None
    }
    
    if is_connected:
        start_time = datetime.now()
        try:
            # Test with a simple API call
            ticker = await exchange.get_ticker("BTC/USDT")
            end_time = datetime.now()
            
            test_results["api_test"] = ticker is not None
            test_results["latency_ms"] = (end_time - start_time).total_seconds() * 1000
            
        except Exception as e:
            test_results["api_error"] = str(e)
    
    return test_results
    
except Exception as e:
    logger.error("exchange_test_failed", exchange=exchange_name, error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

# Trading pair endpoints

@app.get(”/trading-pairs”, response_model=List[TradingPairInfo])
async def get_trading_pairs():
“”“Get trading pair information”””
if not db_manager:
raise HTTPException(status_code=503, detail=“Database not available”)

```
try:
    pairs = await db_manager.get_trading_pairs()
    return [
        TradingPairInfo(
            symbol=pair.symbol,
            base_asset=pair.base_asset,
            quote_asset=pair.quote_asset,
            enabled=pair.is_enabled,
            min_trade_amount=float(pair.min_trade_amount),
            max_trade_amount=float(pair.max_trade_amount),
            min_spread_percent=float(pair.min_spread_percent)
        )
        for pair in pairs
    ]
except Exception as e:
    logger.error("trading_pairs_retrieval_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

# Strategy endpoints

@app.get(”/strategies”, response_model=List[StrategyMetrics])
async def get_strategies():
“”“Get strategy information and metrics”””
if not engine or not engine.strategy_manager:
return []

```
strategies = []
for name, strategy in engine.strategy_manager.strategies.items():
    stats = strategy.get_strategy_stats()
    
    strategies.append(StrategyMetrics(
        name=name,
        enabled=strategy.enabled,
        opportunities_found=stats.get('opportunities_found', 0),
        opportunities_executed=stats.get('opportunities_executed', 0),
        success_rate=stats.get('success_rate', 0),
        total_profit=stats.get('total_profit', 0),
        avg_profit_per_trade=stats.get('avg_profit_per_trade', 0),
        last_opportunity_at=None  # Would need to implement this
    ))

return strategies
```

@app.post(”/strategies/{strategy_name}/enable”)
async def enable_strategy(strategy_name: str, user=Depends(require_auth)):
“”“Enable a trading strategy”””
if not engine or not engine.strategy_manager:
raise HTTPException(status_code=503, detail=“Strategy manager not available”)

```
if strategy_name not in engine.strategy_manager.strategies:
    raise HTTPException(status_code=404, detail="Strategy not found")

strategy = engine.strategy_manager.strategies[strategy_name]
strategy.enabled = True

if strategy_name not in engine.strategy_manager.enabled_strategies:
    engine.strategy_manager.enabled_strategies.append(strategy_name)

logger.info("strategy_enabled", strategy=strategy_name, user=user["user_id"])
return {"message": f"Strategy {strategy_name} enabled"}
```

@app.post(”/strategies/{strategy_name}/disable”)
async def disable_strategy(strategy_name: str, user=Depends(require_auth)):
“”“Disable a trading strategy”””
if not engine or not engine.strategy_manager:
raise HTTPException(status_code=503, detail=“Strategy manager not available”)

```
if strategy_name not in engine.strategy_manager.strategies:
    raise HTTPException(status_code=404, detail="Strategy not found")

strategy = engine.strategy_manager.strategies[strategy_name]
strategy.enabled = False

if strategy_name in engine.strategy_manager.enabled_strategies:
    engine.strategy_manager.enabled_strategies.remove(strategy_name)

logger.info("strategy_disabled", strategy=strategy_name, user=user["user_id"])
return {"message": f"Strategy {strategy_name} disabled"}
```

# Opportunity endpoints

@app.get(”/opportunities”, response_model=List[OpportunityInfo])
async def get_opportunities(
limit: int = Query(50, ge=1, le=200),
status: Optional[str] = Query(None),
strategy: Optional[str] = Query(None),
hours_back: int = Query(24, ge=1, le=168)  # Max 1 week
):
“”“Get recent opportunities”””
if not db_manager:
raise HTTPException(status_code=503, detail=“Database not available”)

```
try:
    # This would need to be implemented in the database manager
    # For now, return empty list
    return []
    
except Exception as e:
    logger.error("opportunities_retrieval_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

# Execution endpoints

@app.get(”/executions”, response_model=List[ExecutionInfo])
async def get_executions(
limit: int = Query(50, ge=1, le=200),
status: Optional[str] = Query(None),
hours_back: int = Query(24, ge=1, le=168)
):
“”“Get recent executions”””
if not db_manager:
raise HTTPException(status_code=503, detail=“Database not available”)

```
try:
    # This would need to be implemented in the database manager
    return []
    
except Exception as e:
    logger.error("executions_retrieval_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

# Portfolio endpoints

@app.get(”/portfolio/balances”, response_model=List[BalanceInfo])
async def get_portfolio_balances():
“”“Get current portfolio balances”””
if not engine or not engine.portfolio_manager:
raise HTTPException(status_code=503, detail=“Portfolio manager not available”)

```
try:
    await engine.portfolio_manager.update_portfolio(force_update=True)
    balances = engine.portfolio_manager.current_balances
    
    result = []
    for asset, balance in balances.items():
        for exchange_name, exchange_balance in balance.exchange_balances.items():
            result.append(BalanceInfo(
                exchange=exchange_name,
                asset=asset,
                total_balance=float(exchange_balance.total),
                available_balance=float(exchange_balance.free),
                locked_balance=float(exchange_balance.locked),
                usd_value=None  # Would need price data to calculate
            ))
    
    return result
    
except Exception as e:
    logger.error("portfolio_balances_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

@app.get(”/portfolio/summary”)
async def get_portfolio_summary():
“”“Get portfolio summary”””
if not engine or not engine.portfolio_manager:
raise HTTPException(status_code=503, detail=“Portfolio manager not available”)

```
try:
    summary = await engine.portfolio_manager.get_portfolio_summary()
    return summary
    
except Exception as e:
    logger.error("portfolio_summary_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

# Risk management endpoints

@app.get(”/risk/status”, response_model=RiskStatus)
async def get_risk_status():
“”“Get risk management status”””
if not engine or not engine.risk_manager:
raise HTTPException(status_code=503, detail=“Risk manager not available”)

```
try:
    status = engine.risk_manager.get_risk_status()
    return RiskStatus(**status)
    
except Exception as e:
    logger.error("risk_status_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

@app.post(”/risk/circuit-breaker/trigger”)
async def trigger_circuit_breaker(reason: str, user=Depends(require_auth)):
“”“Manually trigger circuit breaker”””
if not engine or not engine.risk_manager:
raise HTTPException(status_code=503, detail=“Risk manager not available”)

```
engine.risk_manager.trigger_circuit_breaker(f"Manual trigger by {user['user_id']}: {reason}")

logger.warning("circuit_breaker_triggered_manually", 
              user=user["user_id"], reason=reason)

return {"message": "Circuit breaker triggered", "reason": reason}
```

# Analytics endpoints

@app.get(”/analytics/summary”, response_model=TradingSummary)
async def get_trading_summary(days_back: int = Query(7, ge=1, le=30)):
“”“Get trading performance summary”””
if not db_manager:
raise HTTPException(status_code=503, detail=“Database not available”)

```
try:
    summary = await db_manager.get_trading_summary(days_back)
    return TradingSummary(**summary)
    
except Exception as e:
    logger.error("trading_summary_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

@app.get(”/analytics/performance”)
async def get_performance_metrics(
metric_type: Optional[str] = Query(None),
days_back: int = Query(7, ge=1, le=30)
):
“”“Get performance metrics”””
if not db_manager:
raise HTTPException(status_code=503, detail=“Database not available”)

```
try:
    metrics = await db_manager.get_performance_metrics(metric_type, days_back)
    return [
        {
            "metric_type": metric.metric_type,
            "metric_name": metric.metric_name,
            "value": float(metric.value),
            "timestamp": metric.created_at,
            "metadata": metric.metadata
        }
        for metric in metrics
    ]
    
except Exception as e:
    logger.error("performance_metrics_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

# Control endpoints (require authentication)

@app.post(”/engine/start”)
async def start_engine(user=Depends(require_auth)):
“”“Start the trading engine”””
if not engine:
raise HTTPException(status_code=503, detail=“Engine not initialized”)

```
if engine.is_running:
    return {"message": "Engine is already running"}

try:
    success = await engine.start()
    if success:
        logger.info("engine_started_via_api", user=user["user_id"])
        return {"message": "Engine started successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to start engine")
        
except Exception as e:
    logger.error("engine_start_failed", error=str(e), user=user["user_id"])
    raise HTTPException(status_code=500, detail=str(e))
```

@app.post(”/engine/stop”)
async def stop_engine(user=Depends(require_auth)):
“”“Stop the trading engine”””
if not engine:
raise HTTPException(status_code=503, detail=“Engine not initialized”)

```
if not engine.is_running:
    return {"message": "Engine is already stopped"}

try:
    await engine.shutdown()
    logger.info("engine_stopped_via_api", user=user["user_id"])
    return {"message": "Engine stopped successfully"}
    
except Exception as e:
    logger.error("engine_stop_failed", error=str(e), user=user["user_id"])
    raise HTTPException(status_code=500, detail=str(e))
```

@app.post(”/engine/emergency-stop”)
async def emergency_stop_engine(user=Depends(require_auth)):
“”“Emergency stop the trading engine”””
if not engine:
raise HTTPException(status_code=503, detail=“Engine not initialized”)

```
try:
    await engine.emergency_stop()
    logger.critical("emergency_stop_triggered_via_api", user=user["user_id"])
    return {"message": "Emergency stop executed"}
    
except Exception as e:
    logger.error("emergency_stop_failed", error=str(e), user=user["user_id"])
    raise HTTPException(status_code=500, detail=str(e))
```

# Configuration endpoints

@app.get(”/config”)
async def get_configuration():
“”“Get current configuration”””
if not config_manager:
raise HTTPException(status_code=503, detail=“Config manager not available”)

```
# Return configuration without sensitive data
config = config_manager.get_config()

# Remove sensitive information
safe_config = config.copy()
if 'exchanges' in safe_config:
    for exchange_name in safe_config['exchanges']:
        if 'api_key' in safe_config['exchanges'][exchange_name]:
            safe_config['exchanges'][exchange_name]['api_key'] = "***"
        if 'api_secret' in safe_config['exchanges'][exchange_name]:
            safe_config['exchanges'][exchange_name]['api_secret'] = "***"

return safe_config
```

@app.get(”/logs”)
async def get_recent_logs(
level: Optional[str] = Query(None),
lines: int = Query(100, ge=1, le=1000),
follow: bool = Query(False)
):
“”“Get recent log entries”””
if not db_manager:
raise HTTPException(status_code=503, detail=“Database not available”)

```
try:
    # This would need to be implemented in the database manager
    # For now, return empty list
    return []
    
except Exception as e:
    logger.error("logs_retrieval_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

# Database maintenance endpoints

@app.get(”/database/stats”)
async def get_database_stats():
“”“Get database statistics”””
if not db_manager:
raise HTTPException(status_code=503, detail=“Database not available”)

```
try:
    stats = await db_manager.get_database_stats()
    return stats
    
except Exception as e:
    logger.error("database_stats_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

@app.post(”/database/cleanup”)
async def cleanup_database(
days_to_keep: int = Query(30, ge=7, le=365),
user=Depends(require_auth)
):
“”“Clean up old database records”””
if not db_manager:
raise HTTPException(status_code=503, detail=“Database not available”)

```
try:
    await db_manager.cleanup_old_data(days_to_keep)
    logger.info("database_cleanup_completed", 
               days_to_keep=days_to_keep, user=user["user_id"])
    return {"message": f"Database cleaned up, keeping {days_to_keep} days of data"}
    
except Exception as e:
    logger.error("database_cleanup_failed", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

# Error handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
“”“Handle HTTP exceptions”””
return JSONResponse(
status_code=exc.status_code,
content={
“error”: exc.detail,
“timestamp”: datetime.now().isoformat(),
“path”: str(request.url)
}
)

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
“”“Handle general exceptions”””
logger.error(“api_unhandled_exception”,
error=str(exc), path=str(request.url))

```
return JSONResponse(
    status_code=500,
    content={
        "error": "Internal server error",
        "timestamp": datetime.now().isoformat(),
        "path": str(request.url)
    }
)
```

# Development server

def run_api_server(host: str = “0.0.0.0”, port: int = 8000, debug: bool = False):
“”“Run the API server”””
uvicorn.run(
“src.api.rest_api:app”,
host=host,
port=port,
reload=debug,
access_log=debug,
log_level=“info” if not debug else “debug”
)

if **name** == “**main**”:
run_api_server(debug=True)