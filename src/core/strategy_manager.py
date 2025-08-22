#!/usr/bin/env python3
“””
Strategy Manager for SmartArb Engine
Manages and executes arbitrage trading strategies
“””

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import structlog
import time
from datetime import datetime, timedelta
import statistics

from ..exchanges.base_exchange import BaseExchange, OrderBook, Ticker
from .risk_manager import RiskManager
from .execution_engine import ExecutionEngine

logger = structlog.get_logger(**name**)

class StrategyType(Enum):
“”“Strategy type enumeration”””
SPATIAL_ARBITRAGE = “spatial_arbitrage”
TRIANGULAR_ARBITRAGE = “triangular_arbitrage”
STATISTICAL_ARBITRAGE = “statistical_arbitrage”

class OpportunityStatus(Enum):
“”“Opportunity status enumeration”””
DETECTED = “detected”
ANALYZING = “analyzing”
APPROVED = “approved”
EXECUTING = “executing”
COMPLETED = “completed”
FAILED = “failed”
REJECTED = “rejected”

@dataclass
class ArbitrageOpportunity:
“”“Arbitrage opportunity data structure”””
id: str
strategy_type: StrategyType
symbol: str
buy_exchange: str
sell_exchange: str
buy_price: Decimal
sell_price: Decimal
spread: Decimal
spread_percentage: Decimal
potential_profit: Decimal
required_capital: Decimal
confidence: float
risk_score: float
status: OpportunityStatus
detected_time: float
expiry_time: float

```
@property
def is_expired(self) -> bool:
    """Check if opportunity has expired"""
    return time.time() > self.expiry_time

@property
def time_remaining(self) -> float:
    """Get time remaining before expiry"""
    return max(0, self.expiry_time - time.time())
```

class SpatialArbitrageStrategy:
“”“Spatial arbitrage strategy implementation”””

```
def __init__(self, exchanges: Dict[str, BaseExchange], config: Dict[str, Any]):
    self.exchanges = exchanges
    self.config = config.get('strategies', {}).get('spatial_arbitrage', {})
    self.enabled = self.config.get('enabled', True)
    
    # Strategy parameters
    self.min_spread_percent = Decimal(str(self.config.get('min_spread_percent', 0.2)))
    self.max_position_size = Decimal(str(self.config.get('max_position_size', 1000)))
    self.confidence_threshold = self.config.get('confidence_threshold', 0.7)
    self.opportunity_ttl = self.config.get('opportunity_ttl_seconds', 30)
    
    # Exchange preferences
    self.preferred_pairs = self.config.get('preferred_pairs', [])
    self.trading_pairs = set(self.config.get('trading_pairs', []))
    
    # Opportunity tracking
    self.active_opportunities = {}
    self.opportunity_history = []
    
    self.logger = structlog.get_logger("strategy.spatial_arbitrage")

async def scan_opportunities(self) -> List[ArbitrageOpportunity]:
    """Scan for spatial arbitrage opportunities"""
    opportunities = []
    
    if not self.enabled:
        return opportunities
    
    try:
        # Get all tickers from all exchanges
        exchange_tickers = {}
        
        for exchange_name, exchange in self.exchanges.items():
            if not exchange.connected:
                continue
            
            exchange_tickers[exchange_name] = {}
            
            for symbol in self.trading_pairs:
                try:
                    ticker = await exchange.get_ticker(symbol)
                    exchange_tickers[exchange_name][symbol] = ticker
                except Exception as e:
                    self.logger.warning("ticker_fetch_failed",
                                      exchange=exchange_name,
                                      symbol=symbol,
                                      error=str(e))
        
        # Compare prices across exchanges
        for symbol in self.trading_pairs:
            symbol_opportunities = await self._analyze_symbol_opportunities(
                symbol, exchange_tickers
            )
            opportunities.extend(symbol_opportunities)
        
        # Filter and rank opportunities
        opportunities = self._filter_opportunities(opportunities)
        opportunities = self._rank_opportunities(opportunities)
        
        self.logger.info("opportunities_scanned",
                       total_found=len(opportunities),
                       symbol_count=len(self.trading_pairs))
        
        return opportunities
        
    except Exception as e:
        self.logger.error("opportunity_scan_failed", error=str(e))
        return []

async def _analyze_symbol_opportunities(self, symbol: str, 
                                      exchange_tickers: Dict[str, Dict[str, Ticker]]) -> List[ArbitrageOpportunity]:
    """Analyze opportunities for a specific symbol"""
    opportunities = []
    
    # Get all exchange prices for this symbol
    symbol_prices = {}
    for exchange_name, tickers in exchange_tickers.items():
        if symbol in tickers:
            ticker = tickers[symbol]
            symbol_prices[exchange_name] = {
                'bid': ticker.bid,
                'ask': ticker.ask,
                'timestamp': ticker.timestamp
            }
    
    if len(symbol_prices) < 2:
        return opportunities
    
    # Find arbitrage opportunities
    exchange_names = list(symbol_prices.keys())
    
    for i in range(len(exchange_names)):
        for j in range(i + 1, len(exchange_names)):
            buy_exchange = exchange_names[i]
            sell_exchange = exchange_names[j]
            
            # Check both directions
            opp1 = await self._calculate_opportunity(
                symbol, buy_exchange, sell_exchange, symbol_prices
            )
            if opp1:
                opportunities.append(opp1)
            
            opp2 = await self._calculate_opportunity(
                symbol, sell_exchange, buy_exchange, symbol_prices
            )
            if opp2:
                opportunities.append(opp2)
    
    return opportunities

async def _calculate_opportunity(self, symbol: str, buy_exchange: str, 
                               sell_exchange: str, symbol_prices: Dict[str, Dict]) -> Optional[ArbitrageOpportunity]:
    """Calculate arbitrage opportunity between two exchanges"""
    
    buy_price = symbol_prices[buy_exchange]['ask']  # We buy at ask price
    sell_price = symbol_prices[sell_exchange]['bid']  # We sell at bid price
    
    # Calculate spread
    spread = sell_price - buy_price
    spread_percentage = (spread / buy_price) * 100
    
    # Check if spread meets minimum threshold
    if spread_percentage < self.min_spread_percent:
        return None
    
    # Calculate potential profit (considering fees)
    buy_fee_rate = self._get_trading_fee(buy_exchange, 'taker')
    sell_fee_rate = self._get_trading_fee(sell_exchange, 'taker')
    
    # Estimate trade size (conservative approach)
    max_trade_size = min(
        self.max_position_size / buy_price,  # Based on position limit
        self._estimate_max_trade_size(symbol, buy_exchange, sell_exchange)
    )
    
    # Calculate costs and profit
    buy_cost = buy_price * max_trade_size
    buy_fee = buy_cost * buy_fee_rate
    
    sell_revenue = sell_price * max_trade_size
    sell_fee = sell_revenue * sell_fee_rate
    
    total_cost = buy_cost + buy_fee + sell_fee
    net_profit = sell_revenue - total_cost
    profit_percentage = (net_profit / total_cost) * 100
    
    # Skip if not profitable after fees
    if net_profit <= 0:
        return None
    
    # Calculate confidence and risk score
    confidence = self._calculate_confidence(symbol, buy_exchange, sell_exchange, symbol_prices)
    risk_score = self._calculate_risk_score(symbol, spread_percentage, max_trade_size)
    
    # Generate opportunity ID
    opportunity_id = f"{symbol}_{buy_exchange}_{sell_exchange}_{int(time.time())}"
    
    return ArbitrageOpportunity(
        id=opportunity_id,
        strategy_type=StrategyType.SPATIAL_ARBITRAGE,
        symbol=symbol,
        buy_exchange=buy_exchange,
        sell_exchange=sell_exchange,
        buy_price=buy_price,
        sell_price=sell_price,
        spread=spread,
        spread_percentage=spread_percentage,
        potential_profit=net_profit,
        required_capital=total_cost,
        confidence=confidence,
        risk_score=risk_score,
        status=OpportunityStatus.DETECTED,
        detected_time=time.time(),
        expiry_time=time.time() + self.opportunity_ttl
    )

def _get_trading_fee(self, exchange_name: str, order_type: str) -> Decimal:
    """Get trading fee for exchange"""
    exchange_config = self.config.get('exchanges', {}).get(exchange_name, {})
    
    if order_type == 'maker':
        return Decimal(str(exchange_config.get('maker_fee', 0.001)))
    else:
        return Decimal(str(exchange_config.get('taker_fee', 0.001)))

def _estimate_max_trade_size(self, symbol: str, buy_exchange: str, sell_exchange: str) -> Decimal:
    """Estimate maximum safe trade size based on order book depth"""
    # This is a simplified implementation
    # In practice, you'd analyze order book depth on both exchanges
    return Decimal('1.0')  # Conservative default

def _calculate_confidence(self, symbol: str, buy_exchange: str, sell_exchange: str, 
                        symbol_prices: Dict[str, Dict]) -> float:
    """Calculate confidence score for opportunity"""
    # Factors that affect confidence:
    # 1. Price data freshness
    # 2. Exchange reliability
    # 3. Historical success rate
    # 4. Market volatility
    
    current_time = time.time()
    confidence = 1.0
    
    # Price data freshness
    for exchange_name in [buy_exchange, sell_exchange]:
        price_age = current_time - symbol_prices[exchange_name]['timestamp']
        if price_age > 10:  # 10 seconds
            confidence *= 0.8
        elif price_age > 5:  # 5 seconds
            confidence *= 0.9
    
    # Exchange preference
    preferred_exchanges = {pair[0], pair[1] for pair in self.preferred_pairs}
    if buy_exchange in preferred_exchanges and sell_exchange in preferred_exchanges:
        confidence *= 1.1
    
    return min(confidence, 1.0)

def _calculate_risk_score(self, symbol: str, spread_percentage: Decimal, trade_size: Decimal) -> float:
    """Calculate risk score for opportunity"""
    # Lower score = lower risk
    risk_score = 0.5  # Base risk
    
    # Higher spreads are generally safer
    if spread_percentage > 1.0:
        risk_score *= 0.8
    elif spread_percentage < 0.3:
        risk_score *= 1.2
    
    # Larger trades are riskier
    if trade_size > Decimal('10'):
        risk_score *= 1.1
    
    return min(risk_score, 1.0)

def _filter_opportunities(self, opportunities: List[ArbitrageOpportunity]) -> List[ArbitrageOpportunity]:
    """Filter opportunities based on criteria"""
    filtered = []
    
    for opp in opportunities:
        # Check confidence threshold
        if opp.confidence < self.confidence_threshold:
            continue
        
        # Check if opportunity already exists
        if self._is_duplicate_opportunity(opp):
            continue
        
        # Check exchange pair preferences
        if not self._is_preferred_exchange_pair(opp.buy_exchange, opp.sell_exchange):
            continue
        
        filtered.append(opp)
    
    return filtered

def _rank_opportunities(self, opportunities: List[ArbitrageOpportunity]) -> List[ArbitrageOpportunity]:
    """Rank opportunities by attractiveness"""
    # Sort by a composite score considering profit, confidence, and risk
    def score_opportunity(opp: ArbitrageOpportunity) -> float:
        profit_score = float(opp.potential_profit)
        confidence_score = opp.confidence * 100
        risk_penalty = opp.risk_score * 50
        
        return profit_score + confidence_score - risk_penalty
    
    return sorted(opportunities, key=score_opportunity, reverse=True)

def _is_duplicate_opportunity(self, opportunity: ArbitrageOpportunity) -> bool:
    """Check if similar opportunity already exists"""
    for existing_opp in self.active_opportunities.values():
        if (existing_opp.symbol == opportunity.symbol and
            existing_opp.buy_exchange == opportunity.buy_exchange and
            existing_opp.sell_exchange == opportunity.sell_exchange and
            not existing_opp.is_expired):
            return True
    return False

def _is_preferred_exchange_pair(self, exchange1: str, exchange2: str) -> bool:
    """Check if exchange pair is in preferences"""
    if not self.preferred_pairs:
        return True  # No preferences set, allow all
    
    for pair in self.preferred_pairs:
        if (exchange1 in pair and exchange2 in pair):
            return True
    
    return False
```

class StrategyManager:
“”“Main strategy manager orchestrating all trading strategies”””

```
def __init__(self, exchanges: Dict[str, BaseExchange], 
             risk_manager: RiskManager, 
             execution_engine: ExecutionEngine,
             config: Dict[str, Any]):
    
    self.exchanges = exchanges
    self.risk_manager = risk_manager
    self.execution_engine = execution_engine
    self.config = config
    
    # Initialize strategies
    self.strategies = {}
    self._initialize_strategies()
    
    # Opportunity management
    self.active_opportunities = {}
    self.opportunity_queue = asyncio.Queue()
    
    # Strategy execution
    self.running = False
    self.scan_interval = config.get('strategies', {}).get('scan_frequency', 5)
    
    # Performance tracking
    self.total_opportunities_found = 0
    self.successful_trades = 0
    self.failed_trades = 0
    
    self.logger = structlog.get_logger("strategy_manager")

def _initialize_strategies(self):
    """Initialize all enabled strategies"""
    strategies_config = self.config.get('strategies', {})
    
    # Spatial arbitrage strategy
    if strategies_config.get('spatial_arbitrage', {}).get('enabled', False):
        self.strategies['spatial_arbitrage'] = SpatialArbitrageStrategy(
            self.exchanges, self.config
        )
        self.logger.info("spatial_arbitrage_strategy_initialized")
    
    # Future strategies can be added here
    # if strategies_config.get('triangular_arbitrage', {}).get('enabled', False):
    #     self.strategies['triangular_arbitrage'] = TriangularArbitrageStrategy(...)
    
    self.logger.info("strategy_manager_initialized", 
                    active_strategies=list(self.strategies.keys()))

async def start(self):
    """Start strategy manager"""
    if self.running:
        return
    
    self.running = True
    self.logger.info("strategy_manager_starting")
    
    # Start opportunity scanning
    scan_task = asyncio.create_task(self._opportunity_scanner())
    
    # Start opportunity processor
    processor_task = asyncio.create_task(self._opportunity_processor())
    
    try:
        await asyncio.gather(scan_task, processor_task)
    except asyncio.CancelledError:
        self.logger.info("strategy_manager_cancelled")
    except Exception as e:
        self.logger.error("strategy_manager_error", error=str(e))
    finally:
        self.running = False

async def stop(self):
    """Stop strategy manager"""
    self.running = False
    self.logger.info("strategy_manager_stopping")

async def _opportunity_scanner(self):
    """Continuously scan for opportunities"""
    while self.running:
        try:
            start_time = time.time()
            
            # Scan all strategies for opportunities
            all_opportunities = []
            
            for strategy_name, strategy in self.strategies.items():
                if hasattr(strategy, 'scan_opportunities'):
                    opportunities = await strategy.scan_opportunities()
                    all_opportunities.extend(opportunities)
            
            # Add opportunities to queue
            for opportunity in all_opportunities:
                await self.opportunity_queue.put(opportunity)
                self.total_opportunities_found += 1
            
            scan_duration = time.time() - start_time
            
            self.logger.info("opportunity_scan_completed",
                           opportunities_found=len(all_opportunities),
                           scan_duration=scan_duration)
            
            # Wait before next scan
            await asyncio.sleep(self.scan_interval)
            
        except Exception as e:
            self.logger.error("opportunity_scan_error", error=str(e))
            await asyncio.sleep(self.scan_interval)

async def _opportunity_processor(self):
    """Process detected opportunities"""
    while self.running:
        try:
            # Wait for opportunity
            opportunity = await asyncio.wait_for(
                self.opportunity_queue.get(), 
                timeout=1.0
            )
            
            # Process opportunity
            await self._process_opportunity(opportunity)
            
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            self.logger.error("opportunity_processing_error", error=str(e))

async def _process_opportunity(self, opportunity: ArbitrageOpportunity):
    """Process a single arbitrage opportunity"""
    try:
        # Check if opportunity is still valid
        if opportunity.is_expired:
            self.logger.debug("opportunity_expired", opportunity_id=opportunity.id)
            return
        
        opportunity.status = OpportunityStatus.ANALYZING
        
        # Risk assessment
        risk_assessment = await self.risk_manager.assess_opportunity(opportunity)
        
        if not risk_assessment['approved']:
            opportunity.status = OpportunityStatus.REJECTED
            self.logger.info("opportunity_rejected", 
                           opportunity_id=opportunity.id,
                           reason=risk_assessment['reason'])
            return
        
        opportunity.status = OpportunityStatus.APPROVED
        
        # Execute opportunity
        opportunity.status = OpportunityStatus.EXECUTING
        
        execution_result = await self.execution_engine.execute_arbitrage(opportunity)
        
        if execution_result['success']:
            opportunity.status = OpportunityStatus.COMPLETED
            self.successful_trades += 1
            self.logger.info("opportunity_executed_successfully",
                           opportunity_id=opportunity.id,
                           profit=execution_result.get('actual_profit'))
        else:
            opportunity.status = OpportunityStatus.FAILED
            self.failed_trades += 1
            self.logger.warning("opportunity_execution_failed",
                              opportunity_id=opportunity.id,
                              error=execution_result.get('error'))
        
    except Exception as e:
        opportunity.status = OpportunityStatus.FAILED
        self.failed_trades += 1
        self.logger.error("opportunity_processing_failed",
                        opportunity_id=opportunity.id,
                        error=str(e))

def get_status(self) -> Dict[str, Any]:
    """Get strategy manager status"""
    return {
        'running': self.running,
        'active_strategies': list(self.strategies.keys()),
        'total_opportunities_found': self.total_opportunities_found,
        'successful_trades': self.successful_trades,
        'failed_trades': self.failed_trades,
        'success_rate': (self.successful_trades / max(self.successful_trades + self.failed_trades, 1)) * 100,
        'active_opportunities': len(self.active_opportunities)
    }
```