“””
Spatial Arbitrage Strategy for SmartArb Engine
Complete implementation of cross-exchange arbitrage opportunities detection and execution
“””

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import structlog
import time

from ..exchanges.base_exchange import BaseExchange, Ticker, OrderBook
from .base_strategy import BaseStrategy, Opportunity, OpportunityType, OpportunityStatus

logger = structlog.get_logger(**name**)

@dataclass
class SpatialOpportunity(Opportunity):
“”“Spatial arbitrage opportunity data”””
buy_exchange: str
sell_exchange: str
buy_price: Decimal
sell_price: Decimal
spread_percent: Decimal
volume_available: Decimal
estimated_fees: Decimal
net_profit_percent: Decimal
confidence_score: float  # 0-1 based on liquidity, spread stability
exchanges: List[str] = None  # For compatibility with risk manager

```
def __post_init__(self):
    """Calculate additional metrics after initialization"""
    super().__post_init__()
    if not self.opportunity_id:
        self.opportunity_id = f"spatial_{self.buy_exchange}_{self.sell_exchange}_{self.symbol}_{int(self.timestamp)}"
    
    # Set exchanges list for risk manager compatibility
    if not self.exchanges:
        self.exchanges = [self.buy_exchange, self.sell_exchange]
```

class MarketDataPoint:
“”“Market data for a specific exchange and symbol”””
def **init**(self, exchange_name: str, symbol: str, ticker: Ticker, orderbook: OrderBook):
self.exchange_name = exchange_name
self.symbol = symbol
self.ticker = ticker
self.orderbook = orderbook
self.timestamp = max(ticker.timestamp, orderbook.timestamp)

```
    # Calculate additional metrics
    self.bid_depth = sum(level.amount for level in orderbook.bids[:5])  # Top 5 levels
    self.ask_depth = sum(level.amount for level in orderbook.asks[:5])
    self.spread = ticker.ask - ticker.bid
    self.spread_percent = (self.spread / ticker.ask * 100) if ticker.ask > 0 else Decimal('0')
```

class SpatialArbitrageStrategy(BaseStrategy):
“””
Spatial Arbitrage Strategy

```
Identifies price differences for the same asset across different exchanges
and executes simultaneous buy/sell orders to capture the spread.

Key considerations:
- Transaction fees on both exchanges
- Order book depth and slippage
- Transfer time between exchanges (avoided by pre-positioning)
- Exchange reliability and execution speed
- Market volatility and price stability
"""

def __init__(self, exchanges: Dict[str, BaseExchange], config: Dict[str, Any]):
    super().__init__("spatial_arbitrage", exchanges, config)
    
    # Strategy-specific configuration
    self.min_spread_percent = Decimal(str(config.get('min_spread_percent', 0.20)))
    self.max_position_size = Decimal(str(config.get('max_position_size', 1000)))
    self.min_volume_24h = Decimal(str(config.get('min_volume_24h', 1000000)))
    self.confidence_threshold = config.get('confidence_threshold', 0.7)
    self.max_slippage_percent = Decimal(str(config.get('max_slippage_percent', 0.10)))
    
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
    
    # Market data cache
    self.market_data_cache: Dict[str, Dict[str, MarketDataPoint]] = {}
    self.cache_duration = 30  # seconds
    
    # Spread tracking for trend analysis
    self.spread_history: Dict[str, List[Tuple[float, Decimal]]] = {}  # symbol -> [(timestamp, spread)]
    self.spread_history_length = 100
    
    logger.info("spatial_arbitrage_initialized",
               pairs=len(self.exchange_pairs),
               symbols=len(self.trading_pairs),
               min_spread=float(self.min_spread_percent),
               confidence_threshold=self.confidence_threshold)

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
        
        if not market_data:
            logger.warning("no_market_data_available")
            return opportunities
        
        # Analyze each trading pair across exchange pairs
        for symbol in self.trading_pairs:
            symbol_opportunities = await self._analyze_symbol_opportunities(symbol, market_data)
            opportunities.extend(symbol_opportunities)
        
        # Filter and rank opportunities
        opportunities = self._filter_and_rank_opportunities(opportunities)
        
        logger.info("spatial_opportunities_found",
                   symbol_count=len(self.trading_pairs),
                   total_opportunities=len(opportunities),
                   profitable_opportunities=len([o for o in opportunities if o.expected_profit > 0]))
        
        return opportunities
        
    except Exception as e:
        logger.error("opportunity_scanning_failed", error=str(e))
        return []

async def _fetch_market_data(self) -> Dict[str, Dict[str, MarketDataPoint]]:
    """Fetch market data from all exchanges"""
    market_data = {}
    
    # Fetch data concurrently from all exchanges
    tasks = []
    for exchange_name, exchange in self.exchanges.items():
        if exchange.is_connected:
            for symbol in self.trading_pairs:
                task = asyncio.create_task(
                    self._fetch_exchange_symbol_data(exchange_name, exchange, symbol)
                )
                tasks.append(task)
    
    # Wait for all data to be fetched
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for result in results:
        if isinstance(result, Exception):
            logger.warning("market_data_fetch_failed", error=str(result))
            continue
        
        if result:
            exchange_name, symbol, data_point = result
            if exchange_name not in market_data:
                market_data[exchange_name] = {}
            market_data[exchange_name][symbol] = data_point
    
    # Update cache
    self.market_data_cache = market_data
    
    return market_data

async def _fetch_exchange_symbol_data(self, exchange_name: str, exchange: BaseExchange, 
                                    symbol: str) -> Optional[Tuple[str, str, MarketDataPoint]]:
    """Fetch ticker and orderbook data for a specific exchange and symbol"""
    try:
        # Fetch ticker and orderbook concurrently
        ticker_task = asyncio.create_task(exchange.get_ticker(symbol))
        orderbook_task = asyncio.create_task(exchange.get_orderbook(symbol, depth=10))
        
        ticker, orderbook = await asyncio.gather(ticker_task, orderbook_task)
        
        # Create market data point
        data_point = MarketDataPoint(exchange_name, symbol, ticker, orderbook)
        
        return exchange_name, symbol, data_point
        
    except Exception as e:
        logger.warning("exchange_data_fetch_failed",
                     exchange=exchange_name,
                     symbol=symbol,
                     error=str(e))
        return None

async def _analyze_symbol_opportunities(self, symbol: str, 
                                      market_data: Dict[str, Dict[str, MarketDataPoint]]) -> List[SpatialOpportunity]:
    """Analyze arbitrage opportunities for a specific symbol"""
    opportunities = []
    
    # Get all exchanges that have data for this symbol
    available_exchanges = {}
    for exchange_name, exchange_data in market_data.items():
        if symbol in exchange_data:
            available_exchanges[exchange_name] = exchange_data[symbol]
    
    if len(available_exchanges) < 2:
        return opportunities
    
    # Compare all exchange pairs
    exchange_names = list(available_exchanges.keys())
    for i, buy_exchange in enumerate(exchange_names):
        for sell_exchange in exchange_names[i+1:]:
            
            buy_data = available_exchanges[buy_exchange]
            sell_data = available_exchanges[sell_exchange]
            
            # Analyze both directions
            opp1 = await self._analyze_exchange_pair(symbol, buy_exchange, sell_exchange, buy_data, sell_data)
            if opp1:
                opportunities.append(opp1)
            
            opp2 = await self._analyze_exchange_pair(symbol, sell_exchange, buy_exchange, sell_data, buy_data)
            if opp2:
                opportunities.append(opp2)
    
    return opportunities

async def _analyze_exchange_pair(self, symbol: str, buy_exchange: str, sell_exchange: str,
                               buy_data: MarketDataPoint, sell_data: MarketDataPoint) -> Optional[SpatialOpportunity]:
    """Analyze arbitrage opportunity between two exchanges"""
    
    try:
        # Get best prices
        buy_price = buy_data.ticker.ask  # We buy at ask price
        sell_price = sell_data.ticker.bid  # We sell at bid price
        
        if buy_price <= 0 or sell_price <= 0:
            return None
        
        # Calculate spread
        spread = sell_price - buy_price
        spread_percent = (spread / buy_price) * 100
        
        # Check minimum spread requirement
        if spread_percent < self.min_spread_percent:
            return None
        
        # Calculate available volume (limited by order book depth)
        max_buy_volume = self._calculate_max_volume(buy_data.orderbook.asks, buy_price)
        max_sell_volume = self._calculate_max_volume(sell_data.orderbook.bids, sell_price)
        available_volume = min(max_buy_volume, max_sell_volume, self.max_position_size)
        
        if available_volume <= 0:
            return None
        
        # Calculate fees
        buy_fee = await self._get_trading_fee(buy_exchange, symbol, is_taker=True)
        sell_fee = await self._get_trading_fee(sell_exchange, symbol, is_taker=True)
        
        trade_value = available_volume * buy_price
        estimated_fees = trade_value * (buy_fee + sell_fee)
        
        # Calculate net profit
        gross_profit = available_volume * spread
        net_profit = gross_profit - estimated_fees
        net_profit_percent = (net_profit / trade_value) * 100
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            symbol, buy_data, sell_data, spread_percent, available_volume
        )
        
        # Check if opportunity is profitable after fees
        if net_profit <= 0 or confidence_score < self.confidence_threshold:
            return None
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(buy_data, sell_data, spread_percent)
        
        # Create opportunity
        opportunity = SpatialOpportunity(
            opportunity_type=OpportunityType.SPATIAL_ARBITRAGE,
            symbol=symbol,
            amount=available_volume,
            expected_profit=net_profit,
            expected_profit_percent=net_profit_percent,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            buy_price=buy_price,
            sell_price=sell_price,
            spread_percent=spread_percent,
            volume_available=available_volume,
            estimated_fees=estimated_fees,
            net_profit_percent=net_profit_percent,
            confidence_score=confidence_score,
            risk_score=float(risk_score),
            confidence_level=confidence_score,
            timestamp=time.time(),
            valid_until=time.time() + 60  # Valid for 60 seconds
        )
        
        # Update spread history for trend analysis
        self._update_spread_history(symbol, spread_percent)
        
        logger.debug("spatial_opportunity_detected",
                    symbol=symbol,
                    buy_exchange=buy_exchange,
                    sell_exchange=sell_exchange,
                    spread_percent=float(spread_percent),
                    net_profit=float(net_profit),
                    confidence=confidence_score)
        
        return opportunity
        
    except Exception as e:
        logger.error("opportunity_analysis_failed",
                    symbol=symbol,
                    buy_exchange=buy_exchange,
                    sell_exchange=sell_exchange,
                    error=str(e))
        return None

def _calculate_max_volume(self, orderbook_levels: List, target_price: Decimal) -> Decimal:
    """Calculate maximum volume available at or better than target price"""
    max_volume = Decimal('0')
    
    for level in orderbook_levels:
        # For asks (buying): level price should be <= target price
        # For bids (selling): level price should be >= target price
        if len(orderbook_levels) > 0 and hasattr(orderbook_levels[0], 'price'):
            # This is an ask book if we're checking against ask price
            if target_price >= level.price:
                max_volume += level.amount
            else:
                break
        else:
            # This is a bid book if we're checking against bid price
            if target_price <= level.price:
                max_volume += level.amount
            else:
                break
    
    return max_volume

async def _get_trading_fee(self, exchange_name: str, symbol: str, is_taker: bool = True) -> Decimal:
    """Get trading fee for exchange and symbol"""
    try:
        exchange = self.exchanges.get(exchange_name)
        if exchange:
            fees = await exchange.get_trading_fees(symbol)
            return fees.get('taker' if is_taker else 'maker', exchange.taker_fee if is_taker else exchange.maker_fee)
        else:
            # Default fee if exchange not available
            return Decimal('0.001')  # 0.1%
            
    except Exception as e:
        logger.warning("fee_fetch_failed",
                     exchange=exchange_name,
                     symbol=symbol,
                     error=str(e))
        return Decimal('0.001')  # Default fee

def _calculate_confidence_score(self, symbol: str, buy_data: MarketDataPoint, 
                              sell_data: MarketDataPoint, spread_percent: Decimal, 
                              volume: Decimal) -> float:
    """Calculate confidence score for the opportunity"""
    
    confidence = 1.0
    
    # Factor 1: Data freshness (reduce confidence for stale data)
    now = time.time()
    buy_age = now - buy_data.timestamp
    sell_age = now - sell_data.timestamp
    max_age = max(buy_age, sell_age)
    
    if max_age > 30:  # Data older than 30 seconds
        confidence *= 0.8
    elif max_age > 10:  # Data older than 10 seconds
        confidence *= 0.9
    
    # Factor 2: Order book depth (higher depth = higher confidence)
    min_depth = min(buy_data.bid_depth, sell_data.ask_depth)
    if min_depth < volume * 2:  # Thin order book
        confidence *= 0.7
    elif min_depth < volume * 5:
        confidence *= 0.9
    
    # Factor 3: Spread size (very large spreads might be stale data)
    if spread_percent > 2.0:  # Spread larger than 2%
        confidence *= 0.6
    elif spread_percent > 1.0:  # Spread larger than 1%
        confidence *= 0.8
    
    # Factor 4: Exchange spread consistency
    buy_spread_percent = float(buy_data.spread_percent)
    sell_spread_percent = float(sell_data.spread_percent)
    
    if buy_spread_percent > 0.5 or sell_spread_percent > 0.5:  # Wide spreads
        confidence *= 0.8
    
    # Factor 5: Historical spread stability
    spread_stability = self._get_spread_stability(symbol)
    confidence *= spread_stability
    
    return max(0.0, min(1.0, confidence))

def _calculate_risk_score(self, buy_data: MarketDataPoint, sell_data: MarketDataPoint, 
                        spread_percent: Decimal) -> Decimal:
    """Calculate risk score for the opportunity"""
    
    risk_score = Decimal('0.1')  # Base risk
    
    # Factor 1: Exchange reliability (would be passed from risk manager)
    # For now, use basic heuristics
    
    # Factor 2: Market volatility
    if spread_percent > 1.0:  # High spread might indicate volatility
        risk_score += Decimal('0.2')
    
    # Factor 3: Order book depth
    min_depth = min(buy_data.bid_depth, sell_data.ask_depth)
    if min_depth < 100:  # Thin books increase risk
        risk_score += Decimal('0.3')
    
    # Factor 4: Data staleness
    now = time.time()
    max_age = max(now - buy_data.timestamp, now - sell_data.timestamp)
    if max_age > 10:
        risk_score += Decimal('0.2')
    
    return min(Decimal('1.0'), risk_score)

def _update_spread_history(self, symbol: str, spread_percent: Decimal) -> None:
    """Update spread history for trend analysis"""
    now = time.time()
    
    if symbol not in self.spread_history:
        self.spread_history[symbol] = []
    
    history = self.spread_history[symbol]
    history.append((now, spread_percent))
    
    # Keep only recent history
    cutoff_time = now - 3600  # 1 hour
    self.spread_history[symbol] = [
        (ts, spread) for ts, spread in history 
        if ts > cutoff_time
    ][-self.spread_history_length:]

def _get_spread_stability(self, symbol: str) -> float:
    """Get spread stability score (higher = more stable)"""
    if symbol not in self.spread_history or len(self.spread_history[symbol]) < 10:
        return 0.7  # Default moderate stability
    
    history = self.spread_history[symbol]
    spreads = [float(spread) for _, spread in history[-20:]]  # Last 20 data points
    
    if len(spreads) < 5:
        return 0.7
    
    # Calculate coefficient of variation (std dev / mean)
    mean_spread = sum(spreads) / len(spreads)
    if mean_spread == 0:
        return 0.5
    
    variance = sum((s - mean_spread) ** 2 for s in spreads) / len(spreads)
    std_dev = variance ** 0.5
    cv = std_dev / mean_spread
    
    # Convert to stability score (lower CV = higher stability)
    if cv < 0.1:
        return 1.0
    elif cv < 0.3:
        return 0.9
    elif cv < 0.5:
        return 0.7
    else:
        return 0.5

def _filter_and_rank_opportunities(self, opportunities: List[SpatialOpportunity]) -> List[SpatialOpportunity]:
    """Filter and rank opportunities by profitability and confidence"""
    
    # Filter by minimum requirements
    filtered = []
    for opp in opportunities:
        if (opp.net_profit_percent >= self.min_spread_percent and
            opp.confidence_score >= self.confidence_threshold and
            opp.expected_profit > 0):
            filtered.append(opp)
    
    # Sort by expected profit (descending)
    filtered.sort(key=lambda o: float(o.expected_profit), reverse=True)
    
    # Limit to top opportunities to avoid overwhelming the system
    return filtered[:10]

async def validate_opportunity(self, opportunity: Opportunity) -> bool:
    """Validate an opportunity before execution"""
    
    if not isinstance(opportunity, SpatialOpportunity):
        return False
    
    try:
        # Check if opportunity has expired
        if opportunity.is_expired:
            logger.debug("opportunity_expired", opportunity_id=opportunity.opportunity_id)
            return False
        
        # Check if exchanges are still connected
        buy_exchange = self.exchanges.get(opportunity.buy_exchange)
        sell_exchange = self.exchanges.get(opportunity.sell_exchange)
        
        if not buy_exchange or not sell_exchange:
            logger.warning("exchange_not_available",
                         opportunity_id=opportunity.opportunity_id,
                         buy_exchange=opportunity.buy_exchange,
                         sell_exchange=opportunity.sell_exchange)
            return False
        
        if not buy_exchange.is_connected or not sell_exchange.is_connected:
            logger.warning("exchange_not_connected",
                         opportunity_id=opportunity.opportunity_id,
                         buy_connected=buy_exchange.is_connected,
                         sell_connected=sell_exchange.is_connected)
            return False
        
        # Check current prices (quick validation)
        try:
            buy_ticker = await buy_exchange.get_ticker(opportunity.symbol)
            sell_ticker = await sell_exchange.get_ticker(opportunity.symbol)
            
            # Check if prices are still favorable
            current_spread = sell_ticker.bid - buy_ticker.ask
            current_spread_percent = (current_spread / buy_ticker.ask) * 100
            
            if current_spread_percent < self.min_spread_percent:
                logger.debug("spread_no_longer_profitable",
                           opportunity_id=opportunity.opportunity_id,
                           current_spread=float(current_spread_percent),
                           required_spread=float(self.min_spread_percent))
                return False
            
        except Exception as e:
            logger.warning("price_validation_failed",
                         opportunity_id=opportunity.opportunity_id,
                         error=str(e))
            return False
        
        # Check balances
        if not await self._check_balance_sufficiency(opportunity, buy_exchange, sell_exchange):
            return False
        
        return True
        
    except Exception as e:
        logger.error("opportunity_validation_failed",
                    opportunity_id=opportunity.opportunity_id,
                    error=str(e))
        return False

async def _check_balance_sufficiency(self, opportunity: SpatialOpportunity, 
                                   buy_exchange: BaseExchange, 
                                   sell_exchange: BaseExchange) -> bool:
    """Check if exchanges have sufficient balance for the arbitrage"""
    
    try:
        base_asset, quote_asset = opportunity.symbol.split('/')
        
        # Check buy exchange balance (need quote currency)
        buy_balances = await buy_exchange.get_balance(quote_asset)
        needed_quote = opportunity.amount * opportunity.buy_price * Decimal('1.01')  # 1% buffer
        
        if quote_asset not in buy_balances or buy_balances[quote_asset].free < needed_quote:
            logger.warning("insufficient_buy_balance", 
                         exchange=opportunity.buy_exchange,
                         asset=quote_asset,
                         needed=float(needed_quote),
                         available=float(buy_balances.get(quote_asset, Balance(quote_asset, Decimal('0'), Decimal('0'))).free))
            return False
        
        # Check sell exchange balance (need base currency)
        sell_balances = await sell_exchange.get_balance(base_asset)
        needed_base = opportunity.amount * Decimal('1.01')  # 1% buffer
        
        if base_asset not in sell_balances or sell_balances[base_asset].free < needed_base:
            logger.warning("insufficient_sell_balance",
                         exchange=opportunity.sell_exchange,
                         asset=base_asset,
                         needed=float(needed_base),
                         available=float(sell_balances.get(base_asset, Balance(base_asset, Decimal('0'), Decimal('0'))).free))
            return False
        
        return True
        
    except Exception as e:
        logger.error("balance_check_failed", 
                    opportunity_id=opportunity.opportunity_id,
                    error=str(e))
        return False

async def estimate_profit(self, opportunity: Opportunity) -> Decimal:
    """Estimate potential profit for an opportunity"""
    
    if isinstance(opportunity, SpatialOpportunity):
        return opportunity.expected_profit
    
    # For other opportunity types, return 0
    return Decimal('0')

def get_strategy_stats(self) -> Dict[str, Any]:
    """Get strategy performance statistics"""
    
    success_rate = 0.0
    if self.opportunities_found > 0:
        success_rate = (self.opportunities_executed / self.opportunities_found) * 100
    
    avg_profit_per_trade = 0.0
    if self.opportunities_executed > 0:
        avg_profit_per_trade = float(self.total_profit / self.opportunities_executed)
    
    return {
        'strategy_name': self.name,
        'opportunities_found': self.opportunities_found,
        'opportunities_executed': self.opportunities_executed,
        'total_profit': float(self.total_profit),
        'success_rate': success_rate,
        'avg_profit_per_trade': avg_profit_per_trade,
        'exchange_pairs': len(self.exchange_pairs),
        'trading_pairs': len(self.trading_pairs),
        'min_spread_percent': float(self.min_spread_percent),
        'confidence_threshold': self.confidence_threshold,
        'max_position_size': float(self.max_position_size),
        'cached_symbols': len(self.market_data_cache),
        'spread_histories': len(self.spread_history)
    }

def update_strategy_config(self, new_config: Dict[str, Any]) -> None:
    """Update strategy configuration dynamically"""
    
    old_config = self.get_config()
    super().update_config(new_config)
    
    # Update spatial arbitrage specific settings
    if 'min_spread_percent' in new_config:
        self.min_spread_percent = Decimal(str(new_config['min_spread_percent']))
    
    if 'max_position_size' in new_config:
        self.max_position_size = Decimal(str(new_config['max_position_size']))
    
    if 'confidence_threshold' in new_config:
        self.confidence_threshold = float(new_config['confidence_threshold'])
    
    if 'trading_pairs' in new_config:
        self.trading_pairs = new_config['trading_pairs']
        # Clear cache when trading pairs change
        self.market_data_cache.clear()
    
    logger.info("spatial_arbitrage_config_updated",
               old_min_spread=float(old_config.get('min_spread_percent', 0)),
               new_min_spread=float(self.min_spread_percent),
               old_confidence=old_config.get('confidence_threshold', 0),
               new_confidence=self.confidence_threshold)

def get_market_data_summary(self) -> Dict[str, Any]:
    """Get summary of current market data"""
    
    summary = {
        'last_update': 0,
        'exchanges_online': 0,
        'symbols_tracked': len(self.trading_pairs),
        'total_data_points': 0,
        'avg_spread_by_symbol': {},
        'exchange_status': {}
    }
    
    if not self.market_data_cache:
        return summary
    
    # Calculate summary statistics
    last_update = 0
    total_data_points = 0
    spread_by_symbol = {}
    
    for exchange_name, exchange_data in self.market_data_cache.items():
        summary['exchange_status'][exchange_name] = {
            'symbols': len(exchange_data),
            'online': exchange_name in self.exchanges and self.exchanges[exchange_name].is_connected
        }
        
        if summary['exchange_status'][exchange_name]['online']:
            summary['exchanges_online'] += 1
        
        for symbol, data_point in exchange_data.items():
            total_data_points += 1
            last_update = max(last_update, data_point.timestamp)
            
            if symbol not in spread_by_symbol:
                spread_by_symbol[symbol] = []
            spread_by_symbol[symbol].append(float(data_point.spread_percent))
    
    summary['last_update'] = last_update
    summary['total_data_points'] = total_data_points
    
    # Calculate average spreads
    for symbol, spreads in spread_by_symbol.items():
        if spreads:
            summary['avg_spread_by_symbol'][symbol] = sum(spreads) / len(spreads)
    
    return summary
```