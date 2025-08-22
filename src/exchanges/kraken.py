"""
Kraken Exchange Connector for SmartArb Engine
Implements Kraken-specific API integration
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


class KrakenExchange(BaseExchange):
    """
    Kraken exchange implementation using CCXT
    
    Kraken specifics:
    - Higher fees but excellent security
    - Good for European market
    - Robust API with websocket support
    - Uses different symbol naming (XXBTZUSD vs BTC/USD)
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
                'rateLimit': 1000 / self.rate_limit,  # Convert to ms
            })
            
            # Test connection by fetching server time
            await self.ccxt_client.fetch_time()
            self.is_connected = True
            
            logger.info("kraken_connected", exchange=self.name)
            return True
            
        except Exception as e:
            self.is_connected = False
            self._handle_error(e, "connect")
            return False
    
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
            orderbook_data = await self.ccxt_client.fetch_order_book(kraken_symbol, depth)
            
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
            kraken_symbol = self.normalize_symbol(symbol)
            
            # Normalize amounts according to Kraken precision
            normalized_amount = self.normalize_amount(amount)
            normalized_price = self.normalize_price(price)
            
            # Place order via CCXT
            order_data = await self.ccxt_client.create_order(
                symbol=kraken_symbol,
                type=order_type,
                side=side.value,
                amount=float(normalized_amount),
                price=float(normalized_price) if order_type == 'limit' else None
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
            kraken_symbol = self.normalize_symbol(symbol)
            await self.ccxt_client.cancel_order(order_id, kraken_symbol)
            return True
            
        except Exception as e:
            logger.warning("cancel_order_failed", 
                         order_id=order_id, symbol=symbol, error=str(e))
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Get order status"""
        await self._rate_limit()
        
        try:
            kraken_symbol = self.normalize_symbol(symbol)
            order_data = await self.ccxt_client.fetch_order(order_id, kraken_symbol)
            
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
            kraken_symbol = self.normalize_symbol(symbol) if symbol else None
            orders_data = await self.ccxt_client.fetch_open_orders(kraken_symbol)
            
            orders = []
            for order_data in orders_data:
                original_symbol = self.reverse_symbol_map.get(order_data['symbol'], order_data['symbol'])
                
                orders.append(Order(
                    id=order_data['id'],
                    symbol=original_symbol,
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
        # Kraken has tiered fees, these are standard rates
        # In production, fetch actual user fees via API
        return {
            'maker': Decimal(str(self.config.get('maker_fee', 0.0016))),
            'taker': Decimal(str(self.config.get('taker_fee', 0.0026)))
        }
    
    def normalize_symbol(self, symbol: str) -> str:
        """Convert standard symbol to Kraken format"""
        return self.symbol_map.get(symbol, symbol)
    
    def normalize_amount(self, amount: Decimal) -> Decimal:
        """Normalize amount for Kraken (8 decimal places)"""
        return amount.quantize(Decimal('0.00000001'))
    
    def normalize_price(self, price: Decimal) -> Decimal:
        """Normalize price for Kraken (5 decimal places for most pairs)"""
        return price.quantize(Decimal('0.00001'))
    
    def _convert_order_status(self, ccxt_status: str) -> OrderStatus:
        """Convert CCXT order status to our enum"""
        status_map = {
            'open': OrderStatus.PENDING,
            'closed': OrderStatus.FILLED,
            'canceled': OrderStatus.CANCELLED,
            'cancelled': OrderStatus.CANCELLED,
            'expired': OrderStatus.CANCELLED,
            'rejected': OrderStatus.FAILED
        }
        return status_map.get(ccxt_status, OrderStatus.PENDING)
