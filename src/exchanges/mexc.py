#!/usr/bin/env python3
“””
MEXC Exchange Implementation for SmartArb Engine
Wide altcoin selection exchange with competitive rates
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

class MEXCExchange(BaseExchange):
“”“MEXC exchange implementation”””

```
@property
def name(self) -> str:
    return "mexc"

@property 
def ccxt_id(self) -> str:
    return "mexc"

def __init__(self, config: Dict[str, Any]):
    super().__init__(config)
    
    # MEXC-specific configuration
    self.mexc_config = self.exchange_config
    
    # MEXC symbol mapping (usually no changes needed for spot)
    self.symbol_map = {
        'BTC/USDT': 'BTCUSDT',
        'ETH/USDT': 'ETHUSDT',
        'BNB/USDT': 'BNBUSDT',
        'ADA/USDT': 'ADAUSDT',
        'DOT/USDT': 'DOTUSDT',
        'LINK/USDT': 'LINKUSDT',
        'MATIC/USDT': 'MATICUSDT'
    }
    
    # Reverse mapping
    self.reverse_symbol_map = {v: k for k, v in self.symbol_map.items()}
    
    # MEXC-specific settings
    self.min_order_sizes = {
        'BTC/USDT': Decimal('0.00001'),
        'ETH/USDT': Decimal('0.0001'),
        'BNB/USDT': Decimal('0.001'),
        'ADA/USDT': Decimal('1.0'),
        'DOT/USDT': Decimal('0.1'),
        'LINK/USDT': Decimal('0.1'),
        'MATIC/USDT': Decimal('1.0')
    }
    
    self.price_precision = {
        'BTC/USDT': 2,
        'ETH/USDT': 2,
        'BNB/USDT': 4,
        'ADA/USDT': 6,
        'DOT/USDT': 4,
        'LINK/USDT': 4,
        'MATIC/USDT': 6
    }
    
    self.amount_precision = {
        'BTC/USDT': 5,
        'ETH/USDT': 4,
        'BNB/USDT': 3,
        'ADA/USDT': 1,
        'DOT/USDT': 2,
        'LINK/USDT': 2,
        'MATIC/USDT': 1
    }
    
    # MEXC specific rate limits (more lenient)
    self.mexc_rate_limit = self.mexc_config.get('rate_limit', 20)  # 20 requests per second

async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
    """Get order book for symbol"""
    
    try:
        # MEXC supports higher limits
        actual_limit = min(limit, 100)
        
        # Fetch order book using CCXT
        orderbook_data = await self._handle_request(
            self.ccxt_exchange.fetch_order_book,
            symbol,
            actual_limit
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
        
        # Round amounts to proper precision
        amount_precision = self.get_amount_precision(symbol)
        amount = amount.quantize(Decimal('0.1') ** amount_precision)
        
        # Prepare order parameters
        order_params = {
            'symbol': symbol,
            'type': order_type.value,
            'side': side.value,
            'amount': float(amount)
        }
        
        if price and order_type == OrderType.LIMIT:
            price_precision = self.get_price_precision(symbol)
            price = price.quantize(Decimal('0.1') ** price_precision)
            order_params['price'] = float(price)
        
        # Add MEXC-specific parameters
        params = {}
        
        # MEXC uses different time in force options
        if order_type == OrderType.LIMIT:
            params['timeInForce'] = 'GTC'  # Good Till Cancelled
        
        order_params['params'] = params
        
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
        # MEXC supports up to 1000 trades per request
        actual_limit = min(limit, 1000)
        
        trades_data = await self._handle_request(
            self.ccxt_exchange.fetch_my_trades,
            symbol,
            None,  # since
            actual_limit
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
        'expired': OrderStatus.EXPIRED,
        'filled': OrderStatus.FILLED,
        'partially_filled': OrderStatus.OPEN,
        'new': OrderStatus.PENDING
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

def _format_mexc_symbol(self, symbol: str) -> str:
    """Convert standard symbol to MEXC format"""
    return self.symbol_map.get(symbol, symbol)

def _parse_mexc_symbol(self, mexc_symbol: str) -> str:
    """Convert MEXC symbol to standard format"""
    return self.reverse_symbol_map.get(mexc_symbol, mexc_symbol)

async def _mexc_specific_setup(self):
    """MEXC-specific initialization"""
    
    try:
        # Get server time to check connectivity
        if hasattr(self.ccxt_exchange, 'fetch_time'):
            server_time = await self._handle_request(
                self.ccxt_exchange.fetch_time
            )
            
            if server_time:
                time_diff = abs(time.time() * 1000 - server_time)
                self.logger.info("mexc_server_time_sync", 
                               time_diff_ms=time_diff)
                
                # Warn if time difference is too large
                if time_diff > 5000:  # 5 seconds
                    self.logger.warning("mexc_time_sync_issue",
                                      time_diff_ms=time_diff)
        
        # Get account info
        account_info = await self._handle_request(
            self.ccxt_exchange.fetch_balance
        )
        
        if account_info:
            self.logger.info("mexc_account_connected")
            
        # Get trading fees
        try:
            fees_data = await self.get_trading_fees()
            self.fees = fees_data
            self.logger.info("mexc_fees_loaded",
                           maker=fees_data.get('maker'),
                           taker=fees_data.get('taker'))
        except Exception as e:
            self.logger.warning("mexc_fees_load_failed", error=str(e))
        
    except Exception as e:
        self.logger.warning("mexc_setup_failed", error=str(e))

async def initialize(self) -> bool:
    """Initialize MEXC exchange connection"""
    
    # Call parent initialization
    success = await super().initialize()
    
    if success:
        # MEXC-specific setup
        await self._mexc_specific_setup()
    
    return success

async def get_trading_fees(self) -> Dict[str, Any]:
    """Get current trading fees"""
    
    try:
        fees_data = await self._handle_request(
            self.ccxt_exchange.fetch_trading_fees
        )
        
        return {
            'maker': fees_data.get('maker', 0.002),
            'taker': fees_data.get('taker', 0.002),
            'trading': fees_data.get('trading', {}),
            'funding': fees_data.get('funding', {})
        }
        
    except Exception as e:
        self.logger.warning("trading_fees_fetch_failed", error=str(e))
        return {
            'maker': 0.002,  # Default 0.2%
            'taker': 0.002,  # Default 0.2%
            'trading': {},
            'funding': {}
        }

async def get_deposit_address(self, currency: str, network: str = None) -> Dict[str, Any]:
    """Get deposit address for currency"""
    
    try:
        params = {}
        if network:
            params['network'] = network
        
        address_data = await self._handle_request(
            self.ccxt_exchange.fetch_deposit_address,
            currency,
            params
        )
        
        return {
            'currency': currency,
            'address': address_data.get('address'),
            'tag': address_data.get('tag'),
            'network': address_data.get('network'),
            'info': address_data.get('info', {})
        }
        
    except Exception as e:
        self.logger.error("deposit_address_fetch_failed", 
                        currency=currency, 
                        error=str(e))
        raise ExchangeError(f"Failed to get deposit address for {currency}: {str(e)}")

async def get_deposit_history(self, currency: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get deposit history"""
    
    try:
        deposits_data = await self._handle_request(
            self.ccxt_exchange.fetch_deposits,
            currency,
            None,  # since
            limit
        )
        
        deposits = []
        for deposit_data in deposits_data:
            deposits.append({
                'id': deposit_data.get('id'),
                'currency': deposit_data.get('currency'),
                'amount': float(deposit_data.get('amount', 0)),
                'address': deposit_data.get('address'),
                'tag': deposit_data.get('tag'),
                'status': deposit_data.get('status'),
                'timestamp': deposit_data.get('timestamp'),
                'network': deposit_data.get('network'),
                'fee': float(deposit_data.get('fee', 0)),
                'txid': deposit_data.get('txid')
            })
        
        return deposits
        
    except Exception as e:
        self.logger.error("deposit_history_fetch_failed", 
                        currency=currency, 
                        error=str(e))
        return []

async def get_withdrawal_history(self, currency: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get withdrawal history"""
    
    try:
        withdrawals_data = await self._handle_request(
            self.ccxt_exchange.fetch_withdrawals,
            currency,
            None,  # since
            limit
        )
        
        withdrawals = []
        for withdrawal_data in withdrawals_data:
            withdrawals.append({
                'id': withdrawal_data.get('id'),
                'currency': withdrawal_data.get('currency'),
                'amount': float(withdrawal_data.get('amount', 0)),
                'address': withdrawal_data.get('address'),
                'tag': withdrawal_data.get('tag'),
                'status': withdrawal_data.get('status'),
                'timestamp': withdrawal_data.get('timestamp'),
                'network': withdrawal_data.get('network'),
                'fee': float(withdrawal_data.get('fee', 0)),
                'txid': withdrawal_data.get('txid')
            })
        
        return withdrawals
        
    except Exception as e:
        self.logger.error("withdrawal_history_fetch_failed", 
                        currency=currency, 
                        error=str(e))
        return []
```