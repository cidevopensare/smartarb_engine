#!/usr/bin/env python3
“””
SmartArb Engine Test Suite

This module contains comprehensive tests for the SmartArb Engine:

- Configuration management tests
- Exchange integration tests
- Strategy logic tests
- Risk management tests
- AI integration tests
- End-to-end system tests
  “””

import pytest
import sys
from pathlib import Path

# Add src to path for testing

sys.path.insert(0, str(Path(**file**).parent.parent))

**version** = “1.0.0”

# Test configuration

TEST_CONFIG = {
‘use_mock_exchanges’: True,
‘test_data_path’: Path(**file**).parent / ‘data’,
‘temp_config_dir’: ‘/tmp/smartarb_tests’,
‘log_level’: ‘DEBUG’
}

def get_test_config():
“”“Get test configuration”””
return TEST_CONFIG.copy()

# Test utilities

class MockExchange:
“”“Mock exchange for testing”””

```
def __init__(self, name: str):
    self.name = name
    self.connected = True
    
async def get_ticker(self, symbol: str):
    """Mock ticker data"""
    from src.exchanges.base_exchange import Ticker
    from decimal import Decimal
    import time
    
    return Ticker(
        symbol=symbol,
        bid=Decimal('50000.00'),
        ask=Decimal('50001.00'),
        last=Decimal('50000.50'),
        volume=Decimal('100.0'),
        timestamp=time.time()
    )
```

def create_test_config(temp_dir: Path) -> Path:
“”“Create minimal test configuration”””

```
config_content = """
```

engine:
name: “Test SmartArb Engine”
version: “1.0.0”
debug_mode: true

logging:
log_level: “DEBUG”
log_directory: “logs”

risk_management:
max_daily_loss: 10
max_position_size: 100

strategies:
spatial_arbitrage:
enabled: true
min_spread_percent: 0.1

exchanges:
mock_exchange_1:
enabled: true
api_key: “test_key”
api_secret: “test_secret”
mock_exchange_2:
enabled: true  
api_key: “test_key”
api_secret: “test_secret”
“””

```
config_path = temp_dir / 'test_config.yaml'
with open(config_path, 'w') as f:
    f.write(config_content)

return config_path
```

# Test fixtures (if using pytest)

@pytest.fixture
def test_config_path(tmp_path):
“”“Pytest fixture for test configuration”””
return create_test_config(tmp_path)

@pytest.fixture  
def mock_exchanges():
“”“Pytest fixture for mock exchanges”””
return {
‘mock_exchange_1’: MockExchange(‘mock_exchange_1’),
‘mock_exchange_2’: MockExchange(‘mock_exchange_2’)
}

**all** = [
‘TEST_CONFIG’,
‘get_test_config’,
‘MockExchange’,
‘create_test_config’,
‘test_config_path’,
‘mock_exchanges’
]