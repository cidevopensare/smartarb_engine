“””
Base Exchange Interface for SmartArb Engine
Defines the standard interface that all exchange connectors must implement
“””

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
import time
import structlog

logger = structlog.get_logger(**name**)

class OrderSide(Enum):
“”“Order side enumeration”””
BUY = “buy”
SELL = “sell”

class OrderStatus(Enum):
“”“Order status enumeration”””
OPEN = “open”
FILLED = “filled”
CANCELED = “canceled”
PARTIALLY_FILLED = “partially_filled”
REJECTED = “rejected”

class ExchangeError(Exception):
“”“Base exception for exchange-related errors”””
pass

class ExchangeConnectionError(ExchangeError):
“”“Exception for connection-related errors”””
pass

class ExchangeAPIError(ExchangeError):
“”“Exception for API-related errors”””
pass

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
def spread(self) -> Decimal:
    """Calculate bid-ask spread"""
    return self.ask - self.bid

@property
def spread_percent(self) -> Decimal:
    """Calculate bid-ask spread as percentage"""
    if self.ask > 0:
        return (self.spread / self.ask) * 100
    return Decimal('0')
```

@dataclass
class OrderBookLevel:
“”“Order book level data”””
price: Decimal
amount: Decimal

@dataclass
class OrderBook:
“”“Order book data structure”””
symbol: str
bids: List[OrderBookLevel]
asks: List[OrderBookLevel]
timestamp: float

```
@property
def best_bid(self) -> Optional[OrderBookLevel]:
    """Get best bid (highest buy price)"""
    return self.bids[0] if self.bids else None

@property
def best_ask(self) -> Optional[OrderBookLevel]:
    """Get best ask (lowest sell price)"""
    return self.asks[0] if self.asks else None

@property
def spread(self) -> Decimal:
    """Calculate spread between best bid and ask"""
    if self.best_bid and self.best_ask:
        return self.best_ask.price - self.best_bid.price
    return Decimal('0')
```

@dataclass
class Balance:
“”“Account balance data”””
asset: str
free: Decimal  # Available for trading
locked: Decimal  # Locked in orders

```
@property
def total(self) -> Decimal:
    """Total balance (free + locked)"""
    return self.free + self.locked
```

@dataclass
class Order:
“”“Order data structure”””
order_id: str
symbol: str
side: OrderSide
amount: Decimal
price: Decimal
status: OrderStatus
filled_amount: Decimal = Decimal(‘0’)
average_price: Decimal = Decimal(‘0’)
fees: Decimal = Decimal(‘0’)
timestamp: float = 0

```
@property
def remaining_amount(self) -> Decimal:
    """Calculate remaining unfilled amount"""
    return self.amount - self.filled_amount

@property
def is_filled(self) -> bool:
    """Check if order is completely filled"""
    return self.status == OrderStatus.FILLED
```

class BaseExchange(ABC):
“””
Abstract base class for all exchange connectors

```
All exchange implementations must inherit from this class and implement
the abstract methods to ensure consistent interface across exchanges.
"""

def __init__(self, config: Dict[str, Any]):
    """Initialize exchange with configuration"""
    self.config = config
    self.name = config.get('name', 'Unknown')
    self.api_key = config.get('api_key', '')
    self.api_secret = config.get('api_secret', '')
    self.sandbox = config.get('sandbox', False)
    
    # Connection settings
    self.base_url = config.get('base_url', '')
    self.rate_limit = config.get('rate_limit', 10)  # requests per second
    self.timeout = config.get('timeout', 30)  # seconds
    
    # Trading settings
    self.min_order_size = Decimal(str(config.get('min_order_size', 10)))
    self.max_order_size = Decimal(str(config.get('max_order_size', 100000)))
    self.maker_fee = Decimal(str(config.get('maker_fee', 0.001)))
    self.taker_fee = Decimal(str(config.get('taker_fee', 0.001)))
    
    # State tracking
    self.is_connected = False
    self.last_request_time = 0
    self.request_count = 0
    
    # Performance tracking
    self.total_requests = 0
    self.failed_requests = 0
    self.avg_response_time = 0
    
# Connection Management
@abstractmethod
async def connect(self) -> bool:
    """Establish connection to the exchange"""
    pass

@abstractmethod
async def disconnect(self) -> None:
    """Disconnect from the exchange"""
    pass

# Market Data
@abstractmethod
async def get_ticker(self, symbol: str) -> Ticker:
    """Get current ticker for symbol"""
    pass

@abstractmethod
async def get_orderbook(self, symbol: str, depth: int = 10) -> OrderBook:
    """Get current order book for symbol"""
    pass

@abstractmethod
async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
    """Get account balance(s)"""
    pass

# Trading Operations
@abstractmethod
async def place_order(self, symbol: str, side: OrderSide, 
                     amount: Decimal, price: Decimal,
                     order_type: str = "limit") -> Order:
    """Place a new order"""
    pass

@abstractmethod
async def cancel_order(self, order_id: str, symbol: str) -> bool:
    """Cancel an existing order"""
    pass

@abstractmethod
async def get_order_status(self, order_id: str, symbol: str) -> Order:
    """Get current status of an order"""
    pass

# Utility Methods
async def _rate_limit(self) -> None:
    """Implement rate limiting"""
    now = time.time()
    time_since_last = now - self.last_request_time
    min_interval = 1.0 / self.rate_limit
    
    if time_since_last < min_interval:
        sleep_time = min_interval - time_since_last
        await asyncio.sleep(sleep_time)
    
    self.last_request_time = time.time()
    self.total_requests += 1

def _handle_error(self, error: Exception, context: str = "") -> None:
    """Handle and log errors consistently"""
    self.failed_requests += 1
    
    error_msg = str(error)
    logger.error("exchange_error",
                exchange=self.name,
                context=context,
                error=error_msg,
                error_type=type(error).__name__)
    
    # Re-raise as appropriate exchange error
    if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
        raise ExchangeConnectionError(f"{self.name}: {error_msg}")
    else:
        raise ExchangeAPIError(f"{self.name}: {error_msg}")

def normalize_symbol(self, symbol: str) -> str:
    """Normalize symbol to exchange format"""
    # Default implementation - override in specific exchanges
    return symbol

def normalize_amount(self, amount: Decimal) -> Decimal:
    """Normalize amount to exchange precision"""
    # Default implementation - override in specific exchanges
    return amount.quantize(Decimal('0.00000001'))

def normalize_price(self, price: Decimal) -> Decimal:
    """Normalize price to exchange precision"""
    # Default implementation - override in specific exchanges
    return price.quantize(Decimal('0.00000001'))

def get_trading_fee(self, is_maker: bool = True) -> Decimal:
    """Get applicable trading fee"""
    return self.maker_fee if is_maker else self.taker_fee

def is_valid_order_size(self, amount: Decimal) -> bool:
    """Check if order size is within limits"""
    return self.min_order_size <= amount <= self.max_order_size

def get_exchange_info(self) -> Dict[str, Any]:
    """Get exchange information and status"""
    return {
        'name': self.name,
        'connected': self.is_connected,
        'sandbox': self.sandbox,
        'total_requests': self.total_requests,
        'failed_requests': self.failed_requests,
        'error_rate': self.failed_requests / max(self.total_requests, 1) * 100,
        'rate_limit': self.rate_limit,
        'maker_fee': float(self.maker_fee),
        'taker_fee': float(self.taker_fee)
    }

async def health_check(self) -> bool:
    """Perform health check on exchange connection"""
    try:
        if not self.is_connected:
            return False
        
        # Test with a simple API call (server time)
        # This should be implemented by each exchange
        return True
        
    except Exception as e:
        logger.warning("health_check_failed", exchange=self.name, error=str(e))
        return False

def __str__(self) -> str:
    """String representation"""
    return f"{self.name}Exchange(connected={self.is_connected})"

def __repr__(self) -> str:
    """Detailed string representation"""
    return (f"{self.name}Exchange(connected={self.is_connected}, "
            f"requests={self.total_requests}, errors={self.failed_requests})")
```