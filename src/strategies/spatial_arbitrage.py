"""
Spatial Arbitrage Strategy for SmartArb Engine
Detects and executes cross-exchange arbitrage opportunities
"""

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import structlog

from ..exchanges.base_exchange import BaseExchange, Ticker, OrderBook
from .base_strategy import BaseStrategy, Opportunity

logger = structlog.get_logger(__name__)


@dataclass
class SpatialOpportunity(Opportunity):
    """Spatial arbitrage opportunity data"""
    buy_exchange: str
    sell_exchange: str
    buy_price: Decimal
    sell_price: Decimal
    spread_percent: Decimal
    volume_available: Decimal
    estimated_fees: Decimal
    net_profit_percent: Decimal
    confidence_score: float  # 0-1 based on liquidity, spread stability
    
    def __post_init__(self):
        """Calculate additional metrics after initialization"""
        super().__post_init__()
        if not self.opportunity_id:
            self.opportunity_id = f"spatial_{self.buy_exchange}_{self.sell_exchange}_{self.symbol}_{int(self.timestamp)}"


class SpatialArbitrageStrategy(BaseStrategy):
    """
    Spatial Arbitrage Strategy
    
    Identifies price differences for the same asset across different exchanges
    and executes simultaneous buy/sell orders to capture the spread.
    
    Key considerations:
    - Transaction fees on both exchanges
    - Order book depth and slippage
    - Transfer time between exchanges (avoided by pre-positioning)
    - Exchange reliability and execution speed
    """
    
    def __init__(self, exchanges: Dict[str, BaseExchange], config: Dict[str, Any]):
        super().__init__("spatial_arbitrage", exchanges, config)
        
        # Strategy-specific configuration
        self.min_spread_percent = Decimal(str(config.get('min_spread_percent', 0.20)))
        self.max_position_size = Decimal(str(config.get('max_position_size', 1000)))
        self.min_volume_24h = Decimal(str(config.get('min_volume_24h', 1000000)))
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        
        # Exchange pairs for arbitrage
        self.exchange_pairs = self._get_exchange_pairs()
        
        # Trading pairs to monitor
        self.trading_pairs = config.get('trading_pairs', [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT', 'LINK/USDT', 'MATIC/USDT'
        ])
        
        # Performance tracking
        self.opportunities_found = 0
        self.opportunities_executed = 0
        self.total_profit = Decimal('0')
        
        logger.info("spatial_arbitrage_initialized",
                   pairs=len(self.exchange_pairs),
                   symbols=len(self.trading_pairs),
                   min_spread=float(self.min_spread_percent))
    
    def _get_exchange_pairs(self) -> List[Tuple[str, str]]:
        """Get all possible exchange pairs for arbitrage"""
        exchange_names = list(self.exchanges.keys())
        pairs = []
        
        for i, ex1 in enumerate(exchange_names):
            for ex2 in exchange_names[i+1:]:
                pairs.append((ex1, ex2))
                pairs.append((ex2, ex1))  # Both directions
        
        return pairs
    
    async def find_opportunities(self) -> List[SpatialOpportunity]:
        """Scan for spatial arbitrage opportunities"""
        opportunities = []
        
        try:
            # Get current market data for all pairs
            market_data = await self._fetch_market_data()
            
            # Analyze each trading pair across exchange combinations
            for symbol in self.trading_pairs:
                if symbol not in market_data:
                    continue
                
                # Check all exchange pairs for this symbol
                for buy_exchange, sell_exchange in self.exchange_pairs:
                    if (buy_exchange not in market_data[symbol] or 
                        sell_exchange not in market_data[symbol]):
                        continue
                    
                    opportunity = await self._analyze_opportunity(
                        symbol, buy_exchange, sell_exchange, market_data[symbol]
                    )
                    
                    if opportunity:
                        opportunities.append(opportunity)
                        self.opportunities_found += 1
            
            # Sort by profitability
            opportunities.sort(key=lambda x: x.net_profit_percent, reverse=True)
            
            if opportunities:
                logger.info("spatial_opportunities_found", 
                           count=len(opportunities),
                           best_profit=float(opportunities[0].net_profit_percent))
            
            return opportunities
            
        except Exception as e:
            logger.error("find_opportunities_failed", error=str(e))
            return []
    
    async def _fetch_market_data(self) -> Dict[str, Dict[str, Ticker]]:
        """Fetch current market data from all exchanges"""
        market_data = {}
        
        # Fetch tickers concurrently
        tasks = []
        for symbol in self.trading_pairs:
            market_data[symbol] = {}
            for exchange_name, exchange in self.exchanges.items():
                if exchange.is_connected:
                    task = self._fetch_ticker_safe(exchange, exchange_name, symbol)
                    tasks.append(task)
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                logger.warning("ticker_fetch_failed", error=str(result))
                continue
            
            if result:
                exchange_name, symbol, ticker = result
                market_data[symbol][exchange_name] = ticker
        
        return market_data
    
    async def _fetch_ticker_safe(self, exchange: BaseExchange, exchange_name: str, symbol: str):
        """Safely fetch ticker with error handling"""
        try:
            ticker = await exchange.get_ticker(symbol)
            return (exchange_name, symbol, ticker)
        except Exception as e:
            logger.warning("ticker_fetch_error", 
                         exchange=exchange_name, symbol=symbol, error=str(e))
            return None
    
    async def _analyze_opportunity(self, symbol: str, buy_exchange: str, sell_exchange: str, 
                                 market_data: Dict[str, Ticker]) -> Optional[SpatialOpportunity]:
        """Analyze potential arbitrage opportunity between two exchanges"""
        
        buy_ticker = market_data.get(buy_exchange)
        sell_ticker = market_data.get(sell_exchange)
        
        if not buy_ticker or not sell_ticker:
            return None
        
        # Check if we have valid bid/ask prices
        if not all([buy_ticker.ask, sell_ticker.bid, buy_ticker.ask > 0, sell_ticker.bid > 0]):
            return None
        
        # Calculate spread
        buy_price = buy_ticker.ask  # We buy at ask price
        sell_price = sell_ticker.bid  # We sell at bid price
        
        if sell_price <= buy_price:
            return None  # No arbitrage opportunity
        
        spread_percent = ((sell_price - buy_price) / buy_price) * 100
        
        # Quick spread filter
        if spread_percent < self.min_spread_percent:
            return None
        
        # Calculate estimated fees
        buy_fees = await self._get_trading_fees(buy_exchange, symbol)
        sell_fees = await self._get_trading_fees(sell_exchange, symbol)
        total_fees_percent = buy_fees['taker'] + sell_fees['taker']
        
        # Net profit after fees
        net_profit_percent = spread_percent - (total_fees_percent * 100)
        
        # Must be profitable after fees
        if net_profit_percent <= 0:
            return None
        
        # Calculate available volume
        volume_available = await self._calculate_available_volume(
            buy_ticker, sell_ticker, symbol
        )
        
        if volume_available < Decimal('10'):  # Minimum viable trade size
            return None
        
        # Calculate position size (limited by volume and max position)
        position_size = min(volume_available, self.max_position_size)
        
        # Calculate confidence score
        confidence = self._calculate_confidence_score(
            buy_ticker, sell_ticker, spread_percent, volume_available
        )
        
        if confidence < self.confidence_threshold:
            return None
        
        # Create opportunity
        opportunity = SpatialOpportunity(
            strategy="spatial_arbitrage",
            symbol=symbol,
            amount=position_size,
            expected_profit_percent=net_profit_percent,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            spread_percent=spread_percent,
            volume_available=volume_available,
            estimated_fees=total_fees_percent * 100,
            net_profit_percent=net_profit_percent,
            confidence_score=confidence
        )
        
        logger.debug("opportunity_analyzed",
                    symbol=symbol,
                    buy_exchange=buy_exchange,
                    sell_exchange=sell_exchange,
                    spread=float(spread_percent),
                    net_profit=float(net_profit_percent),
                    confidence=confidence)
        
        return opportunity
    
    async def _get_trading_fees(self, exchange_name: str, symbol: str) -> Dict[str, Decimal]:
        """Get trading fees for exchange and symbol"""
        try:
            exchange = self.exchanges[exchange_name]
            return await exchange.get_trading_fees(symbol)
        except Exception as e:
            logger.warning("fee_fetch_failed", 
                         exchange=exchange_name, symbol=symbol, error=str(e))
            # Return default fees if fetch fails
            return {'maker': Decimal('0.001'), 'taker': Decimal('0.002')}
    
    async def _calculate_available_volume(self, buy_ticker: Ticker, sell_ticker: Ticker, 
                                        symbol: str) -> Decimal:
        """Calculate available volume for arbitrage"""
        # Use minimum of both volumes, with safety factor
        min_volume = min(buy_ticker.volume, sell_ticker.volume)
        
        # Safety factor: use only 1% of daily volume for single trade
        available_volume = min_volume * Decimal('0.01')
        
        # Also consider bid/ask sizes (would need order book for precision)
        # For now, estimate based on volume
        estimated_depth = min_volume * Decimal('0.001')  # 0.1% of daily volume
        
        return min(available_volume, estimated_depth)
    
    def _calculate_confidence_score(self, buy_ticker: Ticker, sell_ticker: Ticker, 
                                  spread_percent: Decimal, volume: Decimal) -> float:
        """Calculate confidence score for opportunity (0-1)"""
        score = 0.0
        
        # Spread size factor (higher spread = higher confidence up to a point)
        if spread_percent < 1:
            score += 0.3 * float(spread_percent)  # Linear increase up to 1%
        elif spread_percent < 3:
            score += 0.3 + 0.2 * float(spread_percent - 1) / 2  # Slower increase 1-3%
        else:
            score += 0.5  # Cap at 0.5 for very high spreads (might be stale data)
        
        # Volume factor
        if volume > 100:
            score += 0.3
        elif volume > 50:
            score += 0.2
        elif volume > 20:
            score += 0.1
        
        # Timestamp freshness (both tickers should be recent)
        import time
        current_time = time.time()
        
        for ticker in [buy_ticker, sell_ticker]:
            if ticker.timestamp and current_time - ticker.timestamp < 30:  # Within 30 seconds
                score += 0.1
        
        # Spread tightness (tighter spreads on individual exchanges = better)
        buy_spread = buy_ticker.spread if buy_ticker.spread else Decimal('1')
        sell_spread = sell_ticker.spread if sell_ticker.spread else Decimal('1')
        
        if buy_spread < Decimal('0.1') and sell_spread < Decimal('0.1'):
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    async def validate_opportunity(self, opportunity: SpatialOpportunity) -> bool:
        """Additional validation before execution"""
        try:
            # Check if exchanges are still connected
            buy_exchange = self.exchanges[opportunity.buy_exchange]
            sell_exchange = self.exchanges[opportunity.sell_exchange]
            
            if not buy_exchange.is_connected or not sell_exchange.is_connected:
                return False
            
            # Re-check current prices (opportunity might be stale)
            current_buy_ticker = await buy_exchange.get_ticker(opportunity.symbol)
            current_sell_ticker = await sell_exchange.get_ticker(opportunity.symbol)
            
            # Verify opportunity still exists with some tolerance
            current_spread = ((current_sell_ticker.bid - current_buy_ticker.ask) / 
                            current_buy_ticker.ask) * 100
            
            # Allow 20% degradation in spread
            min_acceptable_spread = opportunity.spread_percent * Decimal('0.8')
            
            if current_spread < min_acceptable_spread:
                logger.info("opportunity_stale", 
                          symbol=opportunity.symbol,
                          original_spread=float(opportunity.spread_percent),
                          current_spread=float(current_spread))
                return False
            
            # Check available balances
            if not await self._check_balances(opportunity):
                return False
            
            return True
            
        except Exception as e:
            logger.error("opportunity_validation_failed", 
                        opportunity_id=opportunity.opportunity_id, error=str(e))
            return False
    
    async def _check_balances(self, opportunity: SpatialOpportunity) -> bool:
        """Check if we have sufficient balances for the trade"""
        try:
            buy_exchange = self.exchanges[opportunity.buy_exchange]
            sell_exchange = self.exchanges[opportunity.sell_exchange]
            
            # Check buy side balance (need quote currency)
            base_asset, quote_asset = opportunity.symbol.split('/')
            
            buy_balances = await buy_exchange.get_balance(quote_asset)
            needed_quote = opportunity.amount * opportunity.buy_price * Decimal('1.01')  # 1% buffer
            
            if quote_asset not in buy_balances or buy_balances[quote_asset].free < needed_quote:
                logger.warning("insufficient_buy_balance", 
                             exchange=opportunity.buy_exchange,
                             asset=quote_asset,
                             needed=float(needed_quote),
                             available=float(buy_balances.get(quote_asset, {}).get('free', 0)))
                return False
            
            # Check sell side balance (need base currency)
            sell_balances = await sell_exchange.get_balance(base_asset)
            needed_base = opportunity.amount * Decimal('1.01')  # 1% buffer
            
            if base_asset not in sell_balances or sell_balances[base_asset].free < needed_base:
                logger.warning("insufficient_sell_balance",
                             exchange=opportunity.sell_exchange,
                             asset=base_asset,
                             needed=float(needed_base),
                             available=float(sell_balances.get(base_asset, {}).get('free', 0)))
                return False
            
            return True
            
        except Exception as e:
            logger.error("balance_check_failed", error=str(e))
            return False
    
    def get_strategy_stats(self) -> Dict[str, Any]:
        """Get strategy performance statistics"""
        return {
            'strategy_name': self.name,
            'opportunities_found': self.opportunities_found,
            'opportunities_executed': self.opportunities_executed,
            'total_profit': float(self.total_profit),
            'success_rate': (self.opportunities_executed / max(self.opportunities_found, 1)) * 100,
            'exchange_pairs': len(self.exchange_pairs),
            'trading_pairs': len(self.trading_pairs),
            'min_spread_percent': float(self.min_spread_percent)
        }
