"""
Portfolio Manager for SmartArb Engine
Tracks balances, positions, and portfolio performance across exchanges
"""

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import time
import structlog

from ..exchanges.base_exchange import BaseExchange, Balance

logger = structlog.get_logger(__name__)


@dataclass
class PortfolioPosition:
    """Individual position tracking"""
    symbol: str
    exchange: str
    base_amount: Decimal
    quote_amount: Decimal
    average_price: Decimal
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    last_updated: float = field(default_factory=time.time)


@dataclass
class ExchangePortfolio:
    """Portfolio state for a single exchange"""
    exchange_name: str
    balances: Dict[str, Balance] = field(default_factory=dict)
    total_value_usdt: Decimal = Decimal('0')
    last_updated: float = field(default_factory=time.time)
    
    def get_balance(self, asset: str) -> Balance:
        """Get balance for specific asset"""
        return self.balances.get(asset, Balance(asset=asset, free=Decimal('0'), locked=Decimal('0')))
    
    def has_sufficient_balance(self, asset: str, required_amount: Decimal) -> bool:
        """Check if exchange has sufficient free balance"""
        balance = self.get_balance(asset)
        return balance.free >= required_amount


class PortfolioManager:
    """
    Portfolio Management System
    
    Features:
    - Real-time balance tracking across exchanges
    - Position management
    - PnL calculation
    - Portfolio valuation in USDT
    - Risk exposure monitoring
    """
    
    def __init__(self, exchanges: Dict[str, BaseExchange], config: Dict[str, Any]):
        self.exchanges = exchanges
        self.config = config
        
        # Portfolio state
        self.exchange_portfolios: Dict[str, ExchangePortfolio] = {}
        self.positions: Dict[str, PortfolioPosition] = {}  # position_id -> position
        
        # Performance tracking
        self.total_realized_pnl = Decimal('0')
        self.total_unrealized_pnl = Decimal('0')
        self.total_portfolio_value = Decimal('0')
        
        # Update settings
        self.balance_update_interval = config.get('balance_update_interval', 30)  # seconds
        self.last_balance_update = 0
        
        # Price cache for valuation
        self.price_cache: Dict[str, Decimal] = {}
        self.price_cache_ttl = 60  # seconds
        self.last_price_update = 0
        
        # Initialize portfolios
        self._initialize_portfolios()
        
        logger.info("portfolio_manager_initialized", 
                   exchanges=list(self.exchanges.keys()))
    
    def _initialize_portfolios(self):
        """Initialize portfolio tracking for each exchange"""
        for exchange_name in self.exchanges.keys():
            self.exchange_portfolios[exchange_name] = ExchangePortfolio(exchange_name)
    
    async def update_balances(self, force_update: bool = False) -> bool:
        """
        Update balances from all exchanges
        
        Args:
            force_update: Force update even if within cache period
            
        Returns:
            bool: True if update successful
        """
        current_time = time.time()
        
        # Check if update needed
        if not force_update and (current_time - self.last_balance_update) < self.balance_update_interval:
            return True
        
        logger.debug("updating_portfolio_balances")
        
        success_count = 0
        
        # Update balances for each exchange
        for exchange_name, exchange in self.exchanges.items():
            if not exchange.is_connected:
                logger.warning("exchange_not_connected", exchange=exchange_name)
                continue
            
            try:
                # Fetch balances
                balances = await exchange.get_balance()
                
                # Update portfolio
                portfolio = self.exchange_portfolios[exchange_name]
                portfolio.balances = balances
                portfolio.last_updated = current_time
                
                # Calculate portfolio value in USDT
                portfolio.total_value_usdt = await self._calculate_portfolio_value(
                    exchange_name, balances
                )
                
                success_count += 1
                
                logger.debug("balances_updated",
                           exchange=exchange_name,
                           assets=len(balances),
                           total_value=float(portfolio.total_value_usdt))
                
            except Exception as e:
                logger.error("balance_update_failed",
                           exchange=exchange_name,
                           error=str(e))
        
        if success_count > 0:
            self.last_balance_update = current_time
            await self._update_total_portfolio_value()
            return True
        
        return False
    
    async def _calculate_portfolio_value(self, exchange_name: str, 
                                       balances: Dict[str, Balance]) -> Decimal:
        """Calculate total portfolio value in USDT for an exchange"""
        total_value = Decimal('0')
        
        for asset, balance in balances.items():
            if balance.total <= 0:
                continue
            
            if asset == 'USDT':
                # USDT is already in target currency
                total_value += balance.total
            else:
                # Convert to USDT using current price
                try:
                    price = await self._get_asset_price(asset, 'USDT')
                    total_value += balance.total * price
                except Exception as e:
                    logger.warning("price_conversion_failed",
                                 asset=asset,
                                 exchange=exchange_name,
                                 error=str(e))
        
        return total_value
    
    async def _get_asset_price(self, base_asset: str, quote_asset: str) -> Decimal:
        """Get current price for asset pair"""
        symbol = f"{base_asset}/{quote_asset}"
        
        # Check cache first
        current_time = time.time()
        cache_key = symbol
        
        if (cache_key in self.price_cache and 
            (current_time - self.last_price_update) < self.price_cache_ttl):
            return self.price_cache[cache_key]
        
        # Fetch fresh price from any available exchange
        for exchange in self.exchanges.values():
            if not exchange.is_connected:
                continue
            
            try:
                ticker = await exchange.get_ticker(symbol)
                price = ticker.last
                
                # Cache the price
                self.price_cache[cache_key] = price
                self.last_price_update = current_time
                
                return price
                
            except Exception:
                continue  # Try next exchange
        
        # If all exchanges fail, return 0 (or could raise exception)
        logger.warning("price_fetch_failed_all_exchanges", symbol=symbol)
        return Decimal('0')
    
    async def _update_total_portfolio_value(self):
        """Update total portfolio value across all exchanges"""
        total_value = Decimal('0')
        
        for portfolio in self.exchange_portfolios.values():
            total_value += portfolio.total_value_usdt
        
        self.total_portfolio_value = total_value
        
        logger.debug("total_portfolio_value_updated", 
                    value=float(total_value))
    
    def get_exchange_balance(self, exchange_name: str, asset: str) -> Balance:
        """Get balance for specific asset on specific exchange"""
        portfolio = self.exchange_portfolios.get(exchange_name)
        if not portfolio:
            return Balance(asset=asset, free=Decimal('0'), locked=Decimal('0'))
        
        return portfolio.get_balance(asset)
    
    def check_sufficient_balance(self, exchange_name: str, asset: str, 
                               required_amount: Decimal) -> bool:
        """Check if exchange has sufficient balance for trade"""
        portfolio = self.exchange_portfolios.get(exchange_name)
        if not portfolio:
            return False
        
        return portfolio.has_sufficient_balance(asset, required_amount)
    
    def get_total_balance(self, asset: str) -> Decimal:
        """Get total balance across all exchanges for asset"""
        total = Decimal('0')
        
        for portfolio in self.exchange_portfolios.values():
            balance = portfolio.get_balance(asset)
            total += balance.total
        
        return total
    
    async def get_total_value(self) -> Decimal:
        """Get total portfolio value in USDT"""
        if time.time() - self.last_balance_update > self.balance_update_interval:
            await self.update_balances()
        
        return self.total_portfolio_value
    
    def record_trade(self, exchange_name: str, symbol: str, side: str,
                    amount: Decimal, price: Decimal, fee: Decimal = Decimal('0'),
                    trade_id: str = "") -> str:
        """
        Record a trade execution
        
        Returns:
            str: Position ID
        """
        base_asset, quote_asset = symbol.split('/')
        
        # Create position ID
        position_id = f"{exchange_name}_{symbol}_{trade_id}_{int(time.time())}"
        
        # Calculate amounts based on side
        if side.lower() == 'buy':
            base_amount = amount
            quote_amount = -(amount * price + fee)  # Negative because we spent quote
        else:  # sell
            base_amount = -amount  # Negative because we sold base
            quote_amount = amount * price - fee
        
        # Create or update position
        position = PortfolioPosition(
            symbol=symbol,
            exchange=exchange_name,
            base_amount=base_amount,
            quote_amount=quote_amount,
            average_price=price
        )
        
        self.positions[position_id] = position
        
        logger.info("trade_recorded",
                   position_id=position_id,
                   symbol=symbol,
                   side=side,
                   amount=float(amount),
                   price=float(price))
        
        return position_id
    
    def close_position(self, position_id: str, closing_price: Decimal) -> Decimal:
        """
        Close a position and calculate realized PnL
        
        Returns:
            Decimal: Realized PnL
        """
        if position_id not in self.positions:
            logger.warning("position_not_found", position_id=position_id)
            return Decimal('0')
        
        position = self.positions[position_id]
        
        # Calculate realized PnL
        # For buy position: PnL = (closing_price - entry_price) * amount
        # For sell position: PnL = (entry_price - closing_price) * amount
        if position.base_amount > 0:  # Long position
            realized_pnl = (closing_price - position.average_price) * position.base_amount
        else:  # Short position
            realized_pnl = (position.average_price - closing_price) * abs(position.base_amount)
        
        position.realized_pnl = realized_pnl
        self.total_realized_pnl += realized_pnl
        
        logger.info("position_closed",
                   position_id=position_id,
                   realized_pnl=float(realized_pnl))
        
        # Remove from active positions
        del self.positions[position_id]
        
        return realized_pnl
    
    async def calculate_unrealized_pnl(self) -> Decimal:
        """Calculate total unrealized PnL for all open positions"""
        total_unrealized = Decimal('0')
        
        for position in self.positions.values():
            try:
                # Get current price
                current_price = await self._get_asset_price(*position.symbol.split('/'))
                
                # Calculate unrealized PnL
                if position.base_amount > 0:  # Long position
                    unrealized_pnl = (current_price - position.average_price) * position.base_amount
                else:  # Short position
                    unrealized_pnl = (position.average_price - current_price) * abs(position.base_amount)
                
                position.unrealized_pnl = unrealized_pnl
                total_unrealized += unrealized_pnl
                
            except Exception as e:
                logger.warning("unrealized_pnl_calculation_failed",
                             position_id=position.symbol,
                             error=str(e))
        
        self.total_unrealized_pnl = total_unrealized
        return total_unrealized
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        return {
            'total_value_usdt': float(self.total_portfolio_value),
            'total_realized_pnl': float(self.total_realized_pnl),
            'total_unrealized_pnl': float(self.total_unrealized_pnl),
            'open_positions': len(self.positions),
            'last_balance_update': self.last_balance_update,
            'exchanges': {
                name: {
                    'total_value_usdt': float(portfolio.total_value_usdt),
                    'assets_count': len(portfolio.balances),
                    'last_updated': portfolio.last_updated
                }
                for name, portfolio in self.exchange_portfolios.items()
            }
        }
    
    def get_exchange_balances(self, exchange_name: str) -> Dict[str, Dict[str, float]]:
        """Get detailed balances for specific exchange"""
        portfolio = self.exchange_portfolios.get(exchange_name)
        if not portfolio:
            return {}
        
        return {
            asset: {
                'free': float(balance.free),
                'locked': float(balance.locked),
                'total': float(balance.total)
            }
            for asset, balance in portfolio.balances.items()
            if balance.total > 0
        }
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get list of all open positions"""
        return [
            {
                'position_id': position_id,
                'symbol': position.symbol,
                'exchange': position.exchange,
                'base_amount': float(position.base_amount),
                'quote_amount': float(position.quote_amount),
                'average_price': float(position.average_price),
                'unrealized_pnl': float(position.unrealized_pnl),
                'last_updated': position.last_updated
            }
            for position_id, position in self.positions.items()
        ]
