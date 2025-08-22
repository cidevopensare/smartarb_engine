“””
Bybit Exchange Connector for SmartArb Engine
Complete implementation with advanced features and error handling
“””

import asyncio
import ccxt.async_support as ccxt
from decimal import Decimal
from typing import Dict, List, Optional, Any
import structlog

from .base_exchange import (
BaseExchange, Ticker, OrderBook, OrderBookLevel, Balance,
Order, OrderSide, OrderStatus, ExchangeError, ExchangeConnectionError
)

logger = structlog.get_logger(**name**)

class BybitExchange(BaseExchange):
“””
Bybit exchange implementation using CCXT

```
Bybit specifics:
- Lower fees, good for high-frequency trading
- Strong derivatives platform (future expansion)
- Modern API with excellent WebSocket support
- Global user base with good liquidity
- Unified account system
"""

def __init__(self, config: Dict[str, Any]):
    super().__init__(config)
    
    # Bybit-specific configuration
    self.sandbox = config.get('sandbox', False)
    self.ccxt_client = None
    
    # Bybit uses standard symbol format mostly
    self.symbol_map = {
        'BTC/USDT': 'BTC/USDT',
        'ETH/USDT': 'ETH/USDT',
        'BNB/USDT': 'BNB/USDT',
        'ADA/USDT': 'ADA/USDT',
        'DOT/USDT': 'DOT/USDT',
        'LINK/USDT': 'LINK/USDT',
        'MATIC/USDT': 'MATIC/USDT'
    }
    
    # Bybit has different API endpoints for different markets
    self.market_type = config.get('market_type', 'spot')  # spot, linear, inverse
    
    # Trading precision settings (will be fetched from exchange)
    self.precision_cache = {}
    self.min_order_sizes = {}
    
async def connect(self) -> bool:
    """Establish connection to Bybit"""
    try:
        # Initialize CCXT client for Bybit
        self.ccxt_client = ccxt.bybit({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'sandbox': self.sandbox,
            'timeout': self.timeout * 1000,  # CCXT expects milliseconds
            'enableRateLimit': True,
            'rateLimit': 60000 / self.rate_limit,  # Bybit: 120 requests per minute
            'options': {
                'defaultType': self.market_type,  # spot, swap, future
            }
        })
        
        # Test connection by fetching server time
        server_time = await self.ccxt_client.fetch_time()
        
        # Load markets to get trading precision info
        await self._load_markets()
        
        self.is_connected = True
        
        logger.info("bybit_connected", 
                   exchange=self.name,
                   sandbox=self.sandbox,
                   market_type=self.market_type,
                   server_time=server_time)
        return True
        
    except Exception as e:
        self.is_connected = False
        logger.error("bybit_connection_failed", 
                    exchange=self.name, 
                    error=str(e),
                    sandbox=self.sandbox)
        self._handle_error(e, "connect")
        return False

async def _load_markets(self) -> None:
    """Load market information and trading rules"""
    try:
        markets = await self.ccxt_client.load_markets()
        
        for symbol, market in markets.items():
            # Store precision information
            self.precision_cache[symbol] = {
                'amount': market.get('precision', {}).get('amount', 8),
                'price': market.get('precision', {}).get('price', 8)
            }
            
            # Store minimum order sizes
            self.min_order_sizes[symbol] = market.get('limits', {}).get('amount', {}).get('min', 0)
        
        logger.debug("bybit_markets_loaded", 
                    markets_count=len(markets),
                    symbols=list(self.symbol_map.keys()))
        
    except Exception as e:
        logger.warning("bybit_markets_load_failed", error=str(e))

async def disconnect(self) -> None:
    """Disconnect from Bybit"""
    if self.ccxt_client:
        await self.ccxt_client.close()
        self.ccxt_client = None
    self.is_connected = False
    logger.info("bybit_disconnected", exchange=self.name)

async def get_ticker(self, symbol: str) -> Ticker:
    """Get current ticker for symbol"""
    await self._rate_limit()
    
    try:
        bybit_symbol = self.normalize_symbol(symbol)
        ticker_data = await self.ccxt_client.fetch_ticker(bybit_symbol)
        
        return Ticker(
            symbol=symbol,
            bid=Decimal(str(ticker_data['bid'] or 0)),
            ask=Decimal(str(ticker_data['ask'] or 0)),
            last=Decimal(str(ticker_data['last'] or 0)),
            volume=Decimal(str(ticker_data['baseVolume'] or 0)),
            timestamp=ticker_data['timestamp'] / 1000 if ticker_data['timestamp'] else 0
        )
        
    except Exception as e:
        self._handle_error(e, f"get_ticker({symbol})")

async def get_orderbook(self, symbol: str, depth: int = 10) -> OrderBook:
    """Get current order book for symbol"""
    await self._rate_limit()
    
    try:
        bybit_symbol = self.normalize_symbol(symbol)
        orderbook_data = await self.ccxt_client.fetch_order_book(bybit_symbol, depth)
        
        # Convert to our format
        bids = [
            OrderBookLevel(Decimal(str(level[0])), Decimal(str(level[1])))
            for level in orderbook_data['bids'][:depth]
        ]
        asks = [
            OrderBookLevel(Decimal(str(level[0])), Decimal(str(level[1])))
            for level in orderbook_data['asks'][:depth]
        ]
        
        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=orderbook_data['timestamp'] / 1000 if orderbook_data['timestamp'] else 0
        )
        
    except Exception as e:
        self._handle_error(e, f"get_orderbook({symbol})")

async def get_balance(self, asset: Optional[str] = None) -> Dict[str, Balance]:
    """Get account balance(s)"""
    await self._rate_limit()
    
    try:
        balance_data = await self.ccxt_client.fetch_balance()
        balances = {}
        
        for currency, data in balance_data.items():
            if currency in ['free', 'used', 'total', 'info']:
                continue
            
            if asset and currency != asset:
                continue
            
            # Only include assets with meaningful balances
            free_balance = Decimal(str(data.get('free', 0)))
            locked_balance = Decimal(str(data.get('used', 0)))
            
            if free_balance > 0 or locked_balance > 0:
                balances[currency] = Balance(
                    asset=currency,
                    free=free_balance,
                    locked=locked_balance
                )
        
        return balances
        
    except Exception as e:
        self._handle_error(e, f"get_balance({asset})")

async def place_order(self, symbol: str, side: OrderSide, 
                     amount: Decimal, price: Decimal,
                     order_type: str = "limit") -> Order:
    """Place a new order"""
    await self._rate_limit()
    
    try:
        bybit_symbol = self.normalize_symbol(symbol)
        
        # Normalize amounts according to Bybit precision
        normalized_amount = self.normalize_amount(amount, bybit_symbol)
        normalized_price = self.normalize_price(price, bybit_symbol)
        
        # Validate order size
        min_size = self.min_order_sizes.get(bybit_symbol, 0)
        if normalized_amount < Decimal(str(min_size)):
            raise ExchangeError(f"Order amount {normalized_amount} below minimum {min_size}")
        
        # Place order via CCXT
        order_data = await self.ccxt_client.create_order(
            symbol=bybit_symbol,
            type=order_type,
            side=side.value,
            amount=float(normalized_amount),
            price=float(normalized_price) if order_type == 'limit' else None
        )
        
        # Convert to our Order format
        order = Order(
            order_id=str(order_data['id']),
            symbol=symbol,
            side=side,
            amount=normalized_amount,
            price=normalized_price,
            status=self._parse_order_status(order_data['status']),
            filled_amount=Decimal(str(order_data.get('filled', 0))),
            average_price=Decimal(str(order_data.get('average', 0) or 0)),
            fees=Decimal(str(order_data.get('fee', {}).get('cost', 0))),
            timestamp=order_data.get('timestamp', 0) / 1000 if order_data.get('timestamp') else 0
        )
        
        logger.info("bybit_order_placed",
                   order_id=order.order_id,
                   symbol=symbol,
                   side=side.value,
                   amount=float(normalized_amount),
                   price=float(normalized_price))
        
        return order
        
    except Exception as e:
        logger.error("bybit_order_placement_failed",
                    symbol=symbol,
                    side=side.value,
                    amount=float(amount),
                    price=float(price),
                    error=str(e))
        self._handle_error(e, f"place_order({symbol}, {side.value})")

async def cancel_order(self, order_id: str, symbol: str) -> bool:
    """Cancel an existing order"""
    await self._rate_limit()
    
    try:
        bybit_symbol = self.normalize_symbol(symbol)
        
        await self.ccxt_client.cancel_order(order_id, bybit_symbol)
        
        logger.info("bybit_order_cancelled",
                   order_id=order_id,
                   symbol=symbol)
        return True
        
    except Exception as e:
        logger.error("bybit_order_cancellation_failed",
                    order_id=order_id,
                    symbol=symbol,
                    error=str(e))
        self._handle_error(e, f"cancel_order({order_id})")
        return False

async def get_order_status(self, order_id: str, symbol: str) -> Order:
    """Get current status of an order"""
    await self._rate_limit()
    
    try:
        bybit_symbol = self.normalize_symbol(symbol)
        
        order_data = await self.ccxt_client.fetch_order(order_id, bybit_symbol)
        
        order = Order(
            order_id=str(order_data['id']),
            symbol=symbol,
            side=OrderSide.BUY if order_data['side'] == 'buy' else OrderSide.SELL,
            amount=Decimal(str(order_data['amount'])),
            price=Decimal(str(order_data.get('price', 0) or 0)),
            status=self._parse_order_status(order_data['status']),
            filled_amount=Decimal(str(order_data.get('filled', 0))),
            average_price=Decimal(str(order_data.get('average', 0) or 0)),
            fees=Decimal(str(order_data.get('fee', {}).get('cost', 0))),
            timestamp=order_data.get('timestamp', 0) / 1000 if order_data.get('timestamp') else 0
        )
        
        return order
        
    except Exception as e:
        self._handle_error(e, f"get_order_status({order_id})")

def _parse_order_status(self, ccxt_status: str) -> OrderStatus:
    """Convert CCXT order status to our OrderStatus enum"""
    status_mapping = {
        'open': OrderStatus.OPEN,
        'closed': OrderStatus.FILLED,
        'canceled': OrderStatus.CANCELED,
        'cancelled': OrderStatus.CANCELED,
        'rejected': OrderStatus.REJECTED,
        'expired': OrderStatus.CANCELED,
        'partial': OrderStatus.PARTIALLY_FILLED,
        'partially_filled': OrderStatus.PARTIALLY_FILLED
    }
    
    return status_mapping.get(ccxt_status.lower(), OrderStatus.OPEN)

def normalize_symbol(self, symbol: str) -> str:
    """Normalize symbol to Bybit format"""
    return self.symbol_map.get(symbol, symbol)

def normalize_amount(self, amount: Decimal, symbol: Optional[str] = None) -> Decimal:
    """Normalize amount to Bybit precision"""
    if symbol and symbol in self.precision_cache:
        precision = self.precision_cache[symbol]['amount']
        return amount.quantize(Decimal('0.' + '0' * (precision - 1) + '1'))
    
    # Default precision if not cached
    return amount.quantize(Decimal('0.00000001'))

def normalize_price(self, price: Decimal, symbol: Optional[str] = None) -> Decimal:
    """Normalize price to Bybit precision"""
    if symbol and symbol in self.precision_cache:
        precision = self.precision_cache[symbol]['price']
        return price.quantize(Decimal('0.' + '0' * (precision - 1) + '1'))
    
    # Default precision if not cached
    return price.quantize(Decimal('0.00000001'))

async def get_trading_fees(self, symbol: str) -> Dict[str, Decimal]:
    """Get current trading fees for symbol"""
    await self._rate_limit()
    
    try:
        # Bybit has tiered fee structure, get current user's fees
        trading_fees = await self.ccxt_client.fetch_trading_fees()
        
        if symbol in trading_fees:
            fees = trading_fees[symbol]
            return {
                'maker': Decimal(str(fees.get('maker', self.maker_fee))),
                'taker': Decimal(str(fees.get('taker', self.taker_fee)))
            }
        else:
            # Return default fees
            return {
                'maker': self.maker_fee,
                'taker': self.taker_fee
            }
            
    except Exception as e:
        logger.warning("bybit_fees_fetch_failed", 
                      symbol=symbol, 
                      error=str(e))
        # Return default fees on error
        return {
            'maker': self.maker_fee,
            'taker': self.taker_fee
        }

async def get_24h_volume(self, symbol: str) -> Decimal:
    """Get 24h trading volume for symbol"""
    try:
        ticker = await self.get_ticker(symbol)
        return ticker.volume
    except Exception as e:
        logger.warning("bybit_volume_fetch_failed", 
                      symbol=symbol, 
                      error=str(e))
        return Decimal('0')

async def health_check(self) -> bool:
    """Perform health check on Bybit connection"""
    try:
        if not self.is_connected:
            return False
        
        # Test with server time request (lightweight)
        await self.ccxt_client.fetch_time()
        return True
        
    except Exception as e:
        logger.warning("bybit_health_check_failed", error=str(e))
        self.is_connected = False
        return False

async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
    """Get all open orders"""
    await self._rate_limit()
    
    try:
        bybit_symbol = self.normalize_symbol(symbol) if symbol else None
        
        # Fetch open orders
        orders_data = await self.ccxt_client.fetch_open_orders(bybit_symbol)
        
        orders = []
        for order_data in orders_data:
            order = Order(
                order_id=str(order_data['id']),
                symbol=order_data['symbol'],
                side=OrderSide.BUY if order_data['side'] == 'buy' else OrderSide.SELL,
                amount=Decimal(str(order_data['amount'])),
                price=Decimal(str(order_data.get('price', 0) or 0)),
                status=self._parse_order_status(order_data['status']),
                filled_amount=Decimal(str(order_data.get('filled', 0))),
                average_price=Decimal(str(order_data.get('average', 0) or 0)),
                fees=Decimal(str(order_data.get('fee', {}).get('cost', 0))),
                timestamp=order_data.get('timestamp', 0) / 1000 if order_data.get('timestamp') else 0
            )
            orders.append(order)
        
        return orders
        
    except Exception as e:
        logger.error("bybit_open_orders_fetch_failed", 
                    symbol=symbol,
                    error=str(e))
        self._handle_error(e, f"get_open_orders({symbol})")
        return []

async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
    """Cancel all open orders for symbol (or all symbols if None)"""
    try:
        open_orders = await self.get_open_orders(symbol)
        
        cancelled_count = 0
        for order in open_orders:
            try:
                if await self.cancel_order(order.order_id, order.symbol):
                    cancelled_count += 1
            except Exception as e:
                logger.warning("bybit_order_cancel_failed",
                             order_id=order.order_id,
                             error=str(e))
        
        logger.info("bybit_mass_cancel_completed",
                   symbol=symbol,
                   cancelled=cancelled_count,
                   total=len(open_orders))
        
        return cancelled_count
        
    except Exception as e:
        logger.error("bybit_mass_cancel_failed",
                    symbol=symbol,
                    error=str(e))
        return 0

async def get_order_history(self, symbol: Optional[str] = None, 
                          limit: int = 100) -> List[Order]:
    """Get order history"""
    await self._rate_limit()
    
    try:
        bybit_symbol = self.normalize_symbol(symbol) if symbol else None
        
        orders_data = await self.ccxt_client.fetch_orders(
            symbol=bybit_symbol,
            limit=limit
        )
        
        orders = []
        for order_data in orders_data:
            order = Order(
                order_id=str(order_data['id']),
                symbol=order_data['symbol'],
                side=OrderSide.BUY if order_data['side'] == 'buy' else OrderSide.SELL,
                amount=Decimal(str(order_data['amount'])),
                price=Decimal(str(order_data.get('price', 0) or 0)),
                status=self._parse_order_status(order_data['status']),
                filled_amount=Decimal(str(order_data.get('filled', 0))),
                average_price=Decimal(str(order_data.get('average', 0) or 0)),
                fees=Decimal(str(order_data.get('fee', {}).get('cost', 0))),
                timestamp=order_data.get('timestamp', 0) / 1000 if order_data.get('timestamp') else 0
            )
            orders.append(order)
        
        return orders
        
    except Exception as e:
        logger.error("bybit_order_history_fetch_failed",
                    symbol=symbol,
                    error=str(e))
        self._handle_error(e, f"get_order_history({symbol})")
        return []

def get_exchange_info(self) -> Dict[str, Any]:
    """Get detailed exchange information"""
    base_info = super().get_exchange_info()
    
    # Add Bybit-specific information
    bybit_info = {
        'market_type': self.market_type,
        'precision_cache_size': len(self.precision_cache),
        'min_order_sizes_cached': len(self.min_order_sizes),
        'api_version': 'V5',  # Bybit V5 API
        'websocket_supported': True,
        'margin_trading': self.market_type in ['linear', 'inverse'],
        'spot_trading': self.market_type == 'spot'
    }
    
    return {**base_info, **bybit_info}

async def get_account_info(self) -> Dict[str, Any]:
    """Get detailed account information"""
    await self._rate_limit()
    
    try:
        account_info = await self.ccxt_client.fetch_account()
        
        return {
            'account_type': account_info.get('type', 'spot'),
            'permissions': account_info.get('permissions', []),
            'trading_enabled': account_info.get('canTrade', True),
            'withdrawal_enabled': account_info.get('canWithdraw', True),
            'deposit_enabled': account_info.get('canDeposit', True),
            'info': account_info.get('info', {})
        }
        
    except Exception as e:
        logger.error("bybit_account_info_failed", error=str(e))
        return {}

async def emergency_cancel_all(self) -> bool:
    """Emergency cancel all orders across all symbols"""
    try:
        logger.warning("bybit_emergency_cancel_triggered")
        
        cancelled_count = await self.cancel_all_orders()
        
        logger.info("bybit_emergency_cancel_completed",
                   cancelled_orders=cancelled_count)
        
        return cancelled_count > 0
        
    except Exception as e:
        logger.error("bybit_emergency_cancel_failed", error=str(e))
        return False
```