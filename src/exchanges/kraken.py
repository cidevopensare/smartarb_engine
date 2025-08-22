“””
Kraken Exchange Connector for SmartArb Engine
Complete implementation for Kraken cryptocurrency exchange
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

class KrakenExchange(BaseExchange):
“””
Kraken exchange implementation using CCXT

```
Kraken specifics:
- Higher fees but excellent security and reputation
- Strong regulatory compliance
- Good for European market access
- Robust API with websocket support
- Uses different symbol naming convention
- Excellent liquidity for major pairs
"""

def __init__(self, config: Dict[str, Any]):
    super().__init__(config)
    
    # Kraken-specific configuration
    self.sandbox = config.get('sandbox', False)
    self.ccxt_client = None
    
    # Kraken symbol mapping (Kraken uses different naming)
    self.symbol_map = {
        'BTC/USDT': 'XXBTZUSDT',
        'ETH/USDT': 'XETHZUSDT', 
        'ADA/USDT': 'ADAUSDT',
        'DOT/USDT': 'DOTUSDT',
        'LINK/USDT': 'LINKUSDT',
        'MATIC/USDT': 'MATICUSDT'
    }
    
    # Reverse mapping for normalization
    self.reverse_symbol_map = {v: k for k, v in self.symbol_map.items()}
    
    # Trading precision settings (will be fetched from exchange)
    self.precision_cache = {}
    self.min_order_sizes = {}
    self.tick_sizes = {}
    
    # Kraken specific settings
    self.api_version = '0'  # Kraken API version
    
async def connect(self) -> bool:
    """Establish connection to Kraken"""
    try:
        # Initialize CCXT client
        self.ccxt_client = ccxt.kraken({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'sandbox': self.sandbox,
            'timeout': self.timeout * 1000,  # CCXT expects milliseconds
            'enableRateLimit': True,
            'rateLimit': 1000 / self.rate_limit,  # Kraken: 15 calls per second
            'options': {
                'adjustForTimeDifference': True,  # Handle time sync issues
            }
        })
        
        # Test connection by fetching server time
        server_time = await self.ccxt_client.fetch_time()
        
        # Load markets to get trading precision info
        await self._load_markets()
        
        # Verify API credentials
        await self._verify_credentials()
        
        self.is_connected = True
        
        logger.info("kraken_connected", 
                   exchange=self.name,
                   sandbox=self.sandbox,
                   api_version=self.api_version,
                   server_time=server_time)
        return True
        
    except Exception as e:
        self.is_connected = False
        logger.error("kraken_connection_failed", 
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
        
        logger.debug("kraken_markets_loaded", 
                    markets_count=len(markets),
                    symbols=list(self.symbol_map.keys()))
        
    except Exception as e:
        logger.warning("kraken_markets_load_failed", error=str(e))

async def _verify_credentials(self) -> None:
    """Verify API credentials by fetching account info"""
    try:
        # Test API credentials with account balance request
        await self.ccxt_client.fetch_balance()
        logger.debug("kraken_credentials_verified")
    except Exception as e:
        logger.error("kraken_credentials_verification_failed", error=str(e))
        raise ExchangeConnectionError(f"Kraken API credentials verification failed: {str(e)}")

async def disconnect(self) -> None:
    """Disconnect from Kraken"""
    if self.ccxt_client:
        await self.ccxt_client.close()
        self.ccxt_client = None
    self.is_connected = False
    logger.info("kraken_disconnected", exchange=self.name)

async def get_ticker(self, symbol: str) -> Ticker:
    """Get current ticker for symbol"""
    await self._rate_limit()
    
    try:
        kraken_symbol = self.normalize_symbol(symbol)
        ticker_data = await self.ccxt_client.fetch_ticker(kraken_symbol)
        
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
        kraken_symbol = self.normalize_symbol(symbol)
        
        # Kraken supports different depth levels, use closest available
        orderbook_data = await self.ccxt_client.fetch_order_book(kraken_symbol, depth)
        
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
            
            # Normalize Kraken currency names
            normalized_currency = self._normalize_currency_name(currency)
            
            # Only include assets with meaningful balances
            free_balance = Decimal(str(data.get('free', 0)))
            locked_balance = Decimal(str(data.get('used', 0)))
            
            if free_balance > 0 or locked_balance > 0:
                balances[normalized_currency] = Balance(
                    asset=normalized_currency,
                    free=free_balance,
                    locked=locked_balance
                )
        
        return balances
        
    except Exception as e:
        self._handle_error(e, f"get_balance({asset})")

def _normalize_currency_name(self, kraken_currency: str) -> str:
    """Normalize Kraken currency names to standard format"""
    currency_map = {
        'XXBT': 'BTC',
        'XETH': 'ETH',
        'ZUSD': 'USD',
        'ZUSDT': 'USDT',
        'ZEUR': 'EUR'
    }
    return currency_map.get(kraken_currency, kraken_currency)

async def place_order(self, symbol: str, side: OrderSide, 
                     amount: Decimal, price: Decimal,
                     order_type: str = "limit") -> Order:
    """Place a new order"""
    await self._rate_limit()
    
    try:
        kraken_symbol = self.normalize_symbol(symbol)
        
        # Normalize amounts according to Kraken precision
        normalized_amount = self.normalize_amount(amount, kraken_symbol)
        normalized_price = self.normalize_price(price, kraken_symbol)
        
        # Validate order size
        min_size = self.min_order_sizes.get(kraken_symbol, Decimal('0'))
        if normalized_amount < min_size:
            raise ExchangeError(f"Order amount {normalized_amount} below minimum {min_size}")
        
        # Validate order value (Kraken has minimum order value requirements)
        order_value = normalized_amount * normalized_price
        min_value = Decimal('10')  # Kraken minimum order value varies by pair
        if order_value < min_value:
            raise ExchangeError(f"Order value {order_value} below minimum {min_value}")
        
        # Place order via CCXT
        order_data = await self.ccxt_client.create_order(
            symbol=kraken_symbol,
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
        
        logger.info("kraken_order_placed",
                   order_id=order.order_id,
                   symbol=symbol,
                   side=side.value,
                   amount=float(normalized_amount),
                   price=float(normalized_price),
                   order_value=float(order_value))
        
        return order
        
    except Exception as e:
        logger.error("kraken_order_placement_failed",
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
        kraken_symbol = self.normalize_symbol(symbol)
        
        await self.ccxt_client.cancel_order(order_id, kraken_symbol)
        
        logger.info("kraken_order_cancelled",
                   order_id=order_id,
                   symbol=symbol)
        return True
        
    except Exception as e:
        logger.error("kraken_order_cancellation_failed",
                    order_id=order_id,
                    symbol=symbol,
                    error=str(e))
        self._handle_error(e, f"cancel_order({order_id})")
        return False

async def get_order_status(self, order_id: str, symbol: str) -> Order:
    """Get current status of an order"""
    await self._rate_limit()
    
    try:
        kraken_symbol = self.normalize_symbol(symbol)
        
        order_data = await self.ccxt_client.fetch_order(order_id, kraken_symbol)
        
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
    """Normalize symbol to Kraken format"""
    return self.symbol_map.get(symbol, symbol)

def denormalize_symbol(self, kraken_symbol: str) -> str:
    """Convert Kraken symbol back to standard format"""
    return self.reverse_symbol_map.get(kraken_symbol, kraken_symbol)

def normalize_amount(self, amount: Decimal, symbol: Optional[str] = None) -> Decimal:
    """Normalize amount to Kraken precision"""
    if symbol and symbol in self.precision_cache:
        precision = self.precision_cache[symbol]['amount']
        return amount.quantize(Decimal('0.' + '0' * (precision - 1) + '1'))
    
    # Default precision if not cached - Kraken typically uses 8 decimal places
    return amount.quantize(Decimal('0.00000001'))

def normalize_price(self, price: Decimal, symbol: Optional[str] = None) -> Decimal:
    """Normalize price to Kraken precision"""
    if symbol and symbol in self.precision_cache:
        precision = self.precision_cache[symbol]['price']
        return price.quantize(Decimal('0.' + '0' * (precision - 1) + '1'))
    
    # Use tick size if available
    if symbol and symbol in self.tick_sizes:
        tick_size = self.tick_sizes[symbol]
        return (price / tick_size).quantize(Decimal('1')) * tick_size
    
    # Default precision if not cached - Kraken uses variable precision
    return price.quantize(Decimal('0.00001'))

async def get_trading_fees(self, symbol: str) -> Dict[str, Decimal]:
    """Get current trading fees for symbol"""
    await self._rate_limit()
    
    try:
        # Kraken has volume-based fee tiers
        trading_fees = await self.ccxt_client.fetch_trading_fees()
        
        kraken_symbol = self.normalize_symbol(symbol)
        if kraken_symbol in trading_fees:
            fees = trading_fees[kraken_symbol]
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
        logger.warning("kraken_fees_fetch_failed", 
                      symbol=symbol, 
                      error=str(e))
        # Return default fees on error
        return {
            'maker': self.maker_fee,
            'taker': self.taker_fee
        }

async def get_account_volume_info(self) -> Dict[str, Any]:
    """Get account volume information for fee tier calculation"""
    await self._rate_limit()
    
    try:
        # Kraken-specific call to get volume and fee info
        account_info = await self.ccxt_client.fetch_account()
        
        volume_info = {
            'volume_30d': Decimal('0'),
            'fee_tier': 0,
            'current_maker_fee': self.maker_fee,
            'current_taker_fee': self.taker_fee
        }
        
        # Extract volume information if available
        info = account_info.get('info', {})
        if 'TradeVolume' in info:
            volume_info['volume_30d'] = Decimal(str(info['TradeVolume']))
        
        return volume_info
        
    except Exception as e:
        logger.warning("kraken_volume_info_failed", error=str(e))
        return {
            'volume_30d': Decimal('0'),
            'fee_tier': 0,
            'current_maker_fee': self.maker_fee,
            'current_taker_fee': self.taker_fee
        }

async def health_check(self) -> bool:
    """Perform health check on Kraken connection"""
    try:
        if not self.is_connected:
            return False
        
        # Test with server time request (lightweight)
        await self.ccxt_client.fetch_time()
        return True
        
    except Exception as e:
        logger.warning("kraken_health_check_failed", error=str(e))
        self.is_connected = False
        return False

async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
    """Get all open orders"""
    await self._rate_limit()
    
    try:
        kraken_symbol = self.normalize_symbol(symbol) if symbol else None
        
        # Fetch open orders
        orders_data = await self.ccxt_client.fetch_open_orders(kraken_symbol)
        
        orders = []
        for order_data in orders_data:
            # Convert symbol back to standard format
            original_symbol = self.denormalize_symbol(order_data['symbol'])
            
            order = Order(
                order_id=str(order_data['id']),
                symbol=original_symbol,
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
        logger.error("kraken_open_orders_fetch_failed", 
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
                    # Add delay to respect rate limits
                    await asyncio.sleep(0.2)
            except Exception as e:
                logger.warning("kraken_order_cancel_failed",
                             order_id=order.order_id,
                             error=str(e))
        
        logger.info("kraken_mass_cancel_completed",
                   symbol=symbol,
                   cancelled=cancelled_count,
                   total=len(open_orders))
        
        return cancelled_count
        
    except Exception as e:
        logger.error("kraken_mass_cancel_failed",
                    symbol=symbol,
                    error=str(e))
        return 0

async def get_order_history(self, symbol: Optional[str] = None, 
                          limit: int = 50) -> List[Order]:
    """Get order history"""
    await self._rate_limit()
    
    try:
        kraken_symbol = self.normalize_symbol(symbol) if symbol else None
        
        # Kraken has a limit of 50 for order history
        orders_data = await self.ccxt_client.fetch_orders(
            symbol=kraken_symbol,
            limit=min(limit, 50)
        )
        
        orders = []
        for order_data in orders_data:
            # Convert symbol back to standard format
            original_symbol = self.denormalize_symbol(order_data['symbol'])
            
            order = Order(
                order_id=str(order_data['id']),
                symbol=original_symbol,
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
        logger.error("kraken_order_history_fetch_failed",
                    symbol=symbol,
                    error=str(e))
        self._handle_error(e, f"get_order_history({symbol})")
        return []

async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent trades for symbol"""
    await self._rate_limit()
    
    try:
        kraken_symbol = self.normalize_symbol(symbol)
        
        trades = await self.ccxt_client.fetch_trades(kraken_symbol, limit=limit)
        
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
        logger.error("kraken_recent_trades_failed",
                    symbol=symbol,
                    error=str(e))
        return []

def get_exchange_info(self) -> Dict[str, Any]:
    """Get detailed exchange information"""
    base_info = super().get_exchange_info()
    
    # Add Kraken-specific information
    kraken_info = {
        'api_version': self.api_version,
        'precision_cache_size': len(self.precision_cache),
        'min_order_sizes_cached': len(self.min_order_sizes),
        'tick_sizes_cached': len(self.tick_sizes),
        'websocket_supported': True,
        'margin_trading': True,  # Available but not implemented
        'spot_trading': True,
        'futures_trading': False,  # Not implemented
        'max_order_history': 50,
        'supports_batch_cancel': False,
        'regulatory_compliance': 'high',
        'geographic_focus': 'global_with_us_restrictions'
    }
    
    return {**base_info, **kraken_info}

async def get_account_info(self) -> Dict[str, Any]:
    """Get detailed account information"""
    await self._rate_limit()
    
    try:
        account_info = await self.ccxt_client.fetch_account()
        
        return {
            'account_type': 'spot',
            'trading_enabled': True,
            'permissions': ['spot', 'margin'],  # Kraken typically has these
            'verification_level': 'unknown',  # Would need specific API call
            'fee_schedule': {
                'maker': float(self.maker_fee),
                'taker': float(self.taker_fee)
            },
            'info': account_info.get('info', {})
        }
        
    except Exception as e:
        logger.error("kraken_account_info_failed", error=str(e))
        return {}

async def get_deposit_address(self, currency: str, network: Optional[str] = None) -> Dict[str, Any]:
    """Get deposit address for currency"""
    await self._rate_limit()
    
    try:
        # Normalize currency name for Kraken
        kraken_currency = currency
        if currency == 'BTC':
            kraken_currency = 'XXBT'
        elif currency == 'ETH':
            kraken_currency = 'XETH'
        
        deposit_info = await self.ccxt_client.fetch_deposit_address(kraken_currency)
        
        return {
            'currency': currency,
            'address': deposit_info.get('address'),
            'tag': deposit_info.get('tag'),
            'network': deposit_info.get('network', network),
            'info': deposit_info.get('info', {})
        }
        
    except Exception as e:
        logger.error("kraken_deposit_address_failed",
                    currency=currency,
                    error=str(e))
        return {}

async def emergency_cancel_all(self) -> bool:
    """Emergency cancel all orders across all symbols"""
    try:
        logger.warning("kraken_emergency_cancel_triggered")
        
        cancelled_count = await self.cancel_all_orders()
        
        logger.info("kraken_emergency_cancel_completed",
                   cancelled_orders=cancelled_count)
        
        return cancelled_count > 0
        
    except Exception as e:
        logger.error("kraken_emergency_cancel_failed", error=str(e))
        return False

async def get_supported_symbols(self) -> List[str]:
    """Get list of supported trading symbols"""
    try:
        if not self.precision_cache:
            await self._load_markets()
        
        # Filter to only symbols we're interested in
        supported = []
        for symbol in self.symbol_map.keys():
            kraken_symbol = self.normalize_symbol(symbol)
            if kraken_symbol in self.precision_cache:
                supported.append(symbol)
        
        return supported
        
    except Exception as e:
        logger.error("kraken_supported_symbols_failed", error=str(e))
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
        kraken_symbol = self.normalize_symbol(symbol)
        
        # Normalize values
        normalized_amount = self.normalize_amount(amount, kraken_symbol)
        normalized_price = self.normalize_price(price, kraken_symbol)
        
        validation_result['normalized_amount'] = normalized_amount
        validation_result['normalized_price'] = normalized_price
        
        # Check minimum order size
        min_size = self.min_order_sizes.get(kraken_symbol, Decimal('0'))
        if normalized_amount < min_size:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Amount {normalized_amount} below minimum {min_size}")
        
        # Check minimum order value
        order_value = normalized_amount * normalized_price
        min_value = Decimal('10')  # Kraken typical minimum
        if order_value < min_value:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Order value {order_value} below minimum {min_value}")
        
        # Check if symbol is supported
        if kraken_symbol not in self.precision_cache:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Symbol {symbol} not supported or not loaded")
        
        # Add warnings for large orders
        if order_value > Decimal('50000'):  # 50k warning for Kraken
            validation_result['warnings'].append("Large order value may require additional verification")
        
    except Exception as e:
        validation_result['valid'] = False
        validation_result['errors'].append(f"Validation error: {str(e)}")
    
    return validation_result

async def get_withdrawal_fees(self) -> Dict[str, Decimal]:
    """Get current withdrawal fees"""
    try:
        # This would typically require a specific API call
        # For now, return default fees from config
        return {
            'BTC': Decimal('0.00015'),
            'ETH': Decimal('0.0025'),
            'USDT': Decimal('5.0'),
            'ADA': Decimal('0.20'),
            'DOT': Decimal('0.05'),
            'LINK': Decimal('0.02'),
            'MATIC': Decimal('1.0')
        }
    except Exception as e:
        logger.error("kraken_withdrawal_fees_failed", error=str(e))
        return {}
```