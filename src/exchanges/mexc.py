“””
MEXC Exchange Connector for SmartArb Engine
Complete implementation for MEXC Global cryptocurrency exchange
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

class MEXCExchange(BaseExchange):
“””
MEXC Global exchange implementation using CCXT

```
MEXC specifics:
- Large selection of altcoins and new tokens
- Competitive fees and frequent promotions
- Good for finding arbitrage opportunities with less common pairs
- Strong presence in Asian markets
- Modern API with good documentation
"""

def __init__(self, config: Dict[str, Any]):
    super().__init__(config)
    
    # MEXC-specific configuration
    self.sandbox = config.get('sandbox', False)
    self.ccxt_client = None
    
    # MEXC uses standard symbol format
    self.symbol_map = {
        'BTC/USDT': 'BTC/USDT',
        'ETH/USDT': 'ETH/USDT',
        'BNB/USDT': 'BNB/USDT',
        'ADA/USDT': 'ADA/USDT',
        'DOT/USDT': 'DOT/USDT',
        'LINK/USDT': 'LINK/USDT',
        'MATIC/USDT': 'MATIC/USDT'
    }
    
    # Trading precision settings (will be fetched from exchange)
    self.precision_cache = {}
    self.min_order_sizes = {}
    self.tick_sizes = {}
    
    # MEXC specific settings
    self.api_version = 'v3'  # MEXC API version
    
async def connect(self) -> bool:
    """Establish connection to MEXC"""
    try:
        # Initialize CCXT client for MEXC
        self.ccxt_client = ccxt.mexc({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'sandbox': self.sandbox,
            'timeout': self.timeout * 1000,  # CCXT expects milliseconds
            'enableRateLimit': True,
            'rateLimit': 1000 / self.rate_limit,  # MEXC: 20 requests per second
            'options': {
                'defaultType': 'spot',
            }
        })
        
        # Test connection by fetching server time
        server_time = await self.ccxt_client.fetch_time()
        
        # Load markets to get trading precision info
        await self._load_markets()
        
        # Verify API credentials
        await self._verify_credentials()
        
        self.is_connected = True
        
        logger.info("mexc_connected", 
                   exchange=self.name,
                   sandbox=self.sandbox,
                   api_version=self.api_version,
                   server_time=server_time)
        return True
        
    except Exception as e:
        self.is_connected = False
        logger.error("mexc_connection_failed", 
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
            precision = market.get('precision', {})
            self.precision_cache[symbol] = {
                'amount': precision.get('amount', 8),
                'price': precision.get('price', 8)
            }
            
            # Store minimum order sizes
            limits = market.get('limits', {})
            amount_limits = limits.get('amount', {})
            self.min_order_sizes[symbol] = Decimal(str(amount_limits.get('min', 0)))
            
            # Store tick sizes for price precision
            price_limits = limits.get('price', {})
            if 'min' in price_limits:
                self.tick_sizes[symbol] = Decimal(str(price_limits['min']))
        
        logger.debug("mexc_markets_loaded", 
                    markets_count=len(markets),
                    symbols=list(self.symbol_map.keys()))
        
    except Exception as e:
        logger.warning("mexc_markets_load_failed", error=str(e))

async def _verify_credentials(self) -> None:
    """Verify API credentials by fetching account info"""
    try:
        # Test API credentials with a simple account request
        await self.ccxt_client.fetch_balance()
        logger.debug("mexc_credentials_verified")
    except Exception as e:
        logger.error("mexc_credentials_verification_failed", error=str(e))
        raise ExchangeConnectionError(f"MEXC API credentials verification failed: {str(e)}")

async def disconnect(self) -> None:
    """Disconnect from MEXC"""
    if self.ccxt_client:
        await self.ccxt_client.close()
        self.ccxt_client = None
    self.is_connected = False
    logger.info("mexc_disconnected", exchange=self.name)

async def get_ticker(self, symbol: str) -> Ticker:
    """Get current ticker for symbol"""
    await self._rate_limit()
    
    try:
        mexc_symbol = self.normalize_symbol(symbol)
        ticker_data = await self.ccxt_client.fetch_ticker(mexc_symbol)
        
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
        mexc_symbol = self.normalize_symbol(symbol)
        
        # MEXC supports different depth levels: 5, 10, 20, 50, 100, 500, 1000
        # Choose the closest supported depth
        supported_depths = [5, 10, 20, 50, 100, 500, 1000]
        actual_depth = min(supported_depths, key=lambda x: abs(x - depth))
        
        orderbook_data = await self.ccxt_client.fetch_order_book(mexc_symbol, actual_depth)
        
        # Convert to our format, limiting to requested depth
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
        mexc_symbol = self.normalize_symbol(symbol)
        
        # Normalize amounts according to MEXC precision
        normalized_amount = self.normalize_amount(amount, mexc_symbol)
        normalized_price = self.normalize_price(price, mexc_symbol)
        
        # Validate order size
        min_size = self.min_order_sizes.get(mexc_symbol, Decimal('0'))
        if normalized_amount < min_size:
            raise ExchangeError(f"Order amount {normalized_amount} below minimum {min_size}")
        
        # Validate order value (MEXC has minimum order value requirements)
        order_value = normalized_amount * normalized_price
        min_value = Decimal('10')  # MEXC minimum order value is typically 10 USDT
        if order_value < min_value:
            raise ExchangeError(f"Order value {order_value} USDT below minimum {min_value} USDT")
        
        # Place order via CCXT
        order_data = await self.ccxt_client.create_order(
            symbol=mexc_symbol,
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
        
        logger.info("mexc_order_placed",
                   order_id=order.order_id,
                   symbol=symbol,
                   side=side.value,
                   amount=float(normalized_amount),
                   price=float(normalized_price),
                   order_value=float(order_value))
        
        return order
        
    except Exception as e:
        logger.error("mexc_order_placement_failed",
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
        mexc_symbol = self.normalize_symbol(symbol)
        
        await self.ccxt_client.cancel_order(order_id, mexc_symbol)
        
        logger.info("mexc_order_cancelled",
                   order_id=order_id,
                   symbol=symbol)
        return True
        
    except Exception as e:
        logger.error("mexc_order_cancellation_failed",
                    order_id=order_id,
                    symbol=symbol,
                    error=str(e))
        self._handle_error(e, f"cancel_order({order_id})")
        return False

async def get_order_status(self, order_id: str, symbol: str) -> Order:
    """Get current status of an order"""
    await self._rate_limit()
    
    try:
        mexc_symbol = self.normalize_symbol(symbol)
        
        order_data = await self.ccxt_client.fetch_order(order_id, mexc_symbol)
        
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
        'partially_filled': OrderStatus.PARTIALLY_FILLED,
        'filled': OrderStatus.FILLED
    }
    
    return status_mapping.get(ccxt_status.lower(), OrderStatus.OPEN)

def normalize_symbol(self, symbol: str) -> str:
    """Normalize symbol to MEXC format"""
    return self.symbol_map.get(symbol, symbol)

def normalize_amount(self, amount: Decimal, symbol: Optional[str] = None) -> Decimal:
    """Normalize amount to MEXC precision"""
    if symbol and symbol in self.precision_cache:
        precision = self.precision_cache[symbol]['amount']
        return amount.quantize(Decimal('0.' + '0' * (precision - 1) + '1'))
    
    # Default precision if not cached
    return amount.quantize(Decimal('0.00000001'))

def normalize_price(self, price: Decimal, symbol: Optional[str] = None) -> Decimal:
    """Normalize price to MEXC precision"""
    if symbol and symbol in self.precision_cache:
        precision = self.precision_cache[symbol]['price']
        return price.quantize(Decimal('0.' + '0' * (precision - 1) + '1'))
    
    # Use tick size if available
    if symbol and symbol in self.tick_sizes:
        tick_size = self.tick_sizes[symbol]
        return (price / tick_size).quantize(Decimal('1')) * tick_size
    
    # Default precision if not cached
    return price.quantize(Decimal('0.00000001'))

async def get_trading_fees(self, symbol: str) -> Dict[str, Decimal]:
    """Get current trading fees for symbol"""
    await self._rate_limit()
    
    try:
        # MEXC has VIP level based fees, get current user's fees
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
        logger.warning("mexc_fees_fetch_failed", 
                      symbol=symbol, 
                      error=str(e))
        # Return default fees on error
        return {
            'maker': self.maker_fee,
            'taker': self.taker_fee
        }

async def get_24h_stats(self, symbol: str) -> Dict[str, Any]:
    """Get 24h trading statistics for symbol"""
    try:
        ticker = await self.get_ticker(symbol)
        
        return {
            'volume': ticker.volume,
            'last_price': ticker.last,
            'price_change_24h': Decimal('0'),  # Would need historical data
            'high_24h': Decimal('0'),  # Would need ticker with high/low
            'low_24h': Decimal('0'),
            'bid': ticker.bid,
            'ask': ticker.ask,
            'spread': ticker.spread,
            'spread_percent': ticker.spread_percent
        }
        
    except Exception as e:
        logger.warning("mexc_24h_stats_failed", 
                      symbol=symbol, 
                      error=str(e))
        return {}

async def health_check(self) -> bool:
    """Perform health check on MEXC connection"""
    try:
        if not self.is_connected:
            return False
        
        # Test with server time request (lightweight)
        await self.ccxt_client.fetch_time()
        return True
        
    except Exception as e:
        logger.warning("mexc_health_check_failed", error=str(e))
        self.is_connected = False
        return False

async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
    """Get all open orders"""
    await self._rate_limit()
    
    try:
        mexc_symbol = self.normalize_symbol(symbol) if symbol else None
        
        # Fetch open orders
        orders_data = await self.ccxt_client.fetch_open_orders(mexc_symbol)
        
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
        logger.error("mexc_open_orders_fetch_failed", 
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
                    # Add small delay to avoid rate limits
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning("mexc_order_cancel_failed",
                             order_id=order.order_id,
                             error=str(e))
        
        logger.info("mexc_mass_cancel_completed",
                   symbol=symbol,
                   cancelled=cancelled_count,
                   total=len(open_orders))
        
        return cancelled_count
        
    except Exception as e:
        logger.error("mexc_mass_cancel_failed",
                    symbol=symbol,
                    error=str(e))
        return 0

async def get_order_history(self, symbol: Optional[str] = None, 
                          limit: int = 100) -> List[Order]:
    """Get order history"""
    await self._rate_limit()
    
    try:
        mexc_symbol = self.normalize_symbol(symbol) if symbol else None
        
        orders_data = await self.ccxt_client.fetch_orders(
            symbol=mexc_symbol,
            limit=min(limit, 1000)  # MEXC limit
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
        logger.error("mexc_order_history_fetch_failed",
                    symbol=symbol,
                    error=str(e))
        self._handle_error(e, f"get_order_history({symbol})")
        return []

async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent trades for symbol"""
    await self._rate_limit()
    
    try:
        mexc_symbol = self.normalize_symbol(symbol)
        
        trades = await self.ccxt_client.fetch_trades(mexc_symbol, limit=limit)
        
        formatted_trades = []
        for trade in trades:
            formatted_trades.append({
                'id': trade.get('id'),
                'price': Decimal(str(trade.get('price', 0))),
                'amount': Decimal(str(trade.get('amount', 0))),
                'side': trade.get('side'),
                'timestamp': trade.get('timestamp', 0) / 1000 if trade.get('timestamp') else 0
            })
        
        return formatted_trades
        
    except Exception as e:
        logger.error("mexc_recent_trades_failed",
                    symbol=symbol,
                    error=str(e))
        return []

def get_exchange_info(self) -> Dict[str, Any]:
    """Get detailed exchange information"""
    base_info = super().get_exchange_info()
    
    # Add MEXC-specific information
    mexc_info = {
        'api_version': self.api_version,
        'precision_cache_size': len(self.precision_cache),
        'min_order_sizes_cached': len(self.min_order_sizes),
        'tick_sizes_cached': len(self.tick_sizes),
        'websocket_supported': True,
        'margin_trading': False,  # Focus on spot trading
        'spot_trading': True,
        'futures_trading': False,  # Available but not implemented
        'max_order_history': 1000,
        'supports_batch_cancel': False
    }
    
    return {**base_info, **mexc_info}

async def get_account_info(self) -> Dict[str, Any]:
    """Get detailed account information"""
    await self._rate_limit()
    
    try:
        account_info = await self.ccxt_client.fetch_account()
        
        return {
            'account_type': 'spot',
            'trading_enabled': True,
            'permissions': ['spot'],  # MEXC typically has spot permissions
            'commission_rates': {
                'maker': float(self.maker_fee),
                'taker': float(self.taker_fee)
            },
            'info': account_info.get('info', {})
        }
        
    except Exception as e:
        logger.error("mexc_account_info_failed", error=str(e))
        return {}

async def get_deposit_address(self, currency: str, network: Optional[str] = None) -> Dict[str, Any]:
    """Get deposit address for currency"""
    await self._rate_limit()
    
    try:
        deposit_info = await self.ccxt_client.fetch_deposit_address(currency)
        
        return {
            'currency': currency,
            'address': deposit_info.get('address'),
            'tag': deposit_info.get('tag'),
            'network': deposit_info.get('network', network),
            'info': deposit_info.get('info', {})
        }
        
    except Exception as e:
        logger.error("mexc_deposit_address_failed",
                    currency=currency,
                    error=str(e))
        return {}

async def emergency_cancel_all(self) -> bool:
    """Emergency cancel all orders across all symbols"""
    try:
        logger.warning("mexc_emergency_cancel_triggered")
        
        cancelled_count = await self.cancel_all_orders()
        
        logger.info("mexc_emergency_cancel_completed",
                   cancelled_orders=cancelled_count)
        
        return cancelled_count > 0
        
    except Exception as e:
        logger.error("mexc_emergency_cancel_failed", error=str(e))
        return False

async def get_supported_symbols(self) -> List[str]:
    """Get list of supported trading symbols"""
    try:
        if not self.precision_cache:
            await self._load_markets()
        
        # Filter to only symbols we're interested in
        supported = []
        for symbol in self.symbol_map.keys():
            mexc_symbol = self.normalize_symbol(symbol)
            if mexc_symbol in self.precision_cache:
                supported.append(symbol)
        
        return supported
        
    except Exception as e:
        logger.error("mexc_supported_symbols_failed", error=str(e))
        return list(self.symbol_map.keys())  # Return default list

async def validate_order(self, symbol: str, side: OrderSide, 
                       amount: Decimal, price: Decimal) -> Dict[str, Any]:
    """Validate order parameters before placing"""
    validation_result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'normalized_amount': amount,
        'normalized_price': price
    }
    
    try:
        mexc_symbol = self.normalize_symbol(symbol)
        
        # Normalize values
        normalized_amount = self.normalize_amount(amount, mexc_symbol)
        normalized_price = self.normalize_price(price, mexc_symbol)
        
        validation_result['normalized_amount'] = normalized_amount
        validation_result['normalized_price'] = normalized_price
        
        # Check minimum order size
        min_size = self.min_order_sizes.get(mexc_symbol, Decimal('0'))
        if normalized_amount < min_size:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Amount {normalized_amount} below minimum {min_size}")
        
        # Check minimum order value
        order_value = normalized_amount * normalized_price
        min_value = Decimal('10')
        if order_value < min_value:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Order value {order_value} USDT below minimum {min_value} USDT")
        
        # Check if symbol is supported
        if mexc_symbol not in self.precision_cache:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Symbol {symbol} not supported or not loaded")
        
        # Add warnings for large orders
        if order_value > Decimal('100000'):  # 100k USDT
            validation_result['warnings'].append("Large order value may impact market price")
        
    except Exception as e:
        validation_result['valid'] = False
        validation_result['errors'].append(f"Validation error: {str(e)}")
    
    return validation_result
```