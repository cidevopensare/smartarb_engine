"""
Base Strategy Interface for SmartArb Engine
Provides abstract interface for all trading strategies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from decimal import Decimal
from enum import Enum
import time
import uuid


class OpportunityStatus(Enum):
    DETECTED = "detected"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class Opportunity:
    """Base opportunity data structure"""
    strategy: str
    symbol: str
    amount: Decimal
    expected_profit_percent: Decimal
    opportunity_id: str = ""
    timestamp: float = field(default_factory=time.time)
    status: OpportunityStatus = OpportunityStatus.DETECTED
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.opportunity_id:
            self.opportunity_id = f"{self.strategy}_{self.symbol}_{uuid.uuid4().hex[:8]}"
    
    @property
    def expected_profit_amount(self) -> Decimal:
        """Calculate expected profit in absolute terms"""
        return (self.amount * self.expected_profit_percent) / 100
    
    @property
    def age_seconds(self) -> float:
        """Get opportunity age in seconds"""
        return time.time() - self.timestamp
    
    def is_expired(self, max_age_seconds: float = 60) -> bool:
        """Check if opportunity has expired"""
        return self.age_seconds > max_age_seconds


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    
    Provides common interface and utilities for:
    - Opportunity detection
    - Validation logic
    - Performance tracking
    - Configuration management
    """
    
    def __init__(self, name: str, exchanges: Dict[str, Any], config: Dict[str, Any]):
        self.name = name
        self.exchanges = exchanges
        self.config = config
        
        # Strategy state
        self.enabled = config.get('enabled', True)
        self.max_concurrent_opportunities = config.get('max_concurrent', 3)
        
        # Performance tracking
        self.total_opportunities_found = 0
        self.total_opportunities_executed = 0
        self.total_profit = Decimal('0')
        self.last_scan_time = 0
        self.scan_duration_ms = 0
        
        # Active opportunities tracking
        self.active_opportunities: Dict[str, Opportunity] = {}
        
    @abstractmethod
    async def find_opportunities(self) -> List[Opportunity]:
        """
        Scan markets and return list of opportunities
        
        Returns:
            List[Opportunity]: List of detected opportunities
        """
        pass
    
    async def validate_opportunity(self, opportunity: Opportunity) -> bool:
        """
        Validate opportunity before execution
        Default implementation - override for strategy-specific validation
        
        Args:
            opportunity: Opportunity to validate
            
        Returns:
            bool: True if opportunity is valid for execution
        """
        # Basic validation
        if opportunity.is_expired():
            return False
        
        if opportunity.amount <= 0:
            return False
        
        if opportunity.expected_profit_percent <= 0:
            return False
        
        return True
    
    async def scan_and_validate(self) -> List[Opportunity]:
        """
        Scan for opportunities and validate them
        
        Returns:
            List[Opportunity]: List of valid opportunities ready for execution
        """
        start_time = time.time()
        
        try:
            # Find raw opportunities
            opportunities = await self.find_opportunities()
            self.total_opportunities_found += len(opportunities)
            
            # Validate each opportunity
            valid_opportunities = []
            for opportunity in opportunities:
                if await self.validate_opportunity(opportunity):
                    valid_opportunities.append(opportunity)
                    opportunity.status = OpportunityStatus.VALIDATING
            
            # Track performance
            self.last_scan_time = time.time()
            self.scan_duration_ms = (self.last_scan_time - start_time) * 1000
            
            return valid_opportunities
            
        except Exception as e:
            import structlog
            logger = structlog.get_logger(__name__)
            logger.error("strategy_scan_failed", strategy=self.name, error=str(e))
            return []
    
    def add_active_opportunity(self, opportunity: Opportunity):
        """Add opportunity to active tracking"""
        self.active_opportunities[opportunity.opportunity_id] = opportunity
    
    def remove_active_opportunity(self, opportunity_id: str):
        """Remove opportunity from active tracking"""
        self.active_opportunities.pop(opportunity_id, None)
    
    def get_active_count(self) -> int:
        """Get number of active opportunities"""
        return len(self.active_opportunities)
    
    def can_take_opportunity(self) -> bool:
        """Check if strategy can take on more opportunities"""
        return self.get_active_count() < self.max_concurrent_opportunities
    
    def record_execution_result(self, opportunity: Opportunity, success: bool, profit: Decimal = Decimal('0')):
        """Record execution result for performance tracking"""
        if success:
            self.total_opportunities_executed += 1
            self.total_profit += profit
            opportunity.status = OpportunityStatus.COMPLETED
        else:
            opportunity.status = OpportunityStatus.FAILED
        
        # Remove from active tracking
        self.remove_active_opportunity(opportunity.opportunity_id)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get strategy performance statistics"""
        success_rate = 0
        if self.total_opportunities_found > 0:
            success_rate = (self.total_opportunities_executed / self.total_opportunities_found) * 100
        
        return {
            'strategy_name': self.name,
            'enabled': self.enabled,
            'opportunities_found': self.total_opportunities_found,
            'opportunities_executed': self.total_opportunities_executed,
            'success_rate_percent': success_rate,
            'total_profit': float(self.total_profit),
            'average_profit_per_trade': float(self.total_profit / max(self.total_opportunities_executed, 1)),
            'active_opportunities': self.get_active_count(),
            'last_scan_duration_ms': self.scan_duration_ms,
            'last_scan_time': self.last_scan_time
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current strategy status"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'active_opportunities': self.get_active_count(),
            'max_concurrent': self.max_concurrent_opportunities,
            'can_take_more': self.can_take_opportunity(),
            'last_scan': self.last_scan_time,
            'scan_duration_ms': self.scan_duration_ms
        }
    
    def cleanup_expired_opportunities(self, max_age_seconds: float = 300):
        """Remove expired opportunities from active tracking"""
        expired_ids = []
        for opp_id, opportunity in self.active_opportunities.items():
            if opportunity.is_expired(max_age_seconds):
                expired_ids.append(opp_id)
                opportunity.status = OpportunityStatus.EXPIRED
        
        for opp_id in expired_ids:
            self.remove_active_opportunity(opp_id)
        
        return len(expired_ids)
    
    def __str__(self):
        return f"{self.name} Strategy ({'Enabled' if self.enabled else 'Disabled'})"
