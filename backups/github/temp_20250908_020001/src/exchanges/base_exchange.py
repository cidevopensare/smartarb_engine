#!/usr/bin/env python3
“””
Base Exchange Interface for SmartArb Engine
Abstract base class defining the standard interface for all exchange implementations
“””

import asyncio
import ccxt.async_support as ccxt
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import structlog
import time
from datetime import datetime, timedelta
import json

logger = structlog.get_logger(**name**)

class OrderSide(Enum):
“”“Order side enumeration”””
BUY = “buy”
SELL = “sell”

class OrderType(Enum):
“”“Order type enumeration”””
MARKET = “market”
LIMIT = “limit”
STOP_LIMIT = “stop_limit”

class OrderStatus(Enum):
“”“Order status enumeration”””
PENDING = “pending”
OPEN = “open”
FILLED = “filled”
CANCELLED = “cancelled”
REJECTED = “rejected”
EXPIRED = “expired”

@dataclass
class OrderBook:
“”“Order book data structure”””
symbol: str
bids: List[Tuple[Decimal, Decimal]]  # [(price, amount), …]
asks: List[Tuple[Decimal, Decimal]]  # [(price, amount), …]
timestamp: float

```
@property
def best_bid(self) -> Optional[Tuple[Decimal, Decimal]]:
    """Get best bid price and amount"""
    return self.bids[0] if self.bids else None

@property
def best_ask(self) -> Optional[Tuple[Decimal, Decimal]]:
    """Get best ask price and amount"""
    return self.asks[0] if self.asks else None

@property
def spread(self) -> Optional[Decimal]:
    """Get bid-ask spread"""
    if self.best_bid and self.best_ask:
        return self.best_ask[0] - self.best_bid[0]
    return None

@property
def spread_percentage(self) -> Optional[Decimal]:
    """Get spread as percentage of mid price"""
    if self.spread and self.best_bid and self.best_ask:
        mid_price = (self.best_bid[0] + self.best_ask[0]) / 2
        return (self.spread / mid_price) * 100
    return None
```

@dataclass
class Ticker:
“”“Ticker data structure”””
symbol: str
bid: Decimal
ask: Decimal
last: Decimal
volume: Decimal
timestamp: float

```
@property
def mid_price(self) -> Decimal:
    """Get mid price"""
    return (self.bid + self.ask) / 2
```

@dataclass
class Balance:
“”“Account balance data structure”””
asset: str
free: Decimal
locked: Decimal
total: Decimal

```
def __post_init__(self):
    # Ensure total = free + locked
    if self.total != self.free + self.locked:
        self.total = self.free + self.locked
```

@dataclass
class Trade:
“”“Trade data structure”””
id: str
symbol: str
side: OrderSide
amount: Decimal
price: Decimal
cost: Decimal
fee: Decimal
fee_currency: str
timestamp: float
order_id: Optional[str] = None

@dataclass
class Order:
“”“Order data structure”””
id: str
symbol: str
side: OrderSide
type: OrderType
amount: Decimal
price: Optional[Decimal]
status: OrderStatus
filled: Decimal
remaining: Decimal
cost: Decimal
fee: Decimal
fee_currency: str
timestamp: float
trades: List[Trade]

class ExchangeError(Exception):
“”“Base exception for exchange errors”””
pass

class ConnectionError(ExchangeError):
“”“Exchange connection error”””
pass

class AuthenticationError(ExchangeError):
“”“Exchange authentication error”””
pass

class InsufficientFundsError(ExchangeError):
“”“Insufficient funds error”””
pass

class OrderError(ExchangeError):
“”“Order-related error”””
pass

class RateLimitError(ExchangeError):
“”“Rate limit exceeded error”””
pass

class BaseExchange(ABC):
“””
Abstract base class for all exchange implementations

```
Provides a standardized interface for interacting with cryptocurrency exchanges
with proper error handling, rate limiting, and connection management.
"""

def __init__(self, config: Dict[str, Any]):
    """Initialize exchange"""
    self.config = config
    self.exchange_config = config.get('exchanges', {}).get(self.name, {})
    self.enabled = self.exchange_config.get('enabled', False)
    
    # Initialize CCXT exchange
    self.ccxt_exchange = None
    self.connected = False
    self.last_request_time = 0
    
    # Rate limiting
    self.rate_limit = self.exchange_config.get('rate_limit', 10)  # requests per second
    self.min_request_interval = 1.0 / self.rate_limit
    
    # Connection health
    self.connection_errors = 0
    self.max_connection_errors = 5
    self.last_health_check = 0
    self.health_check_interval = 60  # seconds
    
    # Trading pairs and market info
    self.markets = {}
    self.trading_pairs = set()
    self.fees = {}
    
    # Order management
    self.open_orders = {}
    self.order_history = {}
    
    self.logger = structlog.get_logger(f"exchange.{self.name}")

@property
@abstractmethod
def name(self) -> str:
    """Exchange name"""
    pass

@property
@abstractmethod
def ccxt_id(self) -> str:
    """CCXT exchange ID"""
    pass

async def initialize(self) -> bool:
    """Initialize exchange connection"""
    try:
        if not self.enabled:
            self.logger.info("exchange_disabled")
            return False
        
        # Initialize CCXT exchange
        self.ccxt_exchange = getattr(ccxt, self.ccxt_id)({
            'apiKey': self.exchange_config.get('api_key'),
            'secret': self.exchange_config.get('api_secret'),
            'sandbox': self.exchange_config.get('sandbox', False),
            'timeout': self.exchange_config.get('timeout', 30) * 1000,
            'enableRateLimit': True,
        })
        
        # Test connection
        await self._test_connection()
        
        # Load markets
        await self._load_markets()
        
        # Load trading pairs
        self.trading_pairs = set(self.exchange_config.get('trading_pairs', []))
        
        self.connected = True
        self.logger.info("exchange_initialized", 
                       trading_pairs=len(self.trading_pairs),
                       markets=len(self.markets))
        
        return True
        
    except Exception as e:
        self.logger.error("exchange_initialization_failed", error=str(e))
        return False

async def shutdown(self):
    """Shutdown exchange connection"""
    if self.ccxt_exchange:
        await self.ccxt_exchange.close()
    self.connected = False
    self.logger.info("exchange_shutdown_completed")

async def _test_connection(self):
    """Test exchange connection"""
    try:
        await self.ccxt_exchange.fetch_status()
        self.connection_errors = 0
    except Exception as e:
        self.connection_errors += 1
        self.logger.error("connection_test_failed", error=str(e))
        raise ConnectionError(f"Connection test failed: {str(e)}")

async def _load_markets(self):
    """Load market information"""
    try:
        self.markets = await self.ccxt_exchange.load_markets()
        self.logger.info("markets_loaded", count=len(self.markets))
    except Exception as e:
        self.logger.error("markets_load_failed", error=str(e))
        raise

async def _rate_limit(self):
    """Implement rate limiting"""
    current_time = time.time()
    time_since_last_request = current_time - self.last_request_time
    
    if time_since_last_request < self.min_request_interval:
        sleep_time = self.min_request_interval - time_since_last_request
        await asyncio.sleep(sleep_time)
    
    self.last_request_time = time.time()

async def _handle_request(self, func, *args, **kwargs):
    """Handle API request with error handling and rate limiting"""
    await self._rate_limit()
    
    try:
        result = await func(*args, **kwargs)
        self.connection_errors = 0
        return result
        
    except ccxt.NetworkError as e:
        self.connection_errors += 1
        self.logger.warning("network_error", error=str(e), 
                          connection_errors=self.connection_errors)
        
        if self.connection_errors >= self.max_connection_errors:
            self.connected = False
            raise ConnectionError(f"Too many connection errors: {str(e)}")
        
        raise ConnectionError(str(e))
        
    except ccxt.AuthenticationError as e:
        self.logger.error("authentication_error", error=str(e))
        raise AuthenticationError(str(e))
        
    except ccxt.InsufficientFunds as e:
        self.logger.warning("insufficient_funds", error=str(e))
        raise InsufficientFundsError(str(e))
        
    except ccxt.InvalidOrder as e:
        self.logger.warning("invalid_order", error=str(e))
        raise OrderError(str(e))
        
    except ccxt.RateLimitExceeded as e:
        self.logger.warning("rate_limit_exceeded", error=str(e))
        await asyncio.sleep(1)  # Wait before retrying
        raise RateLimitError(str(e))
        
    except Exception as e:
        self.logger.error("unexpected_error", error=str(e))
        raise ExchangeError(str(e))

# Abstract methods that must be implemented by subclasses

@abstractmethod
async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
    """Get order book for symbol"""
    pass

@abstractmethod
async def get_ticker(self, symbol: str) -> Ticker:
    """Get ticker for symbol"""
    pass

@abstractmethod
async def get_balance(self, asset: str = None) -> Dict[str, Balance]:
    """Get account balance"""
    pass

@abstractmethod
async def place_order(self, symbol: str, side: OrderSide, 
                     amount: Decimal, price: Optional[Decimal] = None,
                     order_type: OrderType = OrderType.MARKET) -> Order:
    """Place order"""
    pass

@abstractmethod
async def cancel_order(self, order_id: str, symbol: str) -> bool:
    """Cancel order"""
    pass

@abstractmethod
async def get_order(self, order_id: str, symbol: str) -> Order:
    """Get order status"""
    pass

@abstractmethod
async def get_open_orders(self, symbol: str = None) -> List[Order]:
    """Get open orders"""
    pass

@abstractmethod
async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
    """Get trade history"""
    pass

# Health check methods

async def health_check(self) -> Dict[str, Any]:
    """Perform exchange health check"""
    current_time = time.time()
    
    if current_time - self.last_health_check < self.health_check_interval:
        return {"status": "ok", "cached": True}
    
    try:
        # Test basic connectivity
        await self._test_connection()
        
        # Check if we can fetch a ticker
        if self.trading_pairs:
            test_symbol = list(self.trading_pairs)[0]
            await self.get_ticker(test_symbol)
        
        self.last_health_check = current_time
        
        return {
            "status": "ok",
            "connected": self.connected,
            "connection_errors": self.connection_errors,
            "trading_pairs": len(self.trading_pairs),
            "last_check": current_time
        }
        
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "error": str(e),
            "connection_errors": self.connection_errors
        }

def get_min_order_size(self, symbol: str) -> Decimal:
    """Get minimum order size for symbol"""
    market = self.markets.get(symbol)
    if market and 'limits' in market and 'amount' in market['limits']:
        return Decimal(str(market['limits']['amount']['min'] or 0))
    return Decimal('0.001')  # Default minimum

def get_price_precision(self, symbol: str) -> int:
    """Get price precision for symbol"""
    market = self.markets.get(symbol)
    if market and 'precision' in market and 'price' in market['precision']:
        return market['precision']['price']
    return 8  # Default precision

def get_amount_precision(self, symbol: str) -> int:
    """Get amount precision for symbol"""
    market = self.markets.get(symbol)
    if market and 'precision' in market and 'amount' in market['precision']:
        return market['precision']['amount']
    return 8  # Default precision
```