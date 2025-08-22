"""
Bybit Exchange Connector for SmartArb Engine
Implements Bybit-specific API integration
"""

import asyncio
import ccxt.async_support as ccxt
from decimal import Decimal
from typing import Dict, List, Optional, Any
import structlog

from .base_exchange import (
    BaseExchange, Ticker, OrderBook, OrderBookLevel, Balance, 
    Order, OrderSide, OrderStatus, ExchangeError, ExchangeConnectionError
)

logger = structlog.get_logger(__name__)


class BybitExchange(BaseExchange):
    """
    Bybit exchange implementation using CCXT
    
    Bybit specifics:
    - Lower fees, good for high-frequency trading
    - Strong derivatives platform (future expansion)
    - Modern API with excellent WebSocket support
    - Global user base with good liquidity
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
            await self.ccxt_client.fetch_time()
            self.is_connected = True
            
            logger.info("bybit_connected", exchange=self.name, market_type=self.market_type)
            return True
            
        except Exception as e:
            self.is_connected = False
            self._handle_error(e, "connect")
            return False
    
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
                for level in orderbook_data['bids']
            ]
            asks = [
                OrderBookLevel(Decimal(str(level[0])), Decimal(str(level[1])))
                for level in orderbook_data['asks']
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
                    
                balances[currency] = Balance(
                    asset=currency,
                    free=Decimal(str(data.get('free', 0))),
                    locked=Decimal(str(data.get('used', 0)))
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
            normalized_amount = self.normalize_amount(amount)
            normalized_price = self.normalize_price(price)
            
            # Place order via CCXT
            order_data = await self.ccxt_client.create_order(
                symbol=bybit_symbol,
                type=order_type,
                side=side.value,
                amount=float(normalized_amount),
                price=float(normalized_price) if order_type == 'limit' else None,
                params={'timeInForce': 'GTC'}  # Good Till Cancelled
            )
            
            return Order(
                id=order_data['id'],
                symbol=symbol,
                side=side,
                amount=normalized_amount,
                price=normalized_price,
                status=self._convert_order_status(order_data['status']),
                filled=Decimal(str(order_data.get('filled', 0))),
                timestamp=order_data['timestamp'] / 1000 if order_data['timestamp'] else 0
            )
            
        except Exception as e:
            self._handle_error(e, f"place_order({symbol}, {side}, {amount}, {price})")
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order"""
        await self._rate_limit()
        
        try:
            bybit_symbol = self.normalize_symbol(symbol)
            await self.ccxt_client.cancel_order(order_id, bybit_symbol)
            return True
            
        except Exception as e:
            logger.warning("cancel_order_failed", 
                         order_id=order_id, symbol=symbol, error=str(e))
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Get order status"""
        await self._rate_limit()
        
        try:
            bybit_symbol = self.normalize_symbol(symbol)
            order_data = await self.ccxt_client.fetch_order(order_id, bybit_symbol)
            
            return Order(
                id=order_data['id'],
                symbol=symbol,
                side=OrderSide(order_data['side']),
                amount=Decimal(str(order_data['amount'])),
                price=Decimal(str(order_data['price'] or 0)),
                status=self._convert_order_status(order_data['status']),
                filled=Decimal(str(order_data.get('filled', 0))),
                timestamp=order_data['timestamp'] / 1000 if order_data['timestamp'] else 0
            )
            
        except Exception as e:
            self._handle_error(e, f"get_order_status({order_id}, {symbol})")
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders"""
        await self._rate_limit()
        
        try:
            bybit_symbol = self.normalize_symbol(symbol) if symbol else None
            orders_data = await self.ccxt_client.fetch_open_orders(bybit_symbol)
            
            orders = []
            for order_data in orders_data:
                orders.append(Order(
                    id=order_data['id'],
                    symbol=order_data['symbol'],  # Bybit uses standard format
                    side=OrderSide(order_data['side']),
                    amount=Decimal(str(order_data['amount'])),
                    price=Decimal(str(order_data['price'] or 0)),
                    status=self._convert_order_status(order_data['status']),
                    filled=Decimal(str(order_data.get('filled', 0))),
                    timestamp=order_data['timestamp'] / 1000 if order_data['timestamp'] else 0
                ))
            
            return orders
            
        except Exception as e:
            self._handle_error(e, f"get_open_orders({symbol})")
    
    async def get_trading_fees(self, symbol: str) -> Dict[str, Decimal]:
        """Get trading fees for symbol"""
        try:
            # Bybit has competitive fees
            # These are standard rates - in production, fetch user-specific fees
            return {
                'maker': Decimal(str(self.config.get('maker_fee', 0.001))),  # 0.1%
                'taker': Decimal(str(self.config.get('taker_fee', 0.001)))   # 0.1%
            }
        except Exception as e:
            # Fallback to config values
            return {
                'maker': Decimal('0.001'),
                'taker': Decimal('0.001')
            }
    
    def normalize_symbol(self, symbol: str) -> str:
        """Convert standard symbol to Bybit format"""
        return self.symbol_map.get(symbol, symbol)
    
    def normalize_amount(self, amount: Decimal) -> Decimal:
        """Normalize amount for Bybit (6 decimal places typically)"""
        return amount.quantize(Decimal('0.000001'))
    
    def normalize_price(self, price: Decimal) -> Decimal:
        """Normalize price for Bybit (2-4 decimal places depending on pair)"""
        # For major pairs like BTC/USDT, typically 2 decimal places
        # For smaller pairs, might need more precision
        return price.quantize(Decimal('0.01'))
    
    def _convert_order_status(self, ccxt_status: str) -> OrderStatus:
        """Convert CCXT order status to our enum"""
        status_map = {
            'open': OrderStatus.PENDING,
            'closed': OrderStatus.FILLED,
            'canceled': OrderStatus.CANCELLED,
            'cancelled': OrderStatus.CANCELLED,
            'expired': OrderStatus.CANCELLED,
            'rejected': OrderStatus.FAILED,
            'new': OrderStatus.PENDING,
            'partially_filled': OrderStatus.PARTIALLY_FILLED,
            'filled': OrderStatus.FILLED
        }
        return status_map.get(ccxt_status, OrderStatus.PENDING)
    
    async def get_24h_stats(self, symbol: str) -> Dict[str, Any]:
        """Get 24h trading statistics (Bybit-specific)"""
        await self._rate_limit()
        
        try:
            bybit_symbol = self.normalize_symbol(symbol)
            ticker = await self.ccxt_client.fetch_ticker(bybit_symbol)
            
            return {
                'volume_24h': Decimal(str(ticker.get('baseVolume', 0))),
                'volume_24h_quote': Decimal(str(ticker.get('quoteVolume', 0))),
                'price_change_24h': Decimal(str(ticker.get('change', 0))),
                'price_change_percent_24h': Decimal(str(ticker.get('percentage', 0))),
                'high_24h': Decimal(str(ticker.get('high', 0))),
                'low_24h': Decimal(str(ticker.get('low', 0))),
                'open_24h': Decimal(str(ticker.get('open', 0)))
            }
            
        except Exception as e:
            self._handle_error(e, f"get_24h_stats({symbol})")
