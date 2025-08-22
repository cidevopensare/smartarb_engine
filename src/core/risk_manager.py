“””
Risk Manager for SmartArb Engine
Comprehensive risk management system for trading operations
“””

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime, timedelta
import structlog

from ..strategies.base_strategy import Opportunity, OpportunityStatus
from ..exchanges.base_exchange import BaseExchange, Balance

logger = structlog.get_logger(**name**)

class RiskLevel(Enum):
“”“Risk level enumeration”””
LOW = “low”
MEDIUM = “medium”
HIGH = “high”
CRITICAL = “critical”

class RiskViolation(Enum):
“”“Types of risk violations”””
POSITION_SIZE_EXCEEDED = “position_size_exceeded”
DAILY_LOSS_EXCEEDED = “daily_loss_exceeded”
TOTAL_EXPOSURE_EXCEEDED = “total_exposure_exceeded”
MAX_POSITIONS_EXCEEDED = “max_positions_exceeded”
INSUFFICIENT_BALANCE = “insufficient_balance”
SPREAD_TOO_LOW = “spread_too_low”
HIGH_SLIPPAGE_RISK = “high_slippage_risk”
EXCHANGE_RELIABILITY = “exchange_reliability”
CIRCUIT_BREAKER_TRIGGERED = “circuit_breaker_triggered”

@dataclass
class RiskAssessment:
“”“Risk assessment result”””
opportunity_id: str
risk_level: RiskLevel
risk_score: float  # 0-1 scale
violations: List[RiskViolation]
reasons: List[str]
recommended_position_size: Decimal
max_allowed_size: Decimal
confidence_adjustment: float  # Multiplier for confidence

```
@property
def is_acceptable(self) -> bool:
    """Check if risk is acceptable"""
    return self.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM] and len(self.violations) == 0
```

@dataclass
class PositionRisk:
“”“Individual position risk tracking”””
opportunity_id: str
symbol: str
exchanges: List[str]
position_size: Decimal
entry_time: float
expected_profit: Decimal
actual_profit: Decimal
risk_score: float
stop_loss: Optional[Decimal] = None

```
@property
def unrealized_pnl(self) -> Decimal:
    """Calculate unrealized P&L"""
    return self.actual_profit

@property
def duration_minutes(self) -> float:
    """Position duration in minutes"""
    return (time.time() - self.entry_time) / 60
```

class RiskManager:
“””
Comprehensive Risk Management System

```
Features:
- Position size validation
- Daily loss limits
- Portfolio exposure limits
- Circuit breaker system
- Real-time risk monitoring
- Exchange risk assessment
"""

def __init__(self, exchanges: Dict[str, BaseExchange], config: Dict[str, Any]):
    self.exchanges = exchanges
    self.config = config
    
    # Risk limits from config
    risk_config = config.get('risk_management', {})
    
    # Daily limits
    self.max_daily_trades = risk_config.get('max_daily_trades', 50)
    self.max_daily_volume = Decimal(str(risk_config.get('max_daily_volume_usd', 10000)))
    self.max_daily_loss = Decimal(str(risk_config.get('max_daily_loss', -200)))
    
    # Position limits
    self.max_position_size = Decimal(str(risk_config.get('max_position_size', 1000)))
    self.max_total_exposure = Decimal(str(risk_config.get('max_total_exposure', 5000)))
    self.max_open_positions = risk_config.get('max_open_positions', 5)
    
    # Risk controls
    self.enable_stop_loss = risk_config.get('enable_stop_loss', True)
    self.stop_loss_percent = Decimal(str(risk_config.get('stop_loss_percent', -2.0)))
    self.emergency_stop_enabled = risk_config.get('emergency_stop_enabled', True)
    
    # Circuit breaker
    circuit_config = risk_config.get('circuit_breaker', {})
    self.circuit_breaker_enabled = circuit_config.get('enabled', True)
    self.circuit_breaker_loss_threshold = Decimal(str(circuit_config.get('loss_threshold', -100)))
    self.circuit_breaker_lookback_minutes = circuit_config.get('lookback_minutes', 60)
    self.circuit_breaker_cooldown_minutes = circuit_config.get('cooldown_minutes', 30)
    
    # State tracking
    self.daily_trades = 0
    self.daily_volume = Decimal('0')
    self.daily_pnl = Decimal('0')
    self.active_positions: Dict[str, PositionRisk] = {}
    self.circuit_breaker_triggered = False
    self.circuit_breaker_trigger_time = 0
    
    # Daily reset tracking
    self.last_daily_reset = datetime.now().date()
    
    # Exchange reliability tracking
    self.exchange_reliability: Dict[str, float] = {}
    self._initialize_exchange_reliability()
    
    logger.info("risk_manager_initialized",
               max_position_size=float(self.max_position_size),
               max_daily_loss=float(self.max_daily_loss),
               circuit_breaker=self.circuit_breaker_enabled)

def _initialize_exchange_reliability(self):
    """Initialize exchange reliability scores"""
    for exchange_name in self.exchanges.keys():
        self.exchange_reliability[exchange_name] = 0.95  # Start with high reliability

async def assess_opportunity_risk(self, opportunity: Opportunity) -> RiskAssessment:
    """
    Comprehensive risk assessment for a trading opportunity
    """
    violations = []
    reasons = []
    risk_score = 0.0
    
    # Check daily reset
    await self._check_daily_reset()
    
    # Check circuit breaker
    if await self._check_circuit_breaker():
        violations.append(RiskViolation.CIRCUIT_BREAKER_TRIGGERED)
        reasons.append("Circuit breaker is active")
        return RiskAssessment(
            opportunity_id=opportunity.opportunity_id,
            risk_level=RiskLevel.CRITICAL,
            risk_score=1.0,
            violations=violations,
            reasons=reasons,
            recommended_position_size=Decimal('0'),
            max_allowed_size=Decimal('0'),
            confidence_adjustment=0.0
        )
    
    # 1. Position size assessment
    position_risk, position_violations = await self._assess_position_size(opportunity)
    violations.extend(position_violations)
    risk_score += position_risk
    
    # 2. Daily limits assessment
    daily_risk, daily_violations = await self._assess_daily_limits(opportunity)
    violations.extend(daily_violations)
    risk_score += daily_risk
    
    # 3. Portfolio exposure assessment
    exposure_risk, exposure_violations = await self._assess_portfolio_exposure(opportunity)
    violations.extend(exposure_violations)
    risk_score += exposure_risk
    
    # 4. Exchange risk assessment
    exchange_risk, exchange_violations = await self._assess_exchange_risk(opportunity)
    violations.extend(exchange_violations)
    risk_score += exchange_risk
    
    # 5. Opportunity-specific risk assessment
    opp_risk, opp_violations = await self._assess_opportunity_specific_risk(opportunity)
    violations.extend(opp_violations)
    risk_score += opp_risk
    
    # 6. Balance sufficiency check
    balance_risk, balance_violations = await self._assess_balance_sufficiency(opportunity)
    violations.extend(balance_violations)
    risk_score += balance_risk
    
    # Calculate recommended position size
    recommended_size = await self._calculate_recommended_position_size(opportunity, risk_score)
    max_allowed_size = min(opportunity.amount, self.max_position_size)
    
    # Determine risk level
    risk_level = self._calculate_risk_level(risk_score, len(violations))
    
    # Calculate confidence adjustment
    confidence_adjustment = max(0.1, 1.0 - (risk_score * 0.5))
    
    # Add specific reasons based on violations
    for violation in violations:
        reasons.append(self._get_violation_reason(violation))
    
    assessment = RiskAssessment(
        opportunity_id=opportunity.opportunity_id,
        risk_level=risk_level,
        risk_score=min(1.0, risk_score),
        violations=violations,
        reasons=reasons,
        recommended_position_size=recommended_size,
        max_allowed_size=max_allowed_size,
        confidence_adjustment=confidence_adjustment
    )
    
    logger.info("risk_assessment_completed",
               opportunity_id=opportunity.opportunity_id,
               risk_level=risk_level.value,
               risk_score=risk_score,
               violations=len(violations),
               recommended_size=float(recommended_size))
    
    return assessment

async def _assess_position_size(self, opportunity: Opportunity) -> Tuple[float, List[RiskViolation]]:
    """Assess position size risk"""
    violations = []
    risk_score = 0.0
    
    # Check against maximum position size
    if opportunity.amount > self.max_position_size:
        violations.append(RiskViolation.POSITION_SIZE_EXCEEDED)
        risk_score += 0.3
    
    # Check against available capital
    total_exposure = sum(pos.position_size for pos in self.active_positions.values())
    remaining_capital = self.max_total_exposure - total_exposure
    
    if opportunity.amount > remaining_capital:
        violations.append(RiskViolation.TOTAL_EXPOSURE_EXCEEDED)
        risk_score += 0.4
    
    # Size relative to portfolio
    if total_exposure > 0:
        position_percent = (opportunity.amount / total_exposure) * 100
        if position_percent > 50:  # Single position > 50% of portfolio
            risk_score += 0.2
    
    return risk_score, violations

async def _assess_daily_limits(self, opportunity: Opportunity) -> Tuple[float, List[RiskViolation]]:
    """Assess daily trading limits"""
    violations = []
    risk_score = 0.0
    
    # Check daily trade count
    if self.daily_trades >= self.max_daily_trades:
        violations.append(RiskViolation.MAX_POSITIONS_EXCEEDED)
        risk_score += 0.3
    
    # Check daily volume limit
    if self.daily_volume + opportunity.amount > self.max_daily_volume:
        risk_score += 0.2
    
    # Check daily loss limit
    if self.daily_pnl < self.max_daily_loss:
        violations.append(RiskViolation.DAILY_LOSS_EXCEEDED)
        risk_score += 0.5
    
    # Risk increases as we approach limits
    trade_ratio = self.daily_trades / self.max_daily_trades
    volume_ratio = float(self.daily_volume / self.max_daily_volume)
    
    if trade_ratio > 0.8:
        risk_score += 0.1
    if volume_ratio > 0.8:
        risk_score += 0.1
    
    return risk_score, violations

async def _assess_portfolio_exposure(self, opportunity: Opportunity) -> Tuple[float, List[RiskViolation]]:
    """Assess portfolio exposure risk"""
    violations = []
    risk_score = 0.0
    
    # Check maximum open positions
    if len(self.active_positions) >= self.max_open_positions:
        violations.append(RiskViolation.MAX_POSITIONS_EXCEEDED)
        risk_score += 0.3
    
    # Check total exposure
    total_exposure = sum(pos.position_size for pos in self.active_positions.values())
    exposure_ratio = float((total_exposure + opportunity.amount) / self.max_total_exposure)
    
    if exposure_ratio > 1.0:
        violations.append(RiskViolation.TOTAL_EXPOSURE_EXCEEDED)
        risk_score += 0.4
    elif exposure_ratio > 0.8:
        risk_score += 0.2
    
    # Check symbol concentration
    symbol_exposure = sum(
        pos.position_size for pos in self.active_positions.values()
        if pos.symbol == opportunity.symbol
    )
    symbol_ratio = float((symbol_exposure + opportunity.amount) / self.max_total_exposure)
    
    if symbol_ratio > 0.3:  # Max 30% in single symbol
        risk_score += 0.2
    
    return risk_score, violations

async def _assess_exchange_risk(self, opportunity: Opportunity) -> Tuple[float, List[RiskViolation]]:
    """Assess exchange-specific risks"""
    violations = []
    risk_score = 0.0
    
    # Get exchange names from opportunity (implementation depends on opportunity type)
    exchanges_involved = getattr(opportunity, 'exchanges', [])
    if not exchanges_involved and hasattr(opportunity, 'buy_exchange'):
        exchanges_involved = [opportunity.buy_exchange, opportunity.sell_exchange]
    
    for exchange_name in exchanges_involved:
        if exchange_name in self.exchange_reliability:
            reliability = self.exchange_reliability[exchange_name]
            if reliability < 0.8:
                violations.append(RiskViolation.EXCHANGE_RELIABILITY)
                risk_score += (1.0 - reliability) * 0.3
    
    return risk_score, violations

async def _assess_opportunity_specific_risk(self, opportunity: Opportunity) -> Tuple[float, List[RiskViolation]]:
    """Assess opportunity-specific risks"""
    violations = []
    risk_score = 0.0
    
    # Check profit margin
    if hasattr(opportunity, 'expected_profit_percent'):
        profit_percent = float(opportunity.expected_profit_percent)
        if profit_percent < 0.2:  # Less than 0.2% profit
            violations.append(RiskViolation.SPREAD_TOO_LOW)
            risk_score += 0.3
    
    # Check confidence level
    if hasattr(opportunity, 'confidence_level'):
        confidence = opportunity.confidence_level
        if confidence < 0.7:
            risk_score += (0.7 - confidence) * 0.5
    
    # Check opportunity age
    opportunity_age = time.time() - opportunity.timestamp
    if opportunity_age > 30:  # Opportunity older than 30 seconds
        risk_score += min(0.3, opportunity_age / 100)
    
    # Check market conditions (simplified)
    if hasattr(opportunity, 'market_volatility'):
        volatility = getattr(opportunity, 'market_volatility', 0)
        if volatility > 0.1:  # High volatility
            risk_score += volatility * 0.2
    
    return risk_score, violations

async def _assess_balance_sufficiency(self, opportunity: Opportunity) -> Tuple[float, List[RiskViolation]]:
    """Check if balances are sufficient for the opportunity"""
    violations = []
    risk_score = 0.0
    
    try:
        # This is a simplified check - specific implementation depends on opportunity type
        if hasattr(opportunity, 'buy_exchange') and hasattr(opportunity, 'sell_exchange'):
            buy_exchange = self.exchanges.get(opportunity.buy_exchange)
            sell_exchange = self.exchanges.get(opportunity.sell_exchange)
            
            if buy_exchange and sell_exchange:
                # Check buy side balance
                base_asset, quote_asset = opportunity.symbol.split('/')
                
                buy_balances = await buy_exchange.get_balance(quote_asset)
                needed_quote = opportunity.amount * getattr(opportunity, 'buy_price', Decimal('0')) * Decimal('1.01')
                
                if quote_asset not in buy_balances or buy_balances[quote_asset].free < needed_quote:
                    violations.append(RiskViolation.INSUFFICIENT_BALANCE)
                    risk_score += 0.5
                
                # Check sell side balance
                sell_balances = await sell_exchange.get_balance(base_asset)
                needed_base = opportunity.amount * Decimal('1.01')
                
                if base_asset not in sell_balances or sell_balances[base_asset].free < needed_base:
                    violations.append(RiskViolation.INSUFFICIENT_BALANCE)
                    risk_score += 0.5
    
    except Exception as e:
        logger.warning("balance_check_failed", error=str(e))
        risk_score += 0.2  # Add some risk if we can't verify balances
    
    return risk_score, violations

async def _calculate_recommended_position_size(self, opportunity: Opportunity, risk_score: float) -> Decimal:
    """Calculate recommended position size based on risk assessment"""
    base_size = min(opportunity.amount, self.max_position_size)
    
    # Reduce size based on risk score
    risk_multiplier = max(0.1, 1.0 - risk_score)
    
    # Consider current portfolio exposure
    total_exposure = sum(pos.position_size for pos in self.active_positions.values())
    remaining_capacity = self.max_total_exposure - total_exposure
    
    # Use Kelly Criterion approximation for position sizing
    if hasattr(opportunity, 'expected_profit_percent') and hasattr(opportunity, 'confidence_level'):
        win_rate = opportunity.confidence_level
        avg_win = float(opportunity.expected_profit_percent) / 100
        avg_loss = 0.01  # Assume 1% average loss
        
        if win_rate > 0 and avg_win > 0:
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly_fraction = max(0, min(0.25, kelly_fraction))  # Cap at 25%
            
            kelly_size = self.max_total_exposure * Decimal(str(kelly_fraction))
            base_size = min(base_size, kelly_size)
    
    recommended_size = base_size * Decimal(str(risk_multiplier))
    
    # Ensure we don't exceed remaining capacity
    recommended_size = min(recommended_size, remaining_capacity)
    
    # Minimum position size check
    min_size = Decimal('10')  # Minimum $10 position
    recommended_size = max(min_size, recommended_size) if recommended_size > 0 else Decimal('0')
    
    return recommended_size

def _calculate_risk_level(self, risk_score: float, violations_count: int) -> RiskLevel:
    """Calculate overall risk level"""
    if violations_count > 0:
        return RiskLevel.CRITICAL
    elif risk_score > 0.7:
        return RiskLevel.HIGH
    elif risk_score > 0.4:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW

def _get_violation_reason(self, violation: RiskViolation) -> str:
    """Get human-readable reason for risk violation"""
    reasons_map = {
        RiskViolation.POSITION_SIZE_EXCEEDED: f"Position size exceeds maximum of {self.max_position_size} USDT",
        RiskViolation.DAILY_LOSS_EXCEEDED: f"Daily loss limit of {self.max_daily_loss} USDT exceeded",
        RiskViolation.TOTAL_EXPOSURE_EXCEEDED: f"Total exposure would exceed {self.max_total_exposure} USDT",
        RiskViolation.MAX_POSITIONS_EXCEEDED: f"Maximum {self.max_open_positions} positions already open",
        RiskViolation.INSUFFICIENT_BALANCE: "Insufficient balance to execute opportunity",
        RiskViolation.SPREAD_TOO_LOW: "Profit spread too low for acceptable risk",
        RiskViolation.HIGH_SLIPPAGE_RISK: "High slippage risk detected",
        RiskViolation.EXCHANGE_RELIABILITY: "Exchange reliability below threshold",
        RiskViolation.CIRCUIT_BREAKER_TRIGGERED: "Emergency circuit breaker is active"
    }
    return reasons_map.get(violation, f"Risk violation: {violation.value}")

async def _check_daily_reset(self):
    """Check if we need to reset daily counters"""
    current_date = datetime.now().date()
    if current_date > self.last_daily_reset:
        self.daily_trades = 0
        self.daily_volume = Decimal('0')
        self.daily_pnl = Decimal('0')
        self.last_daily_reset = current_date
        logger.info("daily_counters_reset", date=str(current_date))

async def _check_circuit_breaker(self) -> bool:
    """Check if circuit breaker should be triggered or is active"""
    if not self.circuit_breaker_enabled:
        return False
    
    # Check if currently in cooldown
    if self.circuit_breaker_triggered:
        time_since_trigger = (time.time() - self.circuit_breaker_trigger_time) / 60
        if time_since_trigger < self.circuit_breaker_cooldown_minutes:
            return True
        else:
            # Cooldown period ended
            self.circuit_breaker_triggered = False
            logger.info("circuit_breaker_reset")
            return False
    
    # Check if should be triggered
    if self.daily_pnl <= self.circuit_breaker_loss_threshold:
        self.circuit_breaker_triggered = True
        self.circuit_breaker_trigger_time = time.time()
        logger.warning("circuit_breaker_triggered",
                      daily_pnl=float(self.daily_pnl),
                      threshold=float(self.circuit_breaker_loss_threshold))
        return True
    
    return False

# Position Management Methods
async def add_position(self, opportunity: Opportunity) -> None:
    """Add a position to risk tracking"""
    position = PositionRisk(
        opportunity_id=opportunity.opportunity_id,
        symbol=opportunity.symbol,
        exchanges=getattr(opportunity, 'exchanges', []),
        position_size=opportunity.amount,
        entry_time=time.time(),
        expected_profit=opportunity.expected_profit,
        actual_profit=Decimal('0'),
        risk_score=opportunity.risk_score
    )
    
    if self.enable_stop_loss:
        position.stop_loss = opportunity.expected_profit * (self.stop_loss_percent / 100)
    
    self.active_positions[opportunity.opportunity_id] = position
    self.daily_trades += 1
    self.daily_volume += opportunity.amount
    
    logger.info("position_added",
               opportunity_id=opportunity.opportunity_id,
               symbol=opportunity.symbol,
               size=float(opportunity.amount),
               active_positions=len(self.active_positions))

async def update_position_pnl(self, opportunity_id: str, actual_profit: Decimal) -> None:
    """Update position P&L"""
    if opportunity_id in self.active_positions:
        position = self.active_positions[opportunity_id]
        old_profit = position.actual_profit
        position.actual_profit = actual_profit
        
        # Update daily P&L
        pnl_change = actual_profit - old_profit
        self.daily_pnl += pnl_change
        
        # Check stop loss
        if self.enable_stop_loss and position.stop_loss:
            if actual_profit <= position.stop_loss:
                logger.warning("stop_loss_triggered",
                             opportunity_id=opportunity_id,
                             actual_profit=float(actual_profit),
                             stop_loss=float(position.stop_loss))

async def remove_position(self, opportunity_id: str) -> Optional[PositionRisk]:
    """Remove position from tracking"""
    position = self.active_positions.pop(opportunity_id, None)
    if position:
        logger.info("position_removed",
                   opportunity_id=opportunity_id,
                   final_profit=float(position.actual_profit),
                   duration_minutes=position.duration_minutes,
                   active_positions=len(self.active_positions))
    return position

# Status and Reporting Methods
def get_risk_status(self) -> Dict[str, Any]:
    """Get current risk management status"""
    total_exposure = sum(pos.position_size for pos in self.active_positions.values())
    
    return {
        'daily_stats': {
            'trades': self.daily_trades,
            'volume': float(self.daily_volume),
            'pnl': float(self.daily_pnl),
            'max_trades': self.max_daily_trades,
            'max_volume': float(self.max_daily_volume),
            'max_loss': float(self.max_daily_loss)
        },
        'position_stats': {
            'active_positions': len(self.active_positions),
            'max_positions': self.max_open_positions,
            'total_exposure': float(total_exposure),
            'max_exposure': float(self.max_total_exposure),
            'utilization_percent': float(total_exposure / self.max_total_exposure * 100)
        },
        'circuit_breaker': {
            'enabled': self.circuit_breaker_enabled,
            'triggered': self.circuit_breaker_triggered,
            'trigger_time': self.circuit_breaker_trigger_time if self.circuit_breaker_triggered else None
        },
        'exchange_reliability': self.exchange_reliability
    }

def get_active_positions(self) -> List[Dict[str, Any]]:
    """Get list of active positions"""
    return [
        {
            'opportunity_id': pos.opportunity_id,
            'symbol': pos.symbol,
            'exchanges': pos.exchanges,
            'position_size': float(pos.position_size),
            'expected_profit': float(pos.expected_profit),
            'actual_profit': float(pos.actual_profit),
            'unrealized_pnl': float(pos.unrealized_pnl),
            'duration_minutes': pos.duration_minutes,
            'risk_score': pos.risk_score
        }
        for pos in self.active_positions.values()
    ]

async def emergency_stop(self) -> None:
    """Trigger emergency stop of all trading"""
    if not self.emergency_stop_enabled:
        return
    
    self.circuit_breaker_triggered = True
    self.circuit_breaker_trigger_time = time.time()
    
    logger.critical("emergency_stop_triggered",
                   active_positions=len(self.active_positions),
                   total_exposure=float(sum(pos.position_size for pos in self.active_positions.values())))
    
    # Here you would implement emergency position closure logic
    # For now, we just log and set the circuit breaker

def update_exchange_reliability(self, exchange_name: str, success: bool) -> None:
    """Update exchange reliability score based on operation success"""
    if exchange_name not in self.exchange_reliability:
        self.exchange_reliability[exchange_name] = 0.95
    
    current_reliability = self.exchange_reliability[exchange_name]
    
    if success:
        # Slowly increase reliability on success
        self.exchange_reliability[exchange_name] = min(1.0, current_reliability + 0.001)
    else:
        # Quickly decrease reliability on failure
        self.exchange_reliability[exchange_name] = max(0.0, current_reliability - 0.05)
    
    if not success:
        logger.warning("exchange_reliability_decreased",
                     exchange=exchange_name,
                     new_reliability=self.exchange_reliability[exchange_name])
```