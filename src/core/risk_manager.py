"""
Risk Manager for SmartArb Engine
Comprehensive risk management and position control
"""

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import structlog

from ..strategies.base_strategy import Opportunity

logger = structlog.get_logger(__name__)


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """Current risk metrics"""
    total_exposure: Decimal = Decimal('0')
    daily_pnl: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    open_positions: int = 0
    failed_trades_today: int = 0
    api_error_count: int = 0
    last_successful_trade: float = 0
    
    def get_risk_level(self) -> RiskLevel:
        """Calculate overall risk level"""
        risk_score = 0
        
        # High exposure
        if self.total_exposure > Decimal('5000'):
            risk_score += 3
        elif self.total_exposure > Decimal('2000'):
            risk_score += 2
        elif self.total_exposure > Decimal('1000'):
            risk_score += 1
        
        # Negative PnL
        if self.daily_pnl < Decimal('-100'):
            risk_score += 3
        elif self.daily_pnl < Decimal('-50'):
            risk_score += 2
        elif self.daily_pnl < Decimal('-20'):
            risk_score += 1
        
        # High drawdown
        if self.max_drawdown > Decimal('10'):
            risk_score += 3
        elif self.max_drawdown > Decimal('5'):
            risk_score += 2
        elif self.max_drawdown > Decimal('2'):
            risk_score += 1
        
        # Many failed trades
        if self.failed_trades_today > 10:
            risk_score += 2
        elif self.failed_trades_today > 5:
            risk_score += 1
        
        # API errors
        if self.api_error_count > 20:
            risk_score += 2
        elif self.api_error_count > 10:
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 8:
            return RiskLevel.CRITICAL
        elif risk_score >= 5:
            return RiskLevel.HIGH
        elif risk_score >= 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


@dataclass
class ExposureLimit:
    """Exposure limits for different assets/exchanges"""
    max_position_size: Decimal
    max_daily_volume: Decimal
    max_concurrent_positions: int
    current_exposure: Decimal = Decimal('0')
    daily_volume: Decimal = Decimal('0')
    active_positions: int = 0


class RiskManager:
    """
    Comprehensive risk management system
    
    Features:
    - Position size limits
    - Daily loss limits
    - Exposure tracking
    - Drawdown protection
    - Exchange-specific limits
    - Emergency stop mechanism
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Global risk limits
        self.max_position_size = Decimal(str(config.get('max_position_size', 1000)))
        self.max_daily_loss = Decimal(str(config.get('max_daily_loss', 200)))
        self.min_profit_threshold = Decimal(str(config.get('min_profit_threshold', 0.15)))
        self.max_slippage = Decimal(str(config.get('max_slippage', 0.5)))
        self.max_exposure_per_exchange = Decimal(str(config.get('max_exposure_per_exchange', 500)))
        
        # Exchange-specific limits
        self.exchange_limits = self._parse_exchange_limits(config.get('exchange_limits', {}))
        
        # Emergency controls
        self.emergency_stop = config.get('emergency_stop', True)
        self.emergency_stop_triggered = False
        
        # Risk tracking
        self.risk_metrics = RiskMetrics()
        self.exposure_by_symbol: Dict[str, Decimal] = {}
        self.exposure_by_exchange: Dict[str, ExposureLimit] = {}
        self.daily_trades: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.rejected_opportunities = 0
        self.risk_violations = []
        
        # Initialize exchange limits
        self._initialize_exchange_limits()
        
        logger.info("risk_manager_initialized",
                   max_position=float(self.max_position_size),
                   max_daily_loss=float(self.max_daily_loss),
                   emergency_stop=self.emergency_stop)
    
    def _parse_exchange_limits(self, limits_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Parse exchange-specific limits from config"""
        parsed_limits = {}
        
        for exchange, limits in limits_config.items():
            parsed_limits[exchange] = {
                'max_position': Decimal(str(limits.get('max_position', self.max_position_size))),
                'min_profit': Decimal(str(limits.get('min_profit', self.min_profit_threshold))),
                'max_daily_volume': Decimal(str(limits.get('max_daily_volume', 5000)))
            }
        
        return parsed_limits
    
    def _initialize_exchange_limits(self):
        """Initialize exposure tracking for exchanges"""
        default_limit = ExposureLimit(
            max_position_size=self.max_position_size,
            max_daily_volume=Decimal('5000'),
            max_concurrent_positions=5
        )
        
        # Set default limits for known exchanges
        for exchange in ['kraken', 'bybit', 'mexc']:
            self.exposure_by_exchange[exchange] = ExposureLimit(
                max_position_size=self.exchange_limits.get(exchange, {}).get('max_position', self.max_position_size),
                max_daily_volume=self.exchange_limits.get(exchange, {}).get('max_daily_volume', Decimal('5000')),
                max_concurrent_positions=3
            )
    
    async def validate_opportunity(self, opportunity: Opportunity) -> bool:
        """
        Comprehensive opportunity validation
        
        Args:
            opportunity: Opportunity to validate
            
        Returns:
            bool: True if opportunity passes all risk checks
        """
        try:
            # Emergency stop check
            if self.emergency_stop_triggered:
                self._log_rejection(opportunity, "emergency_stop_active")
                return False
            
            # Basic opportunity validation
            if not await self._validate_basic_requirements(opportunity):
                return False
            
            # Position size validation
            if not self._validate_position_size(opportunity):
                return False
            
            # Exposure validation
            if not self._validate_exposure_limits(opportunity):
                return False
            
            # Profit threshold validation
            if not self._validate_profit_threshold(opportunity):
                return False
            
            # Daily loss protection
            if not self._validate_daily_loss_limit():
                return False
            
            # Risk level validation
            if not self._validate_risk_level():
                return False
            
            logger.debug("opportunity_validated", 
                        opportunity_id=opportunity.opportunity_id,
                        symbol=opportunity.symbol,
                        amount=float(opportunity.amount))
            
            return True
            
        except Exception as e:
            logger.error("risk_validation_failed", 
                        opportunity_id=getattr(opportunity, 'opportunity_id', 'unknown'),
                        error=str(e))
            return False
    
    async def _validate_basic_requirements(self, opportunity: Opportunity) -> bool:
        """Validate basic opportunity requirements"""
        # Amount validation
        if opportunity.amount <= 0:
            self._log_rejection(opportunity, "invalid_amount")
            return False
        
        # Minimum amount check
        if opportunity.amount < Decimal('10'):
            self._log_rejection(opportunity, "amount_too_small")
            return False
        
        # Maximum amount check
        if opportunity.amount > self.max_position_size:
            self._log_rejection(opportunity, "amount_too_large")
            return False
        
        # Opportunity age check
        if opportunity.is_expired(60):  # 60 seconds max age
            self._log_rejection(opportunity, "opportunity_expired")
            return False
        
        return True
    
    def _validate_position_size(self, opportunity: Opportunity) -> bool:
        """Validate position size against limits"""
        # Global position size limit
        if opportunity.amount > self.max_position_size:
            self._log_rejection(opportunity, "exceeds_max_position_size")
            return False
        
        # Strategy-specific limits (if available)
        strategy_limit = self.config.get('strategy_limits', {}).get(opportunity.strategy, {}).get('max_position')
        if strategy_limit and opportunity.amount > Decimal(str(strategy_limit)):
            self._log_rejection(opportunity, "exceeds_strategy_position_limit")
            return False
        
        return True
    
    def _validate_exposure_limits(self, opportunity: Opportunity) -> bool:
        """Validate exposure limits"""
        # Symbol exposure limit
        current_symbol_exposure = self.exposure_by_symbol.get(opportunity.symbol, Decimal('0'))
        if current_symbol_exposure + opportunity.amount > self.max_position_size * 2:
            self._log_rejection(opportunity, "exceeds_symbol_exposure_limit")
            return False
        
        # Exchange exposure limit (for spatial arbitrage)
        if hasattr(opportunity, 'buy_exchange') and hasattr(opportunity, 'sell_exchange'):
            for exchange in [opportunity.buy_exchange, opportunity.sell_exchange]:
                exchange_limit = self.exposure_by_exchange.get(exchange)
                if exchange_limit:
                    if exchange_limit.current_exposure + opportunity.amount > exchange_limit.max_position_size:
                        self._log_rejection(opportunity, f"exceeds_{exchange}_exposure_limit")
                        return False
        
        return True
    
    def _validate_profit_threshold(self, opportunity: Opportunity) -> bool:
        """Validate minimum profit threshold"""
        min_profit = self.min_profit_threshold
        
        # Exchange-specific minimum profit
        if hasattr(opportunity, 'buy_exchange'):
            exchange_limits = self.exchange_limits.get(opportunity.buy_exchange, {})
            min_profit = exchange_limits.get('min_profit', min_profit)
        
        if opportunity.expected_profit_percent < min_profit:
            self._log_rejection(opportunity, "below_profit_threshold")
            return False
        
        return True
    
    def _validate_daily_loss_limit(self) -> bool:
        """Validate daily loss limits"""
        if abs(self.risk_metrics.daily_pnl) > self.max_daily_loss:
            self._trigger_emergency_stop("daily_loss_limit_exceeded")
            return False
        
        return True
    
    def _validate_risk_level(self) -> bool:
        """Validate current risk level"""
        risk_level = self.risk_metrics.get_risk_level()
        
        if risk_level == RiskLevel.CRITICAL:
            self._trigger_emergency_stop("critical_risk_level")
            return False
        
        # Reduce activity at high risk
        if risk_level == RiskLevel.HIGH:
            # Only allow very profitable opportunities
            return False  # For now, block all trades at high risk
        
        return True
    
    def update_exposure(self, symbol: str, exchange: str, amount: Decimal, is_opening: bool = True):
        """Update exposure tracking"""
        multiplier = Decimal('1') if is_opening else Decimal('-1')
        delta = amount * multiplier
        
        # Update symbol exposure
        self.exposure_by_symbol[symbol] = self.exposure_by_symbol.get(symbol, Decimal('0')) + delta
        
        # Update exchange exposure
        if exchange in self.exposure_by_exchange:
            self.exposure_by_exchange[exchange].current_exposure += delta
            if is_opening:
                self.exposure_by_exchange[exchange].active_positions += 1
            else:
                self.exposure_by_exchange[exchange].active_positions = max(0, 
                    self.exposure_by_exchange[exchange].active_positions - 1)
        
        # Update total exposure
        self.risk_metrics.total_exposure += delta
    
    def record_trade_result(self, opportunity: Opportunity, success: bool, 
                          actual_profit: Decimal = Decimal('0'), 
                          actual_loss: Decimal = Decimal('0')):
        """Record trade execution result"""
        trade_record = {
            'timestamp': time.time(),
            'opportunity_id': opportunity.opportunity_id,
            'symbol': opportunity.symbol,
            'amount': float(opportunity.amount),
            'expected_profit': float(opportunity.expected_profit_percent),
            'actual_profit': float(actual_profit),
            'actual_loss': float(actual_loss),
            'success': success
        }
        
        self.daily_trades.append(trade_record)
        
        # Update metrics
        if success:
            self.risk_metrics.daily_pnl += actual_profit
            self.risk_metrics.last_successful_trade = time.time()
        else:
            self.risk_metrics.daily_pnl -= actual_loss
            self.risk_metrics.failed_trades_today += 1
        
        # Update drawdown
        if self.risk_metrics.daily_pnl < Decimal('0'):
            self.risk_metrics.max_drawdown = max(
                self.risk_metrics.max_drawdown,
                abs(self.risk_metrics.daily_pnl)
            )
        
        # Update exposure (close position)
        if hasattr(opportunity, 'buy_exchange'):
            self.update_exposure(opportunity.symbol, opportunity.buy_exchange, 
                               opportunity.amount, is_opening=False)
    
    def _trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop"""
        if not self.emergency_stop_triggered:
            self.emergency_stop_triggered = True
            logger.critical("emergency_stop_triggered", reason=reason)
            
            # Record violation
            self.risk_violations.append({
                'timestamp': time.time(),
                'reason': reason,
                'risk_metrics': {
                    'daily_pnl': float(self.risk_metrics.daily_pnl),
                    'total_exposure': float(self.risk_metrics.total_exposure),
                    'failed_trades': self.risk_metrics.failed_trades_today
                }
            })
    
    def reset_emergency_stop(self):
        """Reset emergency stop (manual intervention)"""
        if self.emergency_stop_triggered:
            self.emergency_stop_triggered = False
            logger.info("emergency_stop_reset")
    
    def _log_rejection(self, opportunity: Opportunity, reason: str):
        """Log opportunity rejection"""
        self.rejected_opportunities += 1
        
        logger.debug("opportunity_rejected",
                    opportunity_id=opportunity.opportunity_id,
                    symbol=opportunity.symbol,
                    amount=float(opportunity.amount),
                    reason=reason)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current risk manager status"""
        return {
            'emergency_stop': self.emergency_stop_triggered,
            'risk_level': self.risk_metrics.get_risk_level().value,
            'total_exposure': float(self.risk_metrics.total_exposure),
            'daily_pnl': float(self.risk_metrics.daily_pnl),
            'max_drawdown': float(self.risk_metrics.max_drawdown),
            'failed_trades_today': self.risk_metrics.failed_trades_today,
            'rejected_opportunities': self.rejected_opportunities,
            'open_positions': self.risk_metrics.open_positions,
            'limits': {
                'max_position_size': float(self.max_position_size),
                'max_daily_loss': float(self.max_daily_loss),
                'min_profit_threshold': float(self.min_profit_threshold)
            }
        }
    
    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of new day)"""
        self.risk_metrics.daily_pnl = Decimal('0')
        self.risk_metrics.failed_trades_today = 0
        self.risk_metrics.max_drawdown = Decimal('0')
        self.daily_trades.clear()
        self.rejected_opportunities = 0
        
        # Reset daily volumes for exchanges
        for exchange_limit in self.exposure_by_exchange.values():
            exchange_limit.daily_volume = Decimal('0')
        
        logger.info("daily_risk_metrics_reset")
