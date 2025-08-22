"""
MEXC Exchange Connector for SmartArb Engine
Implements MEXC-specific API integration
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


class MEXCExchange(BaseExchange):
    """
    MEXC exchange implementation using CCXT
    
    MEXC specifics:
    - Large altcoin selection - good for arbitrage opportunities
    - Competitive fees
    - High volatility = higher potential profits
    - Sometimes has liquidity issues on smaller pairs
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
                'rateLimit': 3000,  # MEXC: 20 requests per second = 50ms between requests
                'options': {
                    'defaultType': 'spot',  # spot trading only for now
                }
            })
            
            # Test connection by fetching server time
            await self.ccxt_client.fetch_time()
            self.is_connected = True
            
            logger.info("mexc_connected", exchange=self.name)
            return True
            
        except Exception as e:
            self.is_connected = False
            self._handle_error(e, "connect")
            return False
    
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
            orderbook_data = await self.ccxt_client.fetch_order_book(mexc_symbol, depth)
            
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
            mexc_symbol = self.normalize_symbol(symbol)
            
            # Normalize amounts according to MEXC precision
            normalized_amount = self.normalize_amount(amount)
            normalized_price = self.normalize_price(price)
            
            # MEXC sometimes requires specific order parameters
            params = {}
            if order_type == 'limit':
                params['timeInForce'] = 'GTC'  # Good Till Cancelled
            
            # Place order via CCXT
            order_data = await self.ccxt_client.create_order(
                symbol=mexc_symbol,
                type=order_type,
                side=side.value,
                amount=float(normalized_amount),
                price=float(normalized_price) if order_type == 'limit' else None,
                params=params
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
            mexc_symbol = self.normalize_symbol(symbol)
            await self.ccxt_client.cancel_order(order_id, mexc_symbol)
            return True
            
        except Exception as e:
            logger.warning("cancel_order_failed", 
                         order_id=order_id, symbol=symbol, error=str(e))
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Get order status"""
        await self._rate_limit()
        
        try:
            mexc_symbol = self.normalize_symbol(symbol)
            order_data = await self.ccxt_client.fetch_order(order_id, mexc_symbol)
            
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
            mexc_symbol = self.normalize_symbol(symbol) if symbol else None
            orders_data = await self.ccxt_client.fetch_open_orders(mexc_symbol)
            
            orders = []
            for order_data in orders_data:
                orders.append(Order(
                    id=order_data['id'],
                    symbol=order_data['symbol'],  # MEXC uses standard format
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
            # MEXC standard fees - competitive but higher than tier-1 exchanges
            return {
                'maker': Decimal(str(self.config.get('maker_fee', 0.002))),  # 0.2%
                'taker': Decimal(str(self.config.get('taker_fee', 0.002)))   # 0.2%
            }
        except Exception as e:
            # Fallback to default values
            return {
                'maker': Decimal('0.002'),
                'taker': Decimal('0.002')
            }
    
    def normalize_symbol(self, symbol: str) -> str:
        """Convert standard symbol to MEXC format"""
        return self.symbol_map.get(symbol, symbol)
    
    def normalize_amount(self, amount: Decimal) -> Decimal:
        """Normalize amount for MEXC (6 decimal places typically)"""
        return amount.quantize(Decimal('0.000001'))
    
    def normalize_price(self, price: Decimal) -> Decimal:
        """Normalize price for MEXC (4 decimal places for most pairs)"""
        return price.quantize(Decimal('0.0001'))
    
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
            'filled': OrderStatus.FILLED,
            'pending': OrderStatus.PENDING
        }
        return status_map.get(ccxt_status, OrderStatus.PENDING)
    
    async def get_market_summary(self, symbol: str) -> Dict[str, Any]:
        """Get market summary for symbol (MEXC-specific)"""
        await self._rate_limit()
        
        try:
            mexc_symbol = self.normalize_symbol(symbol)
            ticker = await self.ccxt_client.fetch_ticker(mexc_symbol)
            
            return {
                'symbol': symbol,
                'last_price': Decimal(str(ticker.get('last', 0))),
                'volume_24h': Decimal(str(ticker.get('baseVolume', 0))),
                'volume_24h_quote': Decimal(str(ticker.get('quoteVolume', 0))),
                'price_change_24h': Decimal(str(ticker.get('change', 0))),
                'price_change_percent_24h': Decimal(str(ticker.get('percentage', 0))),
                'high_24h': Decimal(str(ticker.get('high', 0))),
                'low_24h': Decimal(str(ticker.get('low', 0))),
                'bid': Decimal(str(ticker.get('bid', 0))),
                'ask': Decimal(str(ticker.get('ask', 0))),
                'spread_percent': self._calculate_spread_percent(
                    Decimal(str(ticker.get('bid', 0))),
                    Decimal(str(ticker.get('ask', 0)))
                )
            }
            
        except Exception as e:
            self._handle_error(e, f"get_market_summary({symbol})")
    
    def _calculate_spread_percent(self, bid: Decimal, ask: Decimal) -> Decimal:
        """Calculate spread percentage"""
        if bid > 0 and ask > 0:
            return ((ask - bid) / bid) * 100
        return Decimal('0')
    
    async def check_symbol_status(self, symbol: str) -> Dict[str, Any]:
        """Check if symbol is active and tradeable (MEXC-specific)"""
        try:
            mexc_symbol = self.normalize_symbol(symbol)
            markets = await self.ccxt_client.fetch_markets()
            
            for market in markets:
                if market['symbol'] == mexc_symbol:
                    return {
                        'symbol': symbol,
                        'active': market.get('active', False),
                        'trading': market.get('spot', False),
                        'min_amount': Decimal(str(market.get('limits', {}).get('amount', {}).get('min', 0))),
                        'max_amount': Decimal(str(market.get('limits', {}).get('amount', {}).get('max', 0))),
                        'min_price': Decimal(str(market.get('limits', {}).get('price', {}).get('min', 0))),
                        'max_price': Decimal(str(market.get('limits', {}).get('price', {}).get('max', 0)))
                    }
            
            return {'symbol': symbol, 'active': False, 'trading': False}
            
        except Exception as e:
            logger.warning("check_symbol_status_failed", symbol=symbol, error=str(e))
            return {'symbol': symbol, 'active': False, 'trading': False}
