#!/usr/bin/env python3
“””
Risk Management System for SmartArb Engine
Comprehensive risk management with multiple safety layers and real-time monitoring
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
import json

from ..exchanges.base_exchange import BaseExchange

logger = structlog.get_logger(**name**)

class RiskLevel(Enum):
“”“Risk level enumeration”””
LOW = “low”
MEDIUM = “medium”
HIGH = “high”
CRITICAL = “critical”

class RiskType(Enum):
“”“Risk type enumeration”””
MARKET_RISK = “market_risk”
LIQUIDITY_RISK = “liquidity_risk”
COUNTERPARTY_RISK = “counterparty_risk”
OPERATIONAL_RISK = “operational_risk”
CONCENTRATION_RISK = “concentration_risk”
VOLATILITY_RISK = “volatility_risk”

@dataclass
class RiskMetric:
“”“Risk metric data structure”””
name: str
value: float
threshold: float
level: RiskLevel
description: str
timestamp: float

@dataclass
class RiskAssessment:
“”“Risk assessment result”””
approved: bool
overall_risk_score: float
risk_level: RiskLevel
risk_metrics: List[RiskMetric]
warnings: List[str]
blockers: List[str]
reason: str
timestamp: float

class CircuitBreaker:
“”“Circuit breaker for emergency stops”””

```
def __init__(self, config: Dict[str, Any]):
    self.enabled = config.get('enabled', True)
    self.loss_threshold = Decimal(str(config.get('loss_threshold', -100)))  # USDT
    self.lookback_minutes = config.get('lookback_minutes', 60)
    self.cooldown_minutes = config.get('cooldown_minutes', 30)
    
    self.triggered = False
    self.trigger_time = None
    self.total_loss = Decimal('0')
    self.trade_history = []
    
    self.logger = structlog.get_logger("risk.circuit_breaker")

def add_trade_result(self, profit_loss: Decimal):
    """Add trade result for monitoring"""
    current_time = time.time()
    
    self.trade_history.append({
        'timestamp': current_time,
        'profit_loss': profit_loss
    })
    
    # Clean old trades outside lookback window
    cutoff_time = current_time - (self.lookback_minutes * 60)
    self.trade_history = [
        trade for trade in self.trade_history 
        if trade['timestamp'] > cutoff_time
    ]
    
    # Calculate total loss in lookback period
    self.total_loss = sum(
        trade['profit_loss'] for trade in self.trade_history
    )
    
    # Check if circuit breaker should trigger
    if self.enabled and self.total_loss <= self.loss_threshold and not self.triggered:
        self.trigger()

def trigger(self):
    """Trigger circuit breaker"""
    self.triggered = True
    self.trigger_time = time.time()
    
    self.logger.critical("circuit_breaker_triggered",
                       total_loss=float(self.total_loss),
                       threshold=float(self.loss_threshold),
                       lookback_minutes=self.lookback_minutes)

def reset(self):
    """Reset circuit breaker manually"""
    self.triggered = False
    self.trigger_time = None
    self.total_loss = Decimal('0')
    self.trade_history = []
    
    self.logger.info("circuit_breaker_reset")

def can_trade(self) -> bool:
    """Check if trading is allowed"""
    if not self.triggered:
        return True
    
    # Check if cooldown period has passed
    if self.trigger_time and time.time() - self.trigger_time > (self.cooldown_minutes * 60):
        self.logger.info("circuit_breaker_cooldown_expired")
        self.triggered = False
        self.trigger_time = None
        return True
    
    return False

def get_status(self) -> Dict[str, Any]:
    """Get circuit breaker status"""
    return {
        'enabled': self.enabled,
        'triggered': self.triggered,
        'trigger_time': self.trigger_time,
        'total_loss': float(self.total_loss),
        'loss_threshold': float(self.loss_threshold),
        'trades_in_window': len(self.trade_history),
        'can_trade': self.can_trade()
    }
```

class PositionSizeCalculator:
“”“Calculate optimal position sizes based on risk parameters”””

```
def __init__(self, config: Dict[str, Any]):
    self.max_position_size = Decimal(str(config.get('max_position_size', 1000)))  # USDT
    self.max_portfolio_risk = config.get('max_portfolio_risk', 0.05)  # 5%
    self.kelly_fraction = config.get('kelly_fraction', 0.25)  # Conservative Kelly
    
    self.logger = structlog.get_logger("risk.position_sizing")

def calculate_position_size(self, opportunity, portfolio_value: Decimal, 
                          win_rate: float, avg_win: float, avg_loss: float) -> Decimal:
    """Calculate optimal position size using multiple methods"""
    
    # Method 1: Fixed maximum
    max_size_fixed = self.max_position_size
    
    # Method 2: Portfolio percentage
    max_size_portfolio = portfolio_value * Decimal(str(self.max_portfolio_risk))
    
    # Method 3: Kelly Criterion (if we have historical data)
    max_size_kelly = self._kelly_position_size(
        portfolio_value, win_rate, avg_win, avg_loss
    )
    
    # Method 4: Volatility-based sizing
    max_size_volatility = self._volatility_position_size(
        opportunity, portfolio_value
    )
    
    # Take the minimum of all methods (most conservative)
    position_size = min(
        max_size_fixed,
        max_size_portfolio, 
        max_size_kelly,
        max_size_volatility,
        opportunity.required_capital  # Can't exceed what's needed
    )
    
    self.logger.debug("position_size_calculated",
                     fixed=float(max_size_fixed),
                     portfolio=float(max_size_portfolio),
                     kelly=float(max_size_kelly),
                     volatility=float(max_size_volatility),
                     final=float(position_size))
    
    return position_size

def _kelly_position_size(self, portfolio_value: Decimal, 
                       win_rate: float, avg_win: float, avg_loss: float) -> Decimal:
    """Calculate position size using Kelly Criterion"""
    if win_rate <= 0 or avg_loss <= 0:
        return portfolio_value * Decimal('0.01')  # 1% default
    
    # Kelly fraction = (bp - q) / b
    # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - win_rate
    
    kelly_fraction = (b * p - q) / b
    
    # Apply conservative scaling
    kelly_fraction = max(0, min(kelly_fraction * self.kelly_fraction, 0.1))
    
    return portfolio_value * Decimal(str(kelly_fraction))

def _volatility_position_size(self, opportunity, portfolio_value: Decimal) -> Decimal:
    """Calculate position size based on volatility"""
    # Simplified volatility-based sizing
    # In practice, you'd calculate actual volatility from price history
    
    spread_vol = float(opportunity.spread_percentage)
    
    if spread_vol > 2.0:  # High spread, lower volatility
        vol_factor = 0.05
    elif spread_vol > 1.0:  # Medium spread
        vol_factor = 0.03
    else:  # Low spread, higher volatility
        vol_factor = 0.02
    
    return portfolio_value * Decimal(str(vol_factor))
```

class RiskManager:
“”“Main risk management system”””

```
def __init__(self, exchanges: Dict[str, BaseExchange], config: Dict[str, Any]):
    self.exchanges = exchanges
    self.config = config
    self.risk_config = config.get('risk_management', {})
    
    # Risk limits
    self.max_daily_loss = Decimal(str(self.risk_config.get('max_daily_loss', 50)))
    self.max_position_size = Decimal(str(self.risk_config.get('max_position_size', 1000)))
    self.max_risk_score = self.risk_config.get('max_risk_score', 0.8)
    self.min_confidence_level = self.risk_config.get('min_confidence_level', 0.7)
    
    # Stop loss configuration
    self.enable_stop_loss = self.risk_config.get('enable_stop_loss', True)
    self.stop_loss_percent = Decimal(str(self.risk_config.get('stop_loss_percent', -2.0)))
    self.emergency_stop_enabled = self.risk_config.get('emergency_stop_enabled', True)
    
    # Circuit breaker
    circuit_breaker_config = self.risk_config.get('circuit_breaker', {})
    self.circuit_breaker = CircuitBreaker(circuit_breaker_config)
    
    # Position sizing
    self.position_calculator = PositionSizeCalculator(self.risk_config)
    
    # Risk tracking
    self.daily_pnl = Decimal('0')
    self.total_exposure = Decimal('0')
    self.active_positions = {}
    self.risk_metrics_history = []
    
    # Emergency stop flag
    self.emergency_stop = False
    
    self.logger = structlog.get_logger("risk_manager")

async def assess_opportunity(self, opportunity) -> RiskAssessment:
    """Comprehensive risk assessment of trading opportunity"""
    
    warnings = []
    blockers = []
    risk_metrics = []
    
    # Check circuit breaker
    if not self.circuit_breaker.can_trade():
        blockers.append("Circuit breaker is triggered")
    
    # Check emergency stop
    if self.emergency_stop:
        blockers.append("Emergency stop is active")
    
    # Check daily loss limit
    if self.daily_pnl <= -self.max_daily_loss:
        blockers.append(f"Daily loss limit exceeded: {self.daily_pnl}")
    
    # Assess market risk
    market_risk = await self._assess_market_risk(opportunity)
    risk_metrics.append(market_risk)
    
    if market_risk.level == RiskLevel.CRITICAL:
        blockers.append(f"Market risk too high: {market_risk.description}")
    elif market_risk.level == RiskLevel.HIGH:
        warnings.append(f"High market risk: {market_risk.description}")
    
    # Assess liquidity risk
    liquidity_risk = await self._assess_liquidity_risk(opportunity)
    risk_metrics.append(liquidity_risk)
    
    if liquidity_risk.level == RiskLevel.CRITICAL:
        blockers.append(f"Liquidity risk too high: {liquidity_risk.description}")
    
    # Assess concentration risk
    concentration_risk = await self._assess_concentration_risk(opportunity)
    risk_metrics.append(concentration_risk)
    
    if concentration_risk.level == RiskLevel.HIGH:
        warnings.append(f"High concentration risk: {concentration_risk.description}")
    
    # Assess counterparty risk
    counterparty_risk = await self._assess_counterparty_risk(opportunity)
    risk_metrics.append(counterparty_risk)
    
    # Check minimum confidence level
    if opportunity.confidence < self.min_confidence_level:
        blockers.append(f"Confidence too low: {opportunity.confidence}")
    
    # Check maximum risk score
    if opportunity.risk_score > self.max_risk_score:
        blockers.append(f"Risk score too high: {opportunity.risk_score}")
    
    # Calculate overall risk score
    overall_risk_score = self._calculate_overall_risk_score(risk_metrics)
    
    # Determine risk level
    if overall_risk_score >= 0.8:
        risk_level = RiskLevel.CRITICAL
    elif overall_risk_score >= 0.6:
        risk_level = RiskLevel.HIGH
    elif overall_risk_score >= 0.4:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW
    
    # Final decision
    approved = len(blockers) == 0
    reason = "; ".join(blockers) if blockers else "Risk assessment passed"
    
    assessment = RiskAssessment(
        approved=approved,
        overall_risk_score=overall_risk_score,
        risk_level=risk_level,
        risk_metrics=risk_metrics,
        warnings=warnings,
        blockers=blockers,
        reason=reason,
        timestamp=time.time()
    )
    
    self.logger.info("risk_assessment_completed",
                    opportunity_id=opportunity.id,
                    approved=approved,
                    risk_score=overall_risk_score,
                    risk_level=risk_level.value,
                    warnings_count=len(warnings),
                    blockers_count=len(blockers))
    
    return assessment

async def _assess_market_risk(self, opportunity) -> RiskMetric:
    """Assess market risk factors"""
    
    # Factors to consider:
    # - Spread size (larger spreads may indicate market stress)
    # - Price volatility
    # - Market hours
    # - Recent price movements
    
    risk_score = 0.0
    description_parts = []
    
    # Spread analysis
    spread_pct = float(opportunity.spread_percentage)
    if spread_pct > 2.0:
        risk_score += 0.3
        description_parts.append(f"Large spread: {spread_pct:.2f}%")
    elif spread_pct > 1.0:
        risk_score += 0.1
        description_parts.append(f"Medium spread: {spread_pct:.2f}%")
    
    # Position size relative to limits
    size_ratio = float(opportunity.required_capital / self.max_position_size)
    if size_ratio > 0.8:
        risk_score += 0.2
        description_parts.append(f"Large position size: {size_ratio:.1%}")
    
    # Determine risk level
    if risk_score >= 0.7:
        level = RiskLevel.CRITICAL
    elif risk_score >= 0.5:
        level = RiskLevel.HIGH
    elif risk_score >= 0.3:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW
    
    description = "; ".join(description_parts) if description_parts else "Normal market conditions"
    
    return RiskMetric(
        name="Market Risk",
        value=risk_score,
        threshold=0.7,
        level=level,
        description=description,
        timestamp=time.time()
    )

async def _assess_liquidity_risk(self, opportunity) -> RiskMetric:
    """Assess liquidity risk"""
    
    risk_score = 0.0
    description_parts = []
    
    # Check if we have recent order book data
    try:
        for exchange_name in [opportunity.buy_exchange, opportunity.sell_exchange]:
            exchange = self.exchanges[exchange_name]
            orderbook = await exchange.get_orderbook(opportunity.symbol, limit=10)
            
            # Check order book depth
            if orderbook.best_bid and orderbook.best_ask:
                bid_depth = sum(amount for _, amount in orderbook.bids[:5])
                ask_depth = sum(amount for _, amount in orderbook.asks[:5])
                
                min_depth = min(bid_depth, ask_depth)
                required_amount = opportunity.required_capital / opportunity.buy_price
                
                if min_depth < required_amount * 2:  # Need 2x buffer
                    risk_score += 0.3
                    description_parts.append(f"Low liquidity on {exchange_name}")
            
    except Exception as e:
        risk_score += 0.5
        description_parts.append(f"Unable to assess liquidity: {str(e)}")
    
    # Determine risk level
    if risk_score >= 0.7:
        level = RiskLevel.CRITICAL
    elif risk_score >= 0.4:
        level = RiskLevel.HIGH
    elif risk_score >= 0.2:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW
    
    description = "; ".join(description_parts) if description_parts else "Adequate liquidity"
    
    return RiskMetric(
        name="Liquidity Risk",
        value=risk_score,
        threshold=0.7,
        level=level,
        description=description,
        timestamp=time.time()
    )

async def _assess_concentration_risk(self, opportunity) -> RiskMetric:
    """Assess concentration risk"""
    
    risk_score = 0.0
    description_parts = []
    
    # Check exposure to this symbol
    symbol_exposure = self.active_positions.get(opportunity.symbol, Decimal('0'))
    total_portfolio = self._get_total_portfolio_value()
    
    if total_portfolio > 0:
        symbol_concentration = float(symbol_exposure / total_portfolio)
        new_concentration = float((symbol_exposure + opportunity.required_capital) / total_portfolio)
        
        if new_concentration > 0.3:  # 30% max concentration
            risk_score += 0.4
            description_parts.append(f"High symbol concentration: {new_concentration:.1%}")
        elif new_concentration > 0.2:  # 20% warning
            risk_score += 0.2
            description_parts.append(f"Medium symbol concentration: {new_concentration:.1%}")
    
    # Check exchange concentration
    exchange_names = {opportunity.buy_exchange, opportunity.sell_exchange}
    for exchange_name in exchange_names:
        exchange_exposure = self._get_exchange_exposure(exchange_name)
        if total_portfolio > 0:
            exchange_concentration = float(exchange_exposure / total_portfolio)
            if exchange_concentration > 0.5:  # 50% max per exchange
                risk_score += 0.3
                description_parts.append(f"High {exchange_name} concentration: {exchange_concentration:.1%}")
    
    # Determine risk level
    if risk_score >= 0.6:
        level = RiskLevel.HIGH
    elif risk_score >= 0.3:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW
    
    description = "; ".join(description_parts) if description_parts else "Well diversified"
    
    return RiskMetric(
        name="Concentration Risk",
        value=risk_score,
        threshold=0.6,
        level=level,
        description=description,
        timestamp=time.time()
    )

async def _assess_counterparty_risk(self, opportunity) -> RiskMetric:
    """Assess counterparty (exchange) risk"""
    
    risk_score = 0.0
    description_parts = []
    
    # Check exchange health
    for exchange_name in [opportunity.buy_exchange, opportunity.sell_exchange]:
        exchange = self.exchanges[exchange_name]
        
        # Check connection status
        if not exchange.connected:
            risk_score += 0.5
            description_parts.append(f"{exchange_name} not connected")
            continue
        
        # Check recent connection errors
        if hasattr(exchange, 'connection_errors') and exchange.connection_errors > 2:
            risk_score += 0.2
            description_parts.append(f"{exchange_name} connection issues")
    
    # Determine risk level
    if risk_score >= 0.7:
        level = RiskLevel.CRITICAL
    elif risk_score >= 0.4:
        level = RiskLevel.HIGH
    elif risk_score >= 0.2:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW
    
    description = "; ".join(description_parts) if description_parts else "Exchanges healthy"
    
    return RiskMetric(
        name="Counterparty Risk",
        value=risk_score,
        threshold=0.7,
        level=level,
        description=description,
        timestamp=time.time()
    )

def _calculate_overall_risk_score(self, risk_metrics: List[RiskMetric]) -> float:
    """Calculate weighted overall risk score"""
    
    # Weights for different risk types
    weights = {
        "Market Risk": 0.3,
        "Liquidity Risk": 0.3,
        "Concentration Risk": 0.2,
        "Counterparty Risk": 0.2
    }
    
    weighted_score = 0.0
    total_weight = 0.0
    
    for metric in risk_metrics:
        weight = weights.get(metric.name, 0.1)
        weighted_score += metric.value * weight
        total_weight += weight
    
    return weighted_score / total_weight if total_weight > 0 else 0.0

def _get_total_portfolio_value(self) -> Decimal:
    """Get total portfolio value across all exchanges"""
    # Placeholder implementation
    # In practice, sum balances from all exchanges
    return Decimal('10000')  # Default 10k USDT

def _get_exchange_exposure(self, exchange_name: str) -> Decimal:
    """Get current exposure on specific exchange"""
    # Placeholder implementation
    return Decimal('0')

def add_trade_result(self, profit_loss: Decimal, symbol: str):
    """Add trade result for risk tracking"""
    self.daily_pnl += profit_loss
    self.circuit_breaker.add_trade_result(profit_loss)
    
    # Update position tracking
    if symbol in self.active_positions:
        self.active_positions[symbol] += abs(profit_loss)
    
    self.logger.info("trade_result_recorded",
                    profit_loss=float(profit_loss),
                    daily_pnl=float(self.daily_pnl),
                    symbol=symbol)

def trigger_emergency_stop(self, reason: str):
    """Trigger emergency stop"""
    self.emergency_stop = True
    self.logger.critical("emergency_stop_triggered", reason=reason)

def reset_emergency_stop(self):
    """Reset emergency stop"""
    self.emergency_stop = False
    self.logger.info("emergency_stop_reset")

def get_status(self) -> Dict[str, Any]:
    """Get comprehensive risk status"""
    return {
        'daily_pnl': float(self.daily_pnl),
        'max_daily_loss': float(self.max_daily_loss),
        'emergency_stop': self.emergency_stop,
        'circuit_breaker': self.circuit_breaker.get_status(),
        'total_exposure': float(self.total_exposure),
        'active_positions': {k: float(v) for k, v in self.active_positions.items()},
        'risk_limits': {
            'max_position_size': float(self.max_position_size),
            'max_risk_score': self.max_risk_score,
            'min_confidence_level': self.min_confidence_level
        }
    }
```