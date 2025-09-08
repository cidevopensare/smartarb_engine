#!/usr/bin/env python3
“””
Kraken Exchange Implementation for SmartArb Engine
Professional-grade implementation for Kraken spot trading
“””

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import structlog
import time

from .base_exchange import (
BaseExchange, OrderBook, Ticker, Balance, Trade, Order,
OrderSide, OrderType, OrderStatus, ExchangeError
)

logger = structlog.get_logger(**name**)

class KrakenExchange(BaseExchange):
“”“Kraken exchange implementation”””

```
@property
def name(self) -> str:
    return "kraken"

@property 
def ccxt_id(self) -> str:
    return "kraken"

def __init__(self, config: Dict[str, Any]):
    super().__init__(config)
    
    # Kraken-specific configuration
    self.kraken_config = self.exchange_config
    
    # Kraken symbol mapping (CCXT to Kraken format)
    self.symbol_map = {
        'BTC/USDT': 'XBTUSDT',
        'ETH/USDT': 'ETHUSDT', 
        'ADA/USDT': 'ADAUSDT',
        'DOT/USDT': 'DOTUSDT',
        'LINK/USDT': 'LINKUSDT',
        'MATIC/USDT': 'MATICUSDT'
    }
    
    # Reverse mapping
    self.reverse_symbol_map = {v: k for k, v in self.symbol_map.items()}
    
    # Kraken-specific settings
    self.min_order_sizes = {
        'BTC/USDT': Decimal('0.0001'),
        'ETH/USDT': Decimal('0.001'), 
        'ADA/USDT': Decimal('1.0'),
        'DOT/USDT': Decimal('0.1'),
        'LINK/USDT': Decimal('0.1'),
        'MATIC/USDT': Decimal('1.0')
    }
    
    self.price_precision = {
        'BTC/USDT': 1,
        'ETH/USDT': 2,
        'ADA/USDT': 5,
        'DOT/USDT': 3,
        'LINK/USDT': 3,
        'MATIC/USDT': 5
    }
    
    self.amount_precision = {
        'BTC/USDT': 8,
        'ETH/USDT': 8,
        'ADA/USDT': 2,
        'DOT/USDT': 4,
        'LINK/USDT': 4,
        'MATIC/USDT': 2
    }

async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
    """Get order book for symbol"""
    
    try:
        # Fetch order book using CCXT
        orderbook_data = await self._handle_request(
            self.ccxt_exchange.fetch_order_book,
            symbol,
            limit
        )
        
        # Convert to our format
        bids = [
            (Decimal(str(price)), Decimal(str(amount))) 
            for price, amount in orderbook_data['bids'][:limit]
        ]
        
        asks = [
            (Decimal(str(price)), Decimal(str(amount)))
            for price, amount in orderbook_data['asks'][:limit]
        ]
        
        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=orderbook_data['timestamp'] / 1000 if orderbook_data['timestamp'] else time.time()
        )
        
    except Exception as e:
        self.logger.error("orderbook_fetch_failed", symbol=symbol, error=str(e))
        raise ExchangeError(f"Failed to fetch orderbook for {symbol}: {str(e)}")

async def get_ticker(self, symbol: str) -> Ticker:
    """Get ticker for symbol"""
    
    try:
        # Fetch ticker using CCXT
        ticker_data = await self._handle_request(
            self.ccxt_exchange.fetch_ticker,
            symbol
        )
        
        return Ticker(
            symbol=symbol,
            bid=Decimal(str(ticker_data['bid'])) if ticker_data['bid'] else Decimal('0'),
            ask=Decimal(str(ticker_data['ask'])) if ticker_data['ask'] else Decimal('0'),
            last=Decimal(str(ticker_data['last'])) if ticker_data['last'] else Decimal('0'),
            volume=Decimal(str(ticker_data['baseVolume'])) if ticker_data['baseVolume'] else Decimal('0'),
            timestamp=ticker_data['timestamp'] / 1000 if ticker_data['timestamp'] else time.time()
        )
        
    except Exception as e:
        self.logger.error("ticker_fetch_failed", symbol=symbol, error=str(e))
        raise ExchangeError(f"Failed to fetch ticker for {symbol}: {str(e)}")

async def get_balance(self, asset: str = None) -> Dict[str, Balance]:
    """Get account balance"""
    
    try:
        # Fetch balance using CCXT
        balance_data = await self._handle_request(
            self.ccxt_exchange.fetch_balance
        )
        
        balances = {}
        
        for currency, balance_info in balance_data.items():
            if currency in ['info', 'free', 'used', 'total']:
                continue
            
            # Skip if specific asset requested and this isn't it
            if asset and currency != asset:
                continue
            
            # Skip zero balances
            total = Decimal(str(balance_info.get('total', 0)))
            if total == 0:
                continue
            
            balances[currency] = Balance(
                asset=currency,
                free=Decimal(str(balance_info.get('free', 0))),
                locked=Decimal(str(balance_info.get('used', 0))),
                total=total
            )
        
        # If specific asset requested, return just that one
        if asset:
            return {asset: balances.get(asset, Balance(asset, Decimal('0'), Decimal('0'), Decimal('0')))}
        
        return balances
        
    except Exception as e:
        self.logger.error("balance_fetch_failed", error=str(e))
        raise ExchangeError(f"Failed to fetch balance: {str(e)}")

async def place_order(self, symbol: str, side: OrderSide, 
                     amount: Decimal, price: Optional[Decimal] = None,
                     order_type: OrderType = OrderType.MARKET) -> Order:
    """Place order"""
    
    try:
        # Validate minimum order size
        min_size = self.get_min_order_size(symbol)
        if amount < min_size:
            raise ExchangeError(f"Order amount {amount} below minimum {min_size} for {symbol}")
        
        # Prepare order parameters
        order_params = {
            'symbol': symbol,
            'type': order_type.value,
            'side': side.value,
            'amount': float(amount)
        }
        
        if price and order_type == OrderType.LIMIT:
            order_params['price'] = float(price)
        
        # Add Kraken-specific parameters
        if order_type == OrderType.MARKET:
            # Kraken market orders
            order_params['params'] = {'ordertype': 'market'}
        else:
            # Kraken limit orders
            order_params['params'] = {'ordertype': 'limit'}
        
        # Place order using CCXT
        order_result = await self._handle_request(
            self.ccxt_exchange.create_order,
            **order_params
        )
        
        # Convert to our Order format
        return self._convert_order(order_result, symbol)
        
    except Exception as e:
        self.logger.error("order_placement_failed", 
                        symbol=symbol, 
                        side=side.value,
                        amount=float(amount),
                        error=str(e))
        raise ExchangeError(f"Failed to place order: {str(e)}")

async def cancel_order(self, order_id: str, symbol: str) -> bool:
    """Cancel order"""
    
    try:
        await self._handle_request(
            self.ccxt_exchange.cancel_order,
            order_id,
            symbol
        )
        
        self.logger.info("order_cancelled", order_id=order_id, symbol=symbol)
        return True
        
    except Exception as e:
        self.logger.error("order_cancellation_failed", 
                        order_id=order_id, 
                        symbol=symbol,
                        error=str(e))
        return False

async def get_order(self, order_id: str, symbol: str) -> Order:
    """Get order status"""
    
    try:
        order_data = await self._handle_request(
            self.ccxt_exchange.fetch_order,
            order_id,
            symbol
        )
        
        return self._convert_order(order_data, symbol)
        
    except Exception as e:
        self.logger.error("order_fetch_failed", 
                        order_id=order_id,
                        symbol=symbol,
                        error=str(e))
        raise ExchangeError(f"Failed to fetch order {order_id}: {str(e)}")

async def get_open_orders(self, symbol: str = None) -> List[Order]:
    """Get open orders"""
    
    try:
        if symbol:
            orders_data = await self._handle_request(
                self.ccxt_exchange.fetch_open_orders,
                symbol
            )
        else:
            orders_data = await self._handle_request(
                self.ccxt_exchange.fetch_open_orders
            )
        
        orders = []
        for order_data in orders_data:
            try:
                order = self._convert_order(order_data, order_data['symbol'])
                orders.append(order)
            except Exception as e:
                self.logger.warning("order_conversion_failed", 
                                  order_id=order_data.get('id'),
                                  error=str(e))
        
        return orders
        
    except Exception as e:
        self.logger.error("open_orders_fetch_failed", symbol=symbol, error=str(e))
        raise ExchangeError(f"Failed to fetch open orders: {str(e)}")

async def get_trades(self, symbol: str, limit: int = 100) -> List[Trade]:
    """Get trade history"""
    
    try:
        trades_data = await self._handle_request(
            self.ccxt_exchange.fetch_my_trades,
            symbol,
            None,  # since
            limit
        )
        
        trades = []
        for trade_data in trades_data:
            try:
                trade = Trade(
                    id=str(trade_data['id']),
                    symbol=trade_data['symbol'],
                    side=OrderSide(trade_data['side']),
                    amount=Decimal(str(trade_data['amount'])),
                    price=Decimal(str(trade_data['price'])),
                    cost=Decimal(str(trade_data['cost'])),
                    fee=Decimal(str(trade_data['fee']['cost'])) if trade_data['fee'] else Decimal('0'),
                    fee_currency=trade_data['fee']['currency'] if trade_data['fee'] else '',
                    timestamp=trade_data['timestamp'] / 1000 if trade_data['timestamp'] else time.time(),
                    order_id=str(trade_data['order']) if trade_data['order'] else None
                )
                trades.append(trade)
            except Exception as e:
                self.logger.warning("trade_conversion_failed", 
                                  trade_id=trade_data.get('id'),
                                  error=str(e))
        
        return trades
        
    except Exception as e:
        self.logger.error("trades_fetch_failed", symbol=symbol, error=str(e))
        raise ExchangeError(f"Failed to fetch trades for {symbol}: {str(e)}")

def _convert_order(self, order_data: Dict[str, Any], symbol: str) -> Order:
    """Convert CCXT order data to our Order format"""
    
    # Map CCXT status to our OrderStatus
    status_map = {
        'open': OrderStatus.OPEN,
        'closed': OrderStatus.FILLED,
        'canceled': OrderStatus.CANCELLED,
        'cancelled': OrderStatus.CANCELLED,
        'pending': OrderStatus.PENDING,
        'rejected': OrderStatus.REJECTED,
        'expired': OrderStatus.EXPIRED
    }
    
    status = status_map.get(order_data['status'], OrderStatus.PENDING)
    
    # Convert trades
    trades = []
    if order_data.get('trades'):
        for trade_data in order_data['trades']:
            trade = Trade(
                id=str(trade_data['id']),
                symbol=symbol,
                side=OrderSide(trade_data['side']),
                amount=Decimal(str(trade_data['amount'])),
                price=Decimal(str(trade_data['price'])),
                cost=Decimal(str(trade_data['cost'])),
                fee=Decimal(str(trade_data['fee']['cost'])) if trade_data['fee'] else Decimal('0'),
                fee_currency=trade_data['fee']['currency'] if trade_data['fee'] else '',
                timestamp=trade_data['timestamp'] / 1000 if trade_data['timestamp'] else time.time(),
                order_id=str(order_data['id'])
            )
            trades.append(trade)
    
    return Order(
        id=str(order_data['id']),
        symbol=symbol,
        side=OrderSide(order_data['side']),
        type=OrderType(order_data['type']),
        amount=Decimal(str(order_data['amount'])),
        price=Decimal(str(order_data['price'])) if order_data['price'] else None,
        status=status,
        filled=Decimal(str(order_data['filled'])),
        remaining=Decimal(str(order_data['remaining'])),
        cost=Decimal(str(order_data['cost'])) if order_data['cost'] else Decimal('0'),
        fee=Decimal(str(order_data['fee']['cost'])) if order_data.get('fee') else Decimal('0'),
        fee_currency=order_data['fee']['currency'] if order_data.get('fee') else '',
        timestamp=order_data['timestamp'] / 1000 if order_data['timestamp'] else time.time(),
        trades=trades
    )

def get_min_order_size(self, symbol: str) -> Decimal:
    """Get minimum order size for symbol"""
    return self.min_order_sizes.get(symbol, Decimal('0.001'))

def get_price_precision(self, symbol: str) -> int:
    """Get price precision for symbol"""
    return self.price_precision.get(symbol, 8)

def get_amount_precision(self, symbol: str) -> int:
    """Get amount precision for symbol"""
    return self.amount_precision.get(symbol, 8)

def _format_kraken_symbol(self, symbol: str) -> str:
    """Convert standard symbol to Kraken format"""
    return self.symbol_map.get(symbol, symbol)

def _parse_kraken_symbol(self, kraken_symbol: str) -> str:
    """Convert Kraken symbol to standard format"""
    return self.reverse_symbol_map.get(kraken_symbol, kraken_symbol)

async def _kraken_specific_setup(self):
    """Kraken-specific initialization"""
    
    try:
        # Get trading fees
        if self.ccxt_exchange:
            trading_fees = await self._handle_request(
                self.ccxt_exchange.fetch_trading_fees
            )
            
            if trading_fees:
                self.fees = trading_fees
                self.logger.info("kraken_fees_loaded", 
                               maker_fee=trading_fees.get('maker', 'unknown'),
                               taker_fee=trading_fees.get('taker', 'unknown'))
        
    except Exception as e:
        self.logger.warning("kraken_setup_failed", error=str(e))

async def initialize(self) -> bool:
    """Initialize Kraken exchange connection"""
    
    # Call parent initialization
    success = await super().initialize()
    
    if success:
        # Kraken-specific setup
        await self._kraken_specific_setup()
    
    return success
```