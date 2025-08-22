“””
Risk Management System for SmartArb Engine
Advanced risk assessment and protection mechanisms
“””

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
from datetime import datetime, timedelta
import structlog

from ..exchanges.base_exchange import BaseExchange
from ..strategies.base_strategy import Opportunity

logger = structlog.get_logger(**name**)

class RiskViolation(Enum):
“”“Types of risk violations”””
POSITION_SIZE_EXCEEDED = “position_size_exceeded”
DAILY_LOSS_EXCEEDED = “daily_loss_exceeded”
MAX_POSITIONS_EXCEEDED = “max_positions_exceeded”
TOTAL_EXPOSURE_EXCEEDED = “total_exposure_exceeded”
EXCHANGE_CONCENTRATION = “exchange_concentration”
SYMBOL_CONCENTRATION = “symbol_concentration”
HIGH_CORRELATION = “high_correlation”
INSUFFICIENT_BALANCE = “insufficient_balance”
HIGH_VOLATILITY = “high_volatility”
LOW_LIQUIDITY = “low_liquidity”
EXCHANGE_UNRELIABLE = “exchange_unreliable”
SPREAD_TOO_NARROW = “spread_too_narrow”
EXECUTION_RISK_HIGH = “execution_risk_high”

class RiskLevel(Enum):
“”“Risk assessment levels”””
LOW = “low”
MEDIUM = “medium”
HIGH = “high”
CRITICAL = “critical”

@dataclass
class RiskAssessment:
“”“Risk assessment result”””
opportunity_id: str
risk_score: float  # 0-1 scale
risk_level: RiskLevel
approved: bool
violations: List[RiskViolation] = field(default_factory=list)
warnings: List[str] = field(default_factory=list)
recommendations: List[str] = field(default_factory=list)
max_position_size: Optional[Decimal] = None
confidence_adjustment: float = 1.0
timestamp: float = field(default_factory=time.time)

@dataclass
class Position:
“”“Active position tracking”””
position_id: str
opportunity_id: str
symbol: str
exchanges: List[str]
position_size: Decimal
entry_time: float
expected_profit: Decimal
max_loss: Decimal
current_pnl: Decimal = Decimal(‘0’)
status: str = “open”

@dataclass
class ExchangeHealth:
“”“Exchange health metrics”””
exchange_name: str
is_healthy: bool = True
api_latency: float = 0.0
error_rate: float = 0.0
last_error_time: float = 0
consecutive_errors: int = 0
reliability_score: float = 1.0
last_health_check: float = field(default_factory=time.time)

class RiskManager:
“””
Advanced Risk Management System

```
Features:
- Position size limits
- Daily loss limits
- Portfolio exposure management
- Exchange health monitoring
- Correlation analysis
- Liquidity assessment
- Dynamic risk scoring
"""

def __init__(self, exchanges: Dict[str, BaseExchange], config: Dict[str, Any]):
    self.exchanges = exchanges
    self.config = config
    
    # Risk configuration
    risk_config = config.get('risk_management', {})
    
    # Position limits
    self.max_position_size = Decimal(str(risk_config.get('max_position_size', 1000)))
    self.max_daily_volume = Decimal(str(risk_config.get('max_daily_volume', 5000)))
    self.max_open_positions = risk_config.get('max_open_positions', 5)
    self.max_total_exposure = Decimal(str(risk_config.get('max_total_exposure', 10000)))
    
    # Loss limits
    self.max_daily_loss = Decimal(str(risk_config.get('max_daily_loss', -100)))
    self.max_position_loss = Decimal(str(risk_config.get('max_position_loss', -50)))
    self.stop_loss_percent = Decimal(str(risk_config.get('stop_loss_percent', -5.0)))
    
    # Risk thresholds
    self.high_risk_threshold = risk_config.get('high_risk_threshold', 0.7)
    self.critical_risk_threshold = risk_config.get('critical_risk_threshold', 0.9)
    self.min_confidence_threshold = risk_config.get('min_confidence_threshold', 0.6)
    
    # Concentration limits
    self.max_symbol_concentration = risk_config.get('max_symbol_concentration', 0.3)  # 30%
    self.max_exchange_concentration = risk_config.get('max_exchange_concentration', 0.5)  # 50%
    
    # Operational limits
    self.max_daily_trades = risk_config.get('max_daily_trades', 50)
    self.min_spread_percent = Decimal(str(risk_config.get('min_spread_percent', 0.1)))
    
    # Emergency controls
    self.emergency_stop_enabled = risk_config.get('emergency_stop_enabled', True)
    self.circuit_breaker_enabled = risk_config.get('circuit_breaker_enabled', True)
    
    # State tracking
    self.active_positions: Dict[str, Position] = {}
    self.daily_trades = 0
    self.daily_volume = Decimal('0')
    self.daily_pnl = Decimal('0')
    self.last_reset_date = datetime.now().date()
    
    # Exchange health tracking
    self.exchange_health: Dict[str, ExchangeHealth] = {}
    self._initialize_exchange_health()
    
    # Risk history
    self.risk_assessments: List[RiskAssessment] = []
    self.max_risk_history = 1000
    
    # Circuit breaker state
    self.circuit_breaker_active = False
    self.circuit_breaker_triggered_at = None
    self.circuit_breaker_cooldown = timedelta(minutes=30)
    
    # Performance tracking
    self.risk_stats = {
        'total_assessments': 0,
        'approved_trades': 0,
        'rejected_trades': 0,
        'avg_risk_score': 0.0,
        'violation_counts': {violation.value: 0 for violation in RiskViolation}
    }
    
    logger.info("risk_manager_initialized",
               max_position_size=float(self.max_position_size),
               max_daily_loss=float(self.max_daily_loss),
               max_open_positions=self.max_open_positions,
               emergency_stop=self.emergency_stop_enabled)

def _initialize_exchange_health(self):
    """Initialize exchange health monitoring"""
    for exchange_name in self.exchanges.keys():
        self.exchange_health[exchange_name] = ExchangeHealth(
            exchange_name=exchange_name
        )

async def assess_risk(self, opportunity: Opportunity) -> RiskAssessment:
    """Comprehensive risk assessment for an opportunity"""
    
    # Reset daily counters if needed
    self._check_daily_reset()
    
    # Check circuit breaker
    if self._is_circuit_breaker_active():
        return RiskAssessment(
            opportunity_id=opportunity.opportunity_id,
            risk_score=1.0,
            risk_level=RiskLevel.CRITICAL,
            approved=False,
            violations=[RiskViolation.DAILY_LOSS_EXCEEDED],
            warnings=["Circuit breaker is active"]
        )
    
    # Perform multi-dimensional risk assessment
    assessment = RiskAssessment(
        opportunity_id=opportunity.opportunity_id,
        risk_score=0.0,
        risk_level=RiskLevel.LOW,
        approved=True
    )
    
    try:
        # Position size assessment
        position_risk, position_violations = await self._assess_position_size(opportunity)
        assessment.risk_score += position_risk * 0.25
        assessment.violations.extend(position_violations)
        
        # Daily limits assessment
        daily_risk, daily_violations = await self._assess_daily_limits(opportunity)
        assessment.risk_score += daily_risk * 0.20
        assessment.violations.extend(daily_violations)
        
        # Portfolio exposure assessment
        exposure_risk, exposure_violations = await self._assess_portfolio_exposure(opportunity)
        assessment.risk_score += exposure_risk * 0.20
        assessment.violations.extend(exposure_violations)
        
        # Exchange risk assessment
        exchange_risk, exchange_violations = await self._assess_exchange_risk(opportunity)
        assessment.risk_score += exchange_risk * 0.15
        assessment.violations.extend(exchange_violations)
        
        # Market risk assessment
        market_risk, market_violations = await self._assess_market_risk(opportunity)
        assessment.risk_score += market_risk * 0.15
        assessment.violations.extend(market_violations)
        
        # Execution risk assessment
        execution_risk, execution_violations = await self._assess_execution_risk(opportunity)
        assessment.risk_score += execution_risk * 0.05
        assessment.violations.extend(execution_violations)
        
        # Determine risk level and approval
        assessment.risk_level = self._calculate_risk_level(assessment.risk_score)
        assessment.approved = self._determine_approval(assessment)
        
        # Generate recommendations
        assessment.recommendations = self._generate_recommendations(assessment, opportunity)
        
        # Adjust position size if needed
        assessment.max_position_size = self._calculate_max_position_size(assessment, opportunity)
        
        # Update statistics
        self._update_risk_stats(assessment)
        
        # Store assessment
        self.risk_assessments.append(assessment)
        if len(self.risk_assessments) > self.max_risk_history:
            self.risk_assessments = self.risk_assessments[-self.max_risk_history:]
        
        logger.info("risk_assessment_completed",
                   opportunity_id=opportunity.opportunity_id,
                   risk_score=assessment.risk_score,
                   risk_level=assessment.risk_level.value,
                   approved=assessment.approved,
                   violations_count=len(assessment.violations))
        
        return assessment
        
    except Exception as e:
        logger.error("risk_assessment_failed",
                    opportunity_id=opportunity.opportunity_id,
                    error=str(e))
        
        # Return conservative assessment on error
        return RiskAssessment(
            opportunity_id=opportunity.opportunity_id,
            risk_score=1.0,
            risk_level=RiskLevel.CRITICAL,
            approved=False,
            warnings=[f"Risk assessment error: {str(e)}"]
        )

async def _assess_position_size(self, opportunity: Opportunity) -> Tuple[float, List[RiskViolation]]:
    """Assess position size risk"""
    violations = []
    risk_score = 0.0
    
    # Check against maximum position size
    if opportunity.amount > self.max_position_size:
        violations.append(RiskViolation.POSITION_SIZE_EXCEEDED)
        risk_score += 0.5
    
    # Risk increases as position size approaches limit
    size_ratio = float(opportunity.amount / self.max_position_size)
    if size_ratio > 0.8:
        risk_score += 0.2
    elif size_ratio > 0.5:
        risk_score += 0.1
    
    # Check against available balance
    try:
        if hasattr(opportunity, 'exchanges'):
            for exchange_name in opportunity.exchanges:
                if exchange_name in self.exchanges:
                    exchange = self.exchanges[exchange_name]
                    # Simplified balance check - would need actual implementation
                    # balances = await exchange.get_balance()
                    # Implementation would check actual balances
                    pass
    except Exception as e:
        logger.warning("balance_check_failed", error=str(e))
        risk_score += 0.1
    
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
    
    if symbol_ratio > self.max_symbol_concentration:
        violations.append(RiskViolation.SYMBOL_CONCENTRATION)
        risk_score += 0.2
    
    return risk_score, violations

async def _assess_exchange_risk(self, opportunity: Opportunity) -> Tuple[float, List[RiskViolation]]:
    """Assess exchange-related risks"""
    violations = []
    risk_score = 0.0
    
    # Get exchanges involved in the opportunity
    exchanges = getattr(opportunity, 'exchanges', [])
    if hasattr(opportunity, 'buy_exchange') and hasattr(opportunity, 'sell_exchange'):
        exchanges = [opportunity.buy_exchange, opportunity.sell_exchange]
    
    for exchange_name in exchanges:
        if exchange_name in self.exchange_health:
            health = self.exchange_health[exchange_name]
            
            # Check exchange reliability
            if not health.is_healthy:
                violations.append(RiskViolation.EXCHANGE_UNRELIABLE)
                risk_score += 0.3
            
            # Risk increases with poor reliability
            reliability_risk = (1.0 - health.reliability_score) * 0.2
            risk_score += reliability_risk
            
            # High latency increases execution risk
            if health.api_latency > 2000:  # 2 seconds
                risk_score += 0.1
            
            # Recent errors increase risk
            if health.consecutive_errors > 3:
                risk_score += 0.1
    
    # Check exchange concentration
    exchange_exposure = {}
    for pos in self.active_positions.values():
        for ex in pos.exchanges:
            exchange_exposure[ex] = exchange_exposure.get(ex, Decimal('0')) + pos.position_size
    
    for exchange_name in exchanges:
        current_exposure = exchange_exposure.get(exchange_name, Decimal('0'))
        exposure_ratio = float((current_exposure + opportunity.amount) / self.max_total_exposure)
        
        if exposure_ratio > self.max_exchange_concentration:
            violations.append(RiskViolation.EXCHANGE_CONCENTRATION)
            risk_score += 0.2
    
    return risk_score, violations

async def _assess_market_risk(self, opportunity: Opportunity) -> Tuple[float, List[RiskViolation]]:
    """Assess market-related risks"""
    violations = []
    risk_score = 0.0
    
    # Check spread size
    spread_percent = getattr(opportunity, 'expected_profit_percent', Decimal('0'))
    if spread_percent < self.min_spread_percent:
        violations.append(RiskViolation.SPREAD_TOO_NARROW)
        risk_score += 0.3
    
    # Check confidence level
    confidence = getattr(opportunity, 'confidence_level', 1.0)
    if confidence < self.min_confidence_threshold:
        risk_score += 0.2
    
    # Volatility assessment (simplified)
    volatility_risk = max(0, (0.5 - confidence) * 0.4)
    risk_score += volatility_risk
    
    return risk_score, violations

async def _assess_execution_risk(self, opportunity: Opportunity) -> Tuple[float, List[RiskViolation]]:
    """Assess execution-related risks"""
    violations = []
    risk_score = 0.0
    
    # Time-sensitive nature of arbitrage
    # If opportunity has been around for too long, execution risk increases
    if hasattr(opportunity, 'timestamp'):
        age_seconds = time.time() - opportunity.timestamp
        if age_seconds > 30:  # 30 seconds old
            risk_score += 0.1
        if age_seconds > 60:  # 1 minute old
            violations.append(RiskViolation.EXECUTION_RISK_HIGH)
            risk_score += 0.2
    
    # Market depth and liquidity (would need real order book data)
    # This is a simplified check
    if hasattr(opportunity, 'volume_available'):
        if opportunity.volume_available < opportunity.amount * 2:
            violations.append(RiskViolation.LOW_LIQUIDITY)
            risk_score += 0.2
    
    return risk_score, violations

def _calculate_risk_level(self, risk_score: float) -> RiskLevel:
    """Calculate risk level from score"""
    if risk_score >= self.critical_risk_threshold:
        return RiskLevel.CRITICAL
    elif risk_score >= self.high_risk_threshold:
        return RiskLevel.HIGH
    elif risk_score >= 0.3:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW

def _determine_approval(self, assessment: RiskAssessment) -> bool:
    """Determine if opportunity should be approved"""
    
    # Critical violations always reject
    critical_violations = [
        RiskViolation.DAILY_LOSS_EXCEEDED,
        RiskViolation.TOTAL_EXPOSURE_EXCEEDED,
        RiskViolation.POSITION_SIZE_EXCEEDED,
        RiskViolation.MAX_POSITIONS_EXCEEDED
    ]
    
    for violation in assessment.violations:
        if violation in critical_violations:
            return False
    
    # Reject if risk level is critical
    if assessment.risk_level == RiskLevel.CRITICAL:
        return False
    
    # Reject if risk score is too high
    if assessment.risk_score >= self.critical_risk_threshold:
        return False
    
    return True

def _generate_recommendations(self, assessment: RiskAssessment, 
                            opportunity: Opportunity) -> List[str]:
    """Generate risk management recommendations"""
    recommendations = []
    
    if assessment.risk_score > 0.5:
        recommendations.append("Consider reducing position size")
    
    if RiskViolation.EXCHANGE_CONCENTRATION in assessment.violations:
        recommendations.append("Diversify across more exchanges")
    
    if RiskViolation.SYMBOL_CONCENTRATION in assessment.violations:
        recommendations.append("Reduce exposure to this symbol")
    
    if RiskViolation.LOW_LIQUIDITY in assessment.violations:
        recommendations.append("Wait for better liquidity")
    
    if RiskViolation.SPREAD_TOO_NARROW in assessment.violations:
        recommendations.append("Wait for wider spread")
    
    if assessment.risk_score > 0.3:
        recommendations.append("Monitor position closely")
    
    return recommendations

def _calculate_max_position_size(self, assessment: RiskAssessment, 
                               opportunity: Opportunity) -> Decimal:
    """Calculate maximum safe position size"""
    
    # Start with requested amount
    max_size = opportunity.amount
    
    # Reduce based on risk score
    if assessment.risk_score > 0.5:
        reduction_factor = 1.0 - (assessment.risk_score - 0.5)
        max_size = max_size * Decimal(str(reduction_factor))
    
    # Apply absolute limits
    max_size = min(max_size, self.max_position_size)
    
    # Check daily volume limit
    remaining_daily_volume = self.max_daily_volume - self.daily_volume
    max_size = min(max_size, remaining_daily_volume)
    
    # Ensure minimum viable size
    min_viable_size = Decimal('10')  # $10 minimum
    if max_size < min_viable_size:
        max_size = Decimal('0')
    
    return max_size

def _check_daily_reset(self):
    """Reset daily counters if new day"""
    current_date = datetime.now().date()
    if current_date != self.last_reset_date:
        self.daily_trades = 0
        self.daily_volume = Decimal('0')
        self.daily_pnl = Decimal('0')
        self.last_reset_date = current_date
        
        logger.info("daily_risk_counters_reset", date=str(current_date))

def _is_circuit_breaker_active(self) -> bool:
    """Check if circuit breaker is active"""
    if not self.circuit_breaker_active:
        return False
    
    if self.circuit_breaker_triggered_at:
        time_since_trigger = datetime.now() - self.circuit_breaker_triggered_at
        if time_since_trigger > self.circuit_breaker_cooldown:
            self.circuit_breaker_active = False
            self.circuit_breaker_triggered_at = None
            logger.info("circuit_breaker_deactivated")
            return False
    
    return True

def trigger_circuit_breaker(self, reason: str):
    """Trigger emergency circuit breaker"""
    if not self.circuit_breaker_enabled:
        return
    
    self.circuit_breaker_active = True
    self.circuit_breaker_triggered_at = datetime.now()
    
    logger.critical("circuit_breaker_triggered",
                   reason=reason,
                   cooldown_minutes=self.circuit_breaker_cooldown.total_seconds() / 60)

def _update_risk_stats(self, assessment: RiskAssessment):
    """Update risk statistics"""
    self.risk_stats['total_assessments'] += 1
    
    if assessment.approved:
        self.risk_stats['approved_trades'] += 1
    else:
        self.risk_stats['rejected_trades'] += 1
    
    # Update average risk score
    total = self.risk_stats['total_assessments']
    current_avg = self.risk_stats['avg_risk_score']
    self.risk_stats['avg_risk_score'] = (
        (current_avg * (total - 1) + assessment.risk_score) / total
    )
    
    # Update violation counts
    for violation in assessment.violations:
        self.risk_stats['violation_counts'][violation.value] += 1

async def update_exchange_health(self, exchange_name: str, 
                               latency: float = None, 
                               error: bool = False):
    """Update exchange health metrics"""
    if exchange_name not in self.exchange_health:
        return
    
    health = self.exchange_health[exchange_name]
    health.last_health_check = time.time()
    
    if latency is not None:
        health.api_latency = latency
    
    if error:
        health.consecutive_errors += 1
        health.last_error_time = time.time()
        health.error_rate = min(1.0, health.error_rate + 0.1)
    else:
        health.consecutive_errors = 0
        health.error_rate = max(0.0, health.error_rate - 0.05)
    
    # Update reliability score
    health.reliability_score = 1.0 - (health.error_rate * 0.5)
    health.is_healthy = health.reliability_score > 0.7 and health.consecutive_errors < 5
    
    if not health.is_healthy:
        logger.warning("exchange_unhealthy",
                      exchange=exchange_name,
                      reliability=health.reliability_score,
                      consecutive_errors=health.consecutive_errors)

def add_position(self, opportunity: Opportunity, position_size: Decimal) -> str:
    """Add new position to tracking"""
    
    position_id = f"pos_{int(time.time())}_{opportunity.opportunity_id[:8]}"
    
    exchanges = getattr(opportunity, 'exchanges', [])
    if hasattr(opportunity, 'buy_exchange') and hasattr(opportunity, 'sell_exchange'):
        exchanges = [opportunity.buy_exchange, opportunity.sell_exchange]
    
    position = Position(
        position_id=position_id,
        opportunity_id=opportunity.opportunity_id,
        symbol=opportunity.symbol,
        exchanges=exchanges,
        position_size=position_size,
        entry_time=time.time(),
        expected_profit=opportunity.expected_profit,
        max_loss=position_size * self.stop_loss_percent / 100
    )
    
    self.active_positions[position_id] = position
    
    # Update daily counters
    self.daily_trades += 1
    self.daily_volume += position_size
    
    logger.info("position_added",
               position_id=position_id,
               symbol=opportunity.symbol,
               size=float(position_size),
               active_positions=len(self.active_positions))
    
    return position_id

def close_position(self, position_id: str, actual_pnl: Decimal):
    """Close and remove position from tracking"""
    
    if position_id not in self.active_positions:
        logger.warning("position_not_found", position_id=position_id)
        return
    
    position = self.active_positions[position_id]
    position.current_pnl = actual_pnl
    position.status = "closed"
    
    # Update daily P&L
    self.daily_pnl += actual_pnl
    
    # Remove from active positions
    del self.active_positions[position_id]
    
    # Check for circuit breaker trigger
    if actual_pnl < position.max_loss:
        logger.warning("position_stop_loss_hit",
                      position_id=position_id,
                      pnl=float(actual_pnl),
                      max_loss=float(position.max_loss))
    
    if self.daily_pnl < self.max_daily_loss:
        self.trigger_circuit_breaker("Daily loss limit exceeded")
    
    logger.info("position_closed",
               position_id=position_id,
               pnl=float(actual_pnl),
               daily_pnl=float(self.daily_pnl),
               active_positions=len(self.active_positions))

def get_risk_status(self) -> Dict[str, Any]:
    """Get current risk management status"""
    
    # Calculate utilization ratios
    total_exposure = sum(pos.position_size for pos in self.active_positions.values())
    exposure_utilization = float(total_exposure / self.max_total_exposure) * 100
    
    position_utilization = (len(self.active_positions) / self.max_open_positions) * 100
    daily_volume_utilization = float(self.daily_volume / self.max_daily_volume) * 100
    daily_trades_utilization = (self.daily_trades / self.max_daily_trades) * 100
    
    return {
        'circuit_breaker_active': self.circuit_breaker_active,
        'active_positions': len(self.active_positions),
        'daily_trades': self.daily_trades,
        'daily_volume': float(self.daily_volume),
        'daily_pnl': float(self.daily_pnl),
        'total_exposure': float(total_exposure),
        'utilization': {
            'exposure': exposure_utilization,
            'positions': position_utilization,
            'daily_volume': daily_volume_utilization,
            'daily_trades': daily_trades_utilization
        },
        'exchange_health': {
            name: {
                'healthy': health.is_healthy,
                'reliability_score': health.reliability_score,
                'api_latency': health.api_latency,
                'consecutive_errors': health.consecutive_errors
            }
            for name, health in self.exchange_health.items()
        },
        'risk_stats': self.risk_stats
    }
```