#!/usr/bin/env python3
“””
SmartArb Engine - Professional Cryptocurrency Arbitrage Trading Bot

A sophisticated arbitrage trading system designed for Raspberry Pi 5
with AI-powered optimization using Claude AI.

Features:

- Multi-exchange arbitrage (Kraken, Bybit, MEXC)
- Real-time market data processing
- Risk management and safety controls
- Claude AI integration for automated optimization
- Raspberry Pi optimized performance
- Professional grade logging and monitoring
  “””

**version** = “1.0.0”
**author** = “SmartArb Team”
**email** = “support@smartarb.com”
**license** = “MIT”

# Package information

PROJECT_NAME = “SmartArb Engine”
PROJECT_URL = “https://github.com/smartarb/smartarb_engine”
DOCUMENTATION_URL = “https://docs.smartarb.com”

# Version compatibility

PYTHON_REQUIRES = “>=3.11.0”
SUPPORTED_PLATFORMS = [“linux”, “darwin”, “win32”]

# Exchange support matrix

SUPPORTED_EXCHANGES = {
“kraken”: {
“name”: “Kraken”,
“spot”: True,
“futures”: False,
“api_version”: “0”,
“websocket”: True
},
“bybit”: {
“name”: “Bybit”,
“spot”: True,
“futures”: True,
“api_version”: “5”,
“websocket”: True
},
“mexc”: {
“name”: “MEXC”,
“spot”: True,
“futures”: False,
“api_version”: “3”,
“websocket”: True
}
}

# Trading strategies

SUPPORTED_STRATEGIES = {
“spatial_arbitrage”: {
“name”: “Spatial Arbitrage”,
“description”: “Cross-exchange price differential exploitation”,
“implemented”: True,
“risk_level”: “medium”
},
“triangular_arbitrage”: {
“name”: “Triangular Arbitrage”,
“description”: “Three-currency arbitrage within single exchange”,
“implemented”: False,
“risk_level”: “high”
},
“statistical_arbitrage”: {
“name”: “Statistical Arbitrage”,
“description”: “Mean reversion and correlation-based strategies”,
“implemented”: False,
“risk_level”: “medium”
}
}

# AI Features

AI_FEATURES = {
“claude_integration”: True,
“auto_optimization”: True,
“performance_analysis”: True,
“code_updates”: True,
“risk_assessment”: True,
“market_analysis”: True
}

def get_version() -> str:
“”“Get package version”””
return **version**

def get_package_info() -> dict:
“”“Get complete package information”””
return {
“name”: PROJECT_NAME,
“version”: **version**,
“author”: **author**,
“license”: **license**,
“python_requires”: PYTHON_REQUIRES,
“supported_platforms”: SUPPORTED_PLATFORMS,
“supported_exchanges”: SUPPORTED_EXCHANGES,
“supported_strategies”: SUPPORTED_STRATEGIES,
“ai_features”: AI_FEATURES
}

def check_requirements() -> bool:
“”“Check if system meets minimum requirements”””
import sys
import platform

```
# Check Python version
if sys.version_info < (3, 11):
    print(f"❌ Python 3.11+ required, found {sys.version}")
    return False

# Check platform
if sys.platform not in SUPPORTED_PLATFORMS:
    print(f"⚠️  Platform {sys.platform} not officially supported")

return True
```

# Module exports

**all** = [
“**version**”,
“**author**”,
“**license**”,
“PROJECT_NAME”,
“SUPPORTED_EXCHANGES”,
“SUPPORTED_STRATEGIES”,
“AI_FEATURES”,
“get_version”,
“get_package_info”,
“check_requirements”
]