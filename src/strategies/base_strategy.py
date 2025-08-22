“””
Base Strategy Interface for SmartArb Engine
Defines the standard interface that all trading strategies must implement
“””

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
import time
import uuid
import structlog

from ..exchanges.base_exchange import BaseExchange

logger = structlog.get_logger(**name**)

class OpportunityType(Enum):
“”“Types of trading opportunities”””
SPATIAL_ARBITRAGE = “spatial_arbitrage”
TRIANGULAR_ARBITRAGE = “triangular_arbitrage”
STATISTICAL_ARBITRAGE = “statistical_arbitrage”
MOMENTUM = “momentum”
MEAN_REVERSION = “mean_reversion”

class OpportunityStatus(Enum):
“”“Status of trading opportunities”””
DETECTED = “detected”
VALIDATED = “validated”
EXECUTING = “executing”
EXECUTED = “executed”
FAILED = “failed”
EXPIRED = “expired”

@dataclass
class Opportunity:
“””
Base opportunity data structure
All specific opportunity types should inherit from this
“””
opportunity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
strategy_name: str = “”
opportunity_type: OpportunityType = OpportunityType.SPATIAL_ARBITRAGE
status: OpportunityStatus = OpportunityStatus.DETECTED

```
# Basic opportunity data
symbol: str = ""
amount: Decimal = Decimal('0')
expected_profit: Decimal = Decimal('0')
expected_profit_percent: Decimal = Decimal('0')

# Risk metrics
risk_score: float = 0.0  # 0-1 scale
max_drawdown: Decimal = Decimal('0')
confidence_level: float = 0.0  # 0-1 scale

# Timing
timestamp: float = field(default_factory=time.time)
valid_until: float = 0  # Expiration timestamp
execution_time_limit: float = 30  # Max execution time in seconds

# Execution tracking
orders_placed: List[str] = field(default_factory=list)
actual_profit: Decimal = Decimal('0')
execution_start_time: Optional[float] = None
execution_end_time: Optional[float] = None

# Metadata
metadata: Dict[str, Any] = field(default_factory=dict)

def __post_init__(self):
    """Post-initialization setup"""
    if not self.valid_until:
        self.valid_until = self.timestamp + 60  # Default 60 seconds validity

@property
def is_expired(self) -> bool:
    """Check if opportunity has expired"""
    return time.time() > self.valid_until

@property
def is_executing(self) -> bool:
    """Check if opportunity is currently being executed"""
    return self.status == OpportunityStatus.EXECUTING

@property
def execution_duration(self) -> Optional[float]:
    """Get execution duration in seconds"""
    if self.execution_start_time and self.execution_end_time:
        return self.execution_end_time - self.execution_start_time
    return None

@property
def profit_ratio(self) -> Decimal:
    """Calculate actual vs expected profit ratio"""
    if self.expected_profit > 0:
        return self.actual_profit / self.expected_profit
    return Decimal('0')

def update_status(self, status: OpportunityStatus) -> None:
    """Update opportunity status with timing"""
    old_status = self.status
    self.status = status
    
    if status == OpportunityStatus.EXECUTING:
        self.execution_start_time = time.time()
    elif status in [OpportunityStatus.EXECUTED, OpportunityStatus.FAILED]:
        self.execution_end_time = time.time()
    
    logger.info("opportunity_status_changed",
               opportunity_id=self.opportunity_id,
               strategy=self.strategy_name,
               old_status=old_status.value,
               new_status=status.value)

def to_dict(self) -> Dict[str, Any]:
    """Convert opportunity to dictionary"""
    return {
        'opportunity_id': self.opportunity_id,
        'strategy_name': self.strategy_name,
        'opportunity_type': self.opportunity_type.value,
        'status': self.status.value,
        'symbol': self.symbol,
        'amount': float(self.amount),
        'expected_profit': float(self.expected_profit),
        'expected_profit_percent': float(self.expected_profit_percent),
        'actual_profit': float(self.actual_profit),
        'risk_score': self.risk_score,
        'confidence_level': self.confidence_level,
        'timestamp': self.timestamp,
        'valid_until': self.valid_until,
        'execution_duration': self.execution_duration,
        'profit_ratio': float(self.profit_ratio),
        'metadata': self.metadata
    }
```

class BaseStrategy(ABC):
“””
Abstract base class for all trading strategies

```
All strategy implementations must inherit from this class and implement
the abstract methods to ensure consistent interface across strategies.
"""

def __init__(self, name: str, exchanges: Dict[str, BaseExchange], config: Dict[str, Any]):
    """Initialize strategy with configuration"""
    self.name = name
    self.exchanges = exchanges
    self.config = config
    
    # Strategy settings
    self.enabled = config.get('enabled', True)
    self.priority = config.get('priority', 1)
    self.max_position_size = Decimal(str(config.get('max_position_size', 1000)))
    self.min_profit_threshold = Decimal(str(config.get('min_profit_threshold', 0.1)))
    
    # Risk management
    self.max_risk_score = config.get('max_risk_score', 0.8)
    self.min_confidence_level = config.get('min_confidence_level', 0.7)
    self.max_open_positions = config.get('max_open_positions', 5)
    
    # Performance tracking
    self.opportunities_detected = 0
    self.opportunities_executed = 0
    self.total_profit = Decimal('0')
    self.total_loss = Decimal('0')
    self.active_opportunities: Dict[str, Opportunity] = {}
    
    # Timing
    self.last_scan_time = 0
    self.scan_frequency = config.get('scan_frequency', 5)  # seconds
    
    logger.info("strategy_initialized",
               name=self.name,
               enabled=self.enabled,
               priority=self.priority)

# Abstract Methods (must be implemented by subclasses)
@abstractmethod
async def find_opportunities(self) -> List[Opportunity]:
    """
    Scan markets and identify trading opportunities
    
    Returns:
        List of opportunities found during this scan
    """
    pass

@abstractmethod
async def validate_opportunity(self, opportunity: Opportunity) -> bool:
    """
    Validate an opportunity before execution
    
    Args:
        opportunity: The opportunity to validate
        
    Returns:
        True if opportunity is valid and should be executed
    """
    pass

@abstractmethod
async def estimate_profit(self, opportunity: Opportunity) -> Decimal:
    """
    Estimate potential profit for an opportunity
    
    Args:
        opportunity: The opportunity to estimate
        
    Returns:
        Estimated profit in base currency (usually USDT)
    """
    pass

# Concrete Methods (can be overridden by subclasses)
async def scan_markets(self) -> List[Opportunity]:
    """
    Main scanning method that coordinates the scanning process
    """
    if not self.enabled:
        return []
    
    # Check if enough time has passed since last scan
    now = time.time()
    if now - self.last_scan_time < self.scan_frequency:
        return []
    
    try:
        logger.debug("scanning_markets", strategy=self.name)
        
        # Find opportunities using strategy-specific logic
        opportunities = await self.find_opportunities()
        
        # Filter and enhance opportunities
        valid_opportunities = []
        for opp in opportunities:
            if await self._pre_validate_opportunity(opp):
                # Estimate profit
                opp.expected_profit = await self.estimate_profit(opp)
                
                # Calculate profit percentage
                if opp.amount > 0:
                    opp.expected_profit_percent = (opp.expected_profit / (opp.amount * 100))
                
                # Set strategy name
                opp.strategy_name = self.name
                
                valid_opportunities.append(opp)
                self.opportunities_detected += 1
        
        self.last_scan_time = now
        
        if valid_opportunities:
            logger.info("opportunities_found",
                       strategy=self.name,
                       count=len(valid_opportunities),
                       total_profit=sum(float(o.expected_profit) for o in valid_opportunities))
        
        return valid_opportunities
        
    except Exception as e:
        logger.error("scanning_error", strategy=self.name, error=str(e))
        return []

async def _pre_validate_opportunity(self, opportunity: Opportunity) -> bool:
    """
    Pre-validation checks before detailed validation
    """
    # Check if opportunity has expired
    if opportunity.is_expired:
        logger.debug("opportunity_expired", opportunity_id=opportunity.opportunity_id)
        return False
    
    # Check minimum profit threshold
    estimated_profit = await self.estimate_profit(opportunity)
    if estimated_profit < self.min_profit_threshold:
        logger.debug("profit_below_threshold",
                    opportunity_id=opportunity.opportunity_id,
                    profit=float(estimated_profit),
                    threshold=float(self.min_profit_threshold))
        return False
    
    # Check position size limits
    if opportunity.amount > self.max_position_size:
        logger.debug("position_size_too_large",
                    opportunity_id=opportunity.opportunity_id,
                    amount=float(opportunity.amount),
                    max_size=float(self.max_position_size))
        return False
    
    # Check risk score
    if opportunity.risk_score > self.max_risk_score:
        logger.debug("risk_score_too_high",
                    opportunity_id=opportunity.opportunity_id,
                    risk_score=opportunity.risk_score,
                    max_risk=self.max_risk_score)
        return False
    
    # Check confidence level
    if opportunity.confidence_level < self.min_confidence_level:
        logger.debug("confidence_too_low",
                    opportunity_id=opportunity.opportunity_id,
                    confidence=opportunity.confidence_level,
                    min_confidence=self.min_confidence_level)
        return False
    
    # Check max open positions
    if len(self.active_opportunities) >= self.max_open_positions:
        logger.debug("max_positions_reached",
                    strategy=self.name,
                    active=len(self.active_opportunities),
                    max_positions=self.max_open_positions)
        return False
    
    return True

def add_active_opportunity(self, opportunity: Opportunity) -> None:
    """Add opportunity to active tracking"""
    self.active_opportunities[opportunity.opportunity_id] = opportunity
    logger.info("opportunity_activated",
               strategy=self.name,
               opportunity_id=opportunity.opportunity_id,
               active_count=len(self.active_opportunities))

def remove_active_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
    """Remove opportunity from active tracking"""
    opportunity = self.active_opportunities.pop(opportunity_id, None)
    if opportunity:
        logger.info("opportunity_deactivated",
                   strategy=self.name,
                   opportunity_id=opportunity_id,
                   active_count=len(self.active_opportunities))
    return opportunity

def update_performance(self, opportunity: Opportunity) -> None:
    """Update strategy performance metrics"""
    if opportunity.status == OpportunityStatus.EXECUTED:
        self.opportunities_executed += 1
        if opportunity.actual_profit > 0:
            self.total_profit += opportunity.actual_profit
        else:
            self.total_loss += abs(opportunity.actual_profit)

def get_performance_stats(self) -> Dict[str, Any]:
    """Get strategy performance statistics"""
    success_rate = 0.0
    if self.opportunities_detected > 0:
        success_rate = (self.opportunities_executed / self.opportunities_detected) * 100
    
    return {
        'strategy_name': self.name,
        'enabled': self.enabled,
        'priority': self.priority,
        'opportunities_detected': self.opportunities_detected,
        'opportunities_executed': self.opportunities_executed,
        'success_rate': success_rate,
        'total_profit': float(self.total_profit),
        'total_loss': float(self.total_loss),
        'net_profit': float(self.total_profit - self.total_loss),
        'active_opportunities': len(self.active_opportunities),
        'last_scan_time': self.last_scan_time
    }

def get_config(self) -> Dict[str, Any]:
    """Get strategy configuration"""
    return {
        'name': self.name,
        'enabled': self.enabled,
        'priority': self.priority,
        'max_position_size': float(self.max_position_size),
        'min_profit_threshold': float(self.min_profit_threshold),
        'max_risk_score': self.max_risk_score,
        'min_confidence_level': self.min_confidence_level,
        'max_open_positions': self.max_open_positions,
        'scan_frequency': self.scan_frequency
    }

def update_config(self, new_config: Dict[str, Any]) -> None:
    """Update strategy configuration dynamically"""
    for key, value in new_config.items():
        if hasattr(self, key):
            if key in ['max_position_size', 'min_profit_threshold']:
                setattr(self, key, Decimal(str(value)))
            else:
                setattr(self, key, value)
                
    logger.info("strategy_config_updated", strategy=self.name, config=new_config)

def __str__(self) -> str:
    """String representation"""
    return f"{self.name}Strategy(enabled={self.enabled}, active={len(self.active_opportunities)})"

def __repr__(self) -> str:
    """Detailed string representation"""
    return (f"{self.name}Strategy(enabled={self.enabled}, "
            f"detected={self.opportunities_detected}, "
            f"executed={self.opportunities_executed}, "
            f"profit={float(self.total_profit):.2f})")
```