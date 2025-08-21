"""
Base Exchange Interface for SmartArb Engine
Provides abstract interface for all exchange implementations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from decimal import Decimal
from enum import Enum
import asyncio
import time


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Ticker:
    """Price ticker information"""
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: Decimal
    timestamp: float
    
    @property
    def spread(self) -> Decimal:
        """Calculate bid-ask spread percentage"""
        if self.bid > 0:
            return ((self.ask - self.bid) / self.bid) * 100
        return Decimal('0')


@dataclass
class OrderBookLevel:
    """Single order book level"""
    price: Decimal
    quantity: Decimal


@dataclass
class OrderBook:
    """Order book snapshot"""
    symbol: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: float
    
    @property
    def best_bid(self) -> Optional[OrderBookLevel]:
        """Get best bid price"""
        return self.bids[0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[OrderBookLevel]:
        """Get best ask price"""
        return self.asks[0] if self.asks else None
    
    @property
    def spread(self) -> Decimal:
        """Calculate spread percentage"""
        if self.best_bid and self.best_ask and self.best_bid.price > 0:
            return ((self.best_ask.price - self.best_bid.price) / self.best_bid.price) * 100
        return Decimal('0')


@dataclass  
class Balance:
    """Account balance information"""
    asset: str
    free: Decimal
    locked: Decimal
    
    @property
    def total(self) -> Decimal:
        """Total balance (free + locked)"""
        return self.free + self.locked


@dataclass
class Order:
    """Order information"""
    id: str
    symbol: str
    side: OrderSide
    amount: Decimal
    price: Decimal
    status: OrderStatus
    filled: Decimal = Decimal('0')
    remaining: Decimal = Decimal('0')
    timestamp: float = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
        if self.remaining == Decimal('0'):
            self.remaining = self.amount - self.filled


@dataclass
class Trade:
    """Executed trade information"""
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    amount: Decimal
    price: Decimal
    fee: Decimal
    fee_currency: str
    timestamp: float


class ExchangeError(Exception):
    """Base exception for exchange errors"""
    pass


class ExchangeConnectionError(ExchangeError):
    """Exchange connection related errors"""
    pass


class ExchangeAPIError(ExchangeError):
    """Exchange API related errors"""
    pass


class InsufficientBalanceError(ExchangeError):
    """Insufficient balance error"""
    pass


class BaseExchange(ABC):
    """
    Abstract base class for all exchange implementations
    
    Provides common interface for:
    - Market data (tickers, order books)
    - Account management (balances)
    - Order management (place, cancel, status)
    - WebSocket data feeds
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.name = config.get('name', 'Unknown')
        self.config = config
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.base_url = config.get('base_url')
        self.rate_limit = config.get('rate_limit', 10)
        self.timeout = config.get('timeout', 30)
        
        # Connection state
        self.is_connected = False
        self.last_error = None
        self.request_count = 0
        self.last_request_time = 0
        
        # Rate limiting
        self._rate_limiter = asyncio.Semaphore(self.rate_limit)
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to exchange
        
        Returns:
            bool: True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from exchange"""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """
        Get current ticker for symbol
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Ticker: Current price information
        """
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: int = 10) -> OrderBook:
        """
        Get current order book for symbol
        
        Args:
            symbol: Trading pair symbol
            depth: Number of levels to retrieve
            
        Returns:
            OrderBook: Current order book snapshot
        """
        pass
    
    @abstractmethod
    async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
        """
        Get account balance(s)
        
        Args:
            asset: Specific asset to get balance for (None for all)
            
        Returns:
            Dict[str, Balance]: Asset balances
        """
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: OrderSide, 
                         amount: Decimal, price: Decimal,
                         order_type: str = "limit") -> Order:
        """
        Place a new order
        
        Args:
            symbol: Trading pair symbol
            side: Order side (buy/sell)
            amount: Order amount
            price: Order price
            order_type: Order type (limit/market)
            
        Returns:
            Order: Created order information
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an existing order
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading pair symbol
            
        Returns:
            bool: True if cancellation successful
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """
        Get order status
        
        Args:
            order_id: Order ID to check
            symbol: Trading pair symbol
            
        Returns:
            Order: Current order status
        """
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Get open orders
        
        Args:
            symbol: Filter by symbol (None for all)
            
        Returns:
            List[Order]: List of open orders
        """
        pass
    
    @abstractmethod
    async def get_trading_fees(self, symbol: str) -> Dict[str, Decimal]:
        """
        Get trading fees for symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict with 'maker' and 'taker' fee rates
        """
        pass
    
    # Utility methods
    async def _rate_limit(self):
        """Apply rate limiting"""
        async with self._rate_limiter:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            min_interval = 1.0 / self.rate_limit
            
            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)
            
            self.last_request_time = time.time()
            self.request_count += 1
    
    def _handle_error(self, error: Exception, context: str = ""):
        """Handle and log errors"""
        self.last_error = error
        error_msg = f"{self.name} error in {context}: {str(error)}"
        
        if isinstance(error, (ConnectionError, TimeoutError)):
            self.is_connected = False
            raise ExchangeConnectionError(error_msg)
        elif "insufficient" in str(error).lower():
            raise InsufficientBalanceError(error_msg)
        else:
            raise ExchangeAPIError(error_msg)
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for this exchange
        Override in exchange-specific implementations
        """
        return symbol
    
    def normalize_amount(self, amount: Decimal) -> Decimal:
        """Normalize amount according to exchange precision"""
        # Default implementation - override in specific exchanges
        return amount.quantize(Decimal('0.00000001'))
    
    def normalize_price(self, price: Decimal) -> Decimal:
        """Normalize price according to exchange precision"""
        # Default implementation - override in specific exchanges  
        return price.quantize(Decimal('0.00000001'))
    
    @property
    def status(self) -> Dict[str, Any]:
        """Get exchange status information"""
        return {
            'name': self.name,
            'connected': self.is_connected,
            'request_count': self.request_count,
            'last_error': str(self.last_error) if self.last_error else None,
            'rate_limit': self.rate_limit
        }
    
    def __str__(self):
        return f"{self.name} Exchange ({'Connected' if self.is_connected else 'Disconnected'})"
