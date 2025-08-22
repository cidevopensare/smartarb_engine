“””
Strategy Manager for SmartArb Engine
Complete implementation for managing multiple trading strategies and coordinating their execution
“””

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import time
from datetime import datetime, timedelta
import structlog

from ..exchanges.base_exchange import BaseExchange
from ..strategies.base_strategy import BaseStrategy, Opportunity, OpportunityStatus
from ..strategies.spatial_arbitrage import SpatialArbitrageStrategy
from .risk_manager import RiskManager, RiskAssessment
from .execution_engine import ExecutionEngine, ExecutionResult

logger = structlog.get_logger(**name**)

class StrategyManager:
“””
Strategy Management System

```
Features:
- Multiple strategy coordination
- Opportunity prioritization and filtering
- Execution scheduling and management
- Performance monitoring and analytics
- Resource allocation and limits
- Strategy configuration management
"""

def __init__(self, exchanges: Dict[str, BaseExchange], risk_manager: RiskManager,
             execution_engine: ExecutionEngine, config: Dict[str, Any]):
    self.exchanges = exchanges
    self.risk_manager = risk_manager
    self.execution_engine = execution_engine
    self.config = config
    
    # Strategy registry
    self.strategies: Dict[str, BaseStrategy] = {}
    self.enabled_strategies: List[str] = []
    
    # Execution control
    strategy_config = config.get('strategies', {})
    self.max_concurrent_opportunities = config.get('engine', {}).get('max_concurrent_opportunities', 3)
    self.scan_interval = strategy_config.get('scan_interval', 5)  # seconds
    self.opportunity_timeout = strategy_config.get('opportunity_timeout', 60)  # seconds
    
    # Performance tracking
    self.total_opportunities_found = 0
    self.total_opportunities_executed = 0
    self.total_profit = Decimal('0')
    self.total_loss = Decimal('0')
    
    # Active opportunity management
    self.active_opportunities: Dict[str, Opportunity] = {}
    self.execution_queue: List[str] = []  # Opportunity IDs in execution queue
    self.executing_opportunities: Dict[str, asyncio.Task] = {}
    
    # Strategy performance tracking
    self.strategy_performance: Dict[str, Dict[str, Any]] = {}
    
    # Last scan time tracking
    self.last_scan_times: Dict[str, float] = {}
    
    # Initialize strategies
    self._initialize_strategies()
    
    logger.info("strategy_manager_initialized",
               total_strategies=len(self.strategies),
               enabled_strategies=len(self.enabled_strategies),
               max_concurrent=self.max_concurrent_opportunities)

def _initialize_strategies(self) -> None:
    """Initialize and register trading strategies"""
    
    strategies_config = self.config.get('strategies', {})
    
    # Initialize Spatial Arbitrage Strategy
    spatial_config = strategies_config.get('spatial_arbitrage', {})
    if spatial_config.get('enabled', True):
        spatial_strategy = SpatialArbitrageStrategy(self.exchanges, spatial_config)
        self.register_strategy(spatial_strategy)
        self.enabled_strategies.append('spatial_arbitrage')
        logger.info("spatial_arbitrage_strategy_registered")
    
    # Add other strategies here as they are implemented
    # triangular_config = strategies_config.get('triangular_arbitrage', {})
    # if triangular_config.get('enabled', False):
    #     triangular_strategy = TriangularArbitrageStrategy(self.exchanges, triangular_config)
    #     self.register_strategy(triangular_strategy)
    
    # Initialize performance tracking for all strategies
    for strategy_name in self.strategies.keys():
        self.strategy_performance[strategy_name] = {
            'opportunities_found': 0,
            'opportunities_executed': 0,
            'total_profit': Decimal('0'),
            'total_loss': Decimal('0'),
            'success_rate': 0.0,
            'avg_profit_per_trade': Decimal('0'),
            'last_opportunity_time': 0,
            'execution_times': [],
            'error_count': 0
        }

def register_strategy(self, strategy: BaseStrategy) -> None:
    """Register a new trading strategy"""
    self.strategies[strategy.name] = strategy
    self.last_scan_times[strategy.name] = 0
    
    logger.info("strategy_registered",
               strategy_name=strategy.name,
               enabled=strategy.enabled,
               priority=strategy.priority)

def unregister_strategy(self, strategy_name: str) -> bool:
    """Unregister a trading strategy"""
    if strategy_name in self.strategies:
        del self.strategies[strategy_name]
        if strategy_name in self.enabled_strategies:
            self.enabled_strategies.remove(strategy_name)
        if strategy_name in self.last_scan_times:
            del self.last_scan_times[strategy_name]
        
        logger.info("strategy_unregistered", strategy_name=strategy_name)
        return True
    return False

async def scan_markets(self) -> List[Opportunity]:
    """Scan markets for opportunities across all enabled strategies"""
    
    all_opportunities = []
    scan_tasks = []
    
    try:
        # Create scan tasks for each enabled strategy
        for strategy_name in self.enabled_strategies:
            strategy = self.strategies.get(strategy_name)
            if not strategy or not strategy.enabled:
                continue
            
            # Check if enough time has passed since last scan
            now = time.time()
            last_scan = self.last_scan_times.get(strategy_name, 0)
            if now - last_scan < strategy.scan_frequency:
                continue
            
            # Create scan task
            task = asyncio.create_task(self._scan_strategy(strategy_name, strategy))
            scan_tasks.append(task)
        
        if not scan_tasks:
            return all_opportunities
        
        # Execute all scans concurrently
        scan_results = await asyncio.gather(*scan_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(scan_results):
            if isinstance(result, Exception):
                strategy_name = list(self.enabled_strategies)[i]
                logger.error("strategy_scan_failed",
                           strategy_name=strategy_name,
                           error=str(result))
                self._update_strategy_error_count(strategy_name)
            elif result:
                strategy_name, opportunities = result
                all_opportunities.extend(opportunities)
                self._update_strategy_performance(strategy_name, len(opportunities))
        
        # Filter and prioritize opportunities
        if all_opportunities:
            all_opportunities = await self._filter_and_prioritize_opportunities(all_opportunities)
        
        logger.info("market_scan_completed",
                   strategies_scanned=len(scan_tasks),
                   opportunities_found=len(all_opportunities))
        
        return all_opportunities
        
    except Exception as e:
        logger.error("market_scan_failed", error=str(e))
        return []

async def _scan_strategy(self, strategy_name: str, strategy: BaseStrategy) -> Optional[Tuple[str, List[Opportunity]]]:
    """Scan a single strategy for opportunities"""
    try:
        start_time = time.time()
        
        # Perform strategy scan
        opportunities = await strategy.scan_markets()
        
        # Update scan time
        self.last_scan_times[strategy_name] = time.time()
        
        # Log scan performance
        scan_duration = time.time() - start_time
        logger.debug("strategy_scan_completed",
                    strategy_name=strategy_name,
                    opportunities=len(opportunities),
                    scan_duration=scan_duration)
        
        return strategy_name, opportunities
        
    except Exception as e:
        logger.error("strategy_scan_error",
                    strategy_name=strategy_name,
                    error=str(e))
        raise e

async def _filter_and_prioritize_opportunities(self, opportunities: List[Opportunity]) -> List[Opportunity]:
    """Filter and prioritize opportunities"""
    
    if not opportunities:
        return []
    
    # Remove expired opportunities
    valid_opportunities = [
        opp for opp in opportunities 
        if not opp.is_expired
    ]
    
    if not valid_opportunities:
        logger.debug("all_opportunities_expired", 
                    total=len(opportunities))
        return []
    
    # Filter by risk assessment
    risk_filtered = []
    for opportunity in valid_opportunities:
        try:
            # Quick risk check
            if (opportunity.risk_score <= 0.8 and 
                opportunity.confidence_level >= 0.6 and
                opportunity.expected_profit > 0):
                risk_filtered.append(opportunity)
                
        except Exception as e:
            logger.warning("opportunity_risk_filter_failed",
                         opportunity_id=opportunity.opportunity_id,
                         error=str(e))
    
    # Sort by expected profit (descending)
    risk_filtered.sort(key=lambda o: float(o.expected_profit), reverse=True)
    
    # Limit to maximum concurrent opportunities
    final_opportunities = risk_filtered[:self.max_concurrent_opportunities]
    
    logger.info("opportunities_filtered_and_prioritized",
               initial_count=len(opportunities),
               valid_count=len(valid_opportunities),
               risk_filtered_count=len(risk_filtered),
               final_count=len(final_opportunities))
    
    return final_opportunities

async def execute_opportunity(self, opportunity: Opportunity) -> Optional[Dict[str, Any]]:
    """Execute a single trading opportunity"""
    
    opportunity_id = opportunity.opportunity_id
    
    try:
        logger.info("opportunity_execution_started",
                   opportunity_id=opportunity_id,
                   strategy=opportunity.strategy_name,
                   symbol=opportunity.symbol,
                   expected_profit=float(opportunity.expected_profit))
        
        # Add to active opportunities
        self.active_opportunities[opportunity_id] = opportunity
        
        # Validate opportunity
        strategy = self.strategies.get(opportunity.strategy_name)
        if not strategy:
            raise ValueError(f"Strategy {opportunity.strategy_name} not found")
        
        if not await strategy.validate_opportunity(opportunity):
            opportunity.update_status(OpportunityStatus.FAILED)
            return {'success': False, 'reason': 'Validation failed'}
        
        # Risk assessment
        risk_assessment = await self.risk_manager.assess_opportunity_risk(opportunity)
        
        if not risk_assessment.is_acceptable:
            opportunity.update_status(OpportunityStatus.FAILED)
            logger.warning("opportunity_rejected_by_risk_manager",
                         opportunity_id=opportunity_id,
                         risk_level=risk_assessment.risk_level.value,
                         violations=len(risk_assessment.violations))
            return {
                'success': False, 
                'reason': 'Risk assessment failed',
                'risk_assessment': risk_assessment
            }
        
        # Add position to risk manager
        await self.risk_manager.add_position(opportunity)
        
        # Execute opportunity
        execution_result = await self.execution_engine.execute_opportunity(opportunity, risk_assessment)
        
        # Process execution result
        result = await self._process_execution_result(opportunity, execution_result)
        
        # Update performance metrics
        self._update_execution_performance(opportunity, execution_result)
        
        return result
        
    except Exception as e:
        logger.error("opportunity_execution_failed",
                    opportunity_id=opportunity_id,
                    error=str(e))
        
        # Clean up
        opportunity.update_status(OpportunityStatus.FAILED)
        await self._cleanup_failed_opportunity(opportunity)
        
        return {'success': False, 'reason': str(e)}
    
    finally:
        # Remove from active opportunities
        if opportunity_id in self.active_opportunities:
            del self.active_opportunities[opportunity_id]

async def _process_execution_result(self, opportunity: Opportunity, 
                                  execution_result: ExecutionResult) -> Dict[str, Any]:
    """Process the result of opportunity execution"""
    
    opportunity_id = opportunity.opportunity_id
    
    try:
        if execution_result.success_rate >= 100:
            # Successful execution
            opportunity.update_status(OpportunityStatus.EXECUTED)
            opportunity.actual_profit = execution_result.actual_profit
            
            # Update risk manager
            await self.risk_manager.update_position_pnl(
                opportunity_id, 
                execution_result.actual_profit
            )
            
            # Update totals
            self.total_opportunities_executed += 1
            if execution_result.actual_profit > 0:
                self.total_profit += execution_result.actual_profit
            else:
                self.total_loss += abs(execution_result.actual_profit)
            
            logger.info("opportunity_executed_successfully",
                       opportunity_id=opportunity_id,
                       actual_profit=float(execution_result.actual_profit),
                       execution_time=execution_result.execution_time)
            
            return {
                'success': True,
                'profit': float(execution_result.actual_profit),
                'execution_time': execution_result.execution_time,
                'fees_paid': float(execution_result.fees_paid),
                'orders_executed': len(execution_result.executed_orders),
                'execution_result': execution_result
            }
        
        else:
            # Partial or failed execution
            opportunity.update_status(OpportunityStatus.FAILED)
            
            # Handle partial execution
            if execution_result.success_rate > 0:
                logger.warning("opportunity_partially_executed",
                             opportunity_id=opportunity_id,
                             success_rate=execution_result.success_rate,
                             actual_profit=float(execution_result.actual_profit))
            else:
                logger.error("opportunity_execution_completely_failed",
                           opportunity_id=opportunity_id,
                           error=execution_result.error_message)
            
            # Update risk manager
            await self.risk_manager.update_position_pnl(
                opportunity_id, 
                execution_result.actual_profit
            )
            
            return {
                'success': False,
                'profit': float(execution_result.actual_profit),
                'execution_time': execution_result.execution_time,
                'success_rate': execution_result.success_rate,
                'error': execution_result.error_message,
                'execution_result': execution_result
            }
            
    except Exception as e:
        logger.error("execution_result_processing_failed",
                    opportunity_id=opportunity_id,
                    error=str(e))
        return {'success': False, 'reason': f'Result processing failed: {str(e)}'}
    
    finally:
        # Remove position from risk manager
        await self.risk_manager.remove_position(opportunity_id)

async def _cleanup_failed_opportunity(self, opportunity: Opportunity) -> None:
    """Clean up after a failed opportunity"""
    try:
        # Remove from risk manager if it was added
        await self.risk_manager.remove_position(opportunity.opportunity_id)
        
        # Update strategy performance
        strategy_name = opportunity.strategy_name
        if strategy_name in self.strategy_performance:
            self.strategy_performance[strategy_name]['error_count'] += 1
        
    except Exception as e:
        logger.warning("opportunity_cleanup_failed",
                      opportunity_id=opportunity.opportunity_id,
                      error=str(e))

def _update_strategy_performance(self, strategy_name: str, opportunities_found: int) -> None:
    """Update strategy performance metrics"""
    if strategy_name not in self.strategy_performance:
        return
    
    performance = self.strategy_performance[strategy_name]
    performance['opportunities_found'] += opportunities_found
    performance['last_opportunity_time'] = time.time()
    
    self.total_opportunities_found += opportunities_found

def _update_execution_performance(self, opportunity: Opportunity, result: ExecutionResult) -> None:
    """Update execution performance metrics"""
    strategy_name = opportunity.strategy_name
    if strategy_name not in self.strategy_performance:
        return
    
    performance = self.strategy_performance[strategy_name]
    
    if result.success_rate >= 100:
        performance['opportunities_executed'] += 1
        
        if result.actual_profit > 0:
            performance['total_profit'] += result.actual_profit
        else:
            performance['total_loss'] += abs(result.actual_profit)
    
    # Update success rate
    if performance['opportunities_found'] > 0:
        performance['success_rate'] = (
            performance['opportunities_executed'] / performance['opportunities_found'] * 100
        )
    
    # Update average profit per trade
    if performance['opportunities_executed'] > 0:
        net_profit = performance['total_profit'] - performance['total_loss']
        performance['avg_profit_per_trade'] = net_profit / performance['opportunities_executed']
    
    # Track execution times
    performance['execution_times'].append(result.execution_time)
    if len(performance['execution_times']) > 100:  # Keep last 100
        performance['execution_times'] = performance['execution_times'][-100:]

def _update_strategy_error_count(self, strategy_name: str) -> None:
    """Update strategy error count"""
    if strategy_name in self.strategy_performance:
        self.strategy_performance[strategy_name]['error_count'] += 1

# Management and control methods
def enable_strategy(self, strategy_name: str) -> bool:
    """Enable a strategy"""
    if strategy_name in self.strategies:
        strategy = self.strategies[strategy_name]
        strategy.enabled = True
        if strategy_name not in self.enabled_strategies:
            self.enabled_strategies.append(strategy_name)
        
        logger.info("strategy_enabled", strategy_name=strategy_name)
        return True
    return False

def disable_strategy(self, strategy_name: str) -> bool:
    """Disable a strategy"""
    if strategy_name in self.strategies:
        strategy = self.strategies[strategy_name]
        strategy.enabled = False
        if strategy_name in self.enabled_strategies:
            self.enabled_strategies.remove(strategy_name)
        
        logger.info("strategy_disabled", strategy_name=strategy_name)
        return True
    return False

def update_strategy_config(self, strategy_name: str, new_config: Dict[str, Any]) -> bool:
    """Update strategy configuration"""
    if strategy_name not in self.strategies:
        return False
    
    try:
        strategy = self.strategies[strategy_name]
        strategy.update_config(new_config)
        
        logger.info("strategy_config_updated",
                   strategy_name=strategy_name,
                   config=new_config)
        return True
        
    except Exception as e:
        logger.error("strategy_config_update_failed",
                    strategy_name=strategy_name,
                    error=str(e))
        return False

async def cancel_active_opportunities(self, strategy_name: Optional[str] = None) -> int:
    """Cancel active opportunities, optionally filtered by strategy"""
    cancelled_count = 0
    
    opportunities_to_cancel = []
    for opp_id, opportunity in self.active_opportunities.items():
        if strategy_name is None or opportunity.strategy_name == strategy_name:
            opportunities_to_cancel.append(opp_id)
    
    for opp_id in opportunities_to_cancel:
        try:
            # Cancel execution if running
            if opp_id in self.executing_opportunities:
                task = self.executing_opportunities[opp_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Update opportunity status
            opportunity = self.active_opportunities.get(opp_id)
            if opportunity:
                opportunity.update_status(OpportunityStatus.FAILED)
            
            # Clean up
            await self._cleanup_failed_opportunity(opportunity)
            cancelled_count += 1
            
        except Exception as e:
            logger.error("opportunity_cancellation_failed",
                       opportunity_id=opp_id,
                       error=str(e))
    
    logger.info("active_opportunities_cancelled",
               count=cancelled_count,
               strategy_filter=strategy_name)
    
    return cancelled_count

# Status and reporting methods
async def get_strategy_stats(self) -> Dict[str, Any]:
    """Get comprehensive strategy statistics"""
    
    # Overall statistics
    overall_stats = {
        'total_strategies': len(self.strategies),
        'enabled_strategies': len(self.enabled_strategies),
        'total_opportunities_found': self.total_opportunities_found,
        'total_opportunities_executed': self.total_opportunities_executed,
        'total_profit': float(self.total_profit),
        'total_loss': float(self.total_loss),
        'net_profit': float(self.total_profit - self.total_loss),
        'overall_success_rate': (
            self.total_opportunities_executed / max(self.total_opportunities_found, 1) * 100
        ),
        'active_opportunities': len(self.active_opportunities),
        'max_concurrent_opportunities': self.max_concurrent_opportunities
    }
    
    # Individual strategy statistics
    strategy_stats = {}
    for strategy_name, strategy in self.strategies.items():
        performance = self.strategy_performance.get(strategy_name, {})
        
        # Get strategy-specific stats
        strategy_specific_stats = {}
        if hasattr(strategy, 'get_strategy_stats'):
            strategy_specific_stats = strategy.get_strategy_stats()
        
        # Calculate average execution time
        avg_execution_time = 0.0
        execution_times = performance.get('execution_times', [])
        if execution_times:
            avg_execution_time = sum(execution_times) / len(execution_times)
        
        strategy_stats[strategy_name] = {
            'enabled': strategy.enabled,
            'priority': strategy.priority,
            'opportunities_found': performance.get('opportunities_found', 0),
            'opportunities_executed': performance.get('opportunities_executed', 0),
            'total_profit': float(performance.get('total_profit', 0)),
            'total_loss': float(performance.get('total_loss', 0)),
            'net_profit': float(
                performance.get('total_profit', 0) - performance.get('total_loss', 0)
            ),
            'success_rate': performance.get('success_rate', 0.0),
            'avg_profit_per_trade': float(performance.get('avg_profit_per_trade', 0)),
            'avg_execution_time': avg_execution_time,
            'error_count': performance.get('error_count', 0),
            'last_scan_time': self.last_scan_times.get(strategy_name, 0),
            'strategy_specific': strategy_specific_stats
        }
    
    return {
        'overall': overall_stats,
        'strategies': strategy_stats,
        'timestamp': time.time()
    }

async def get_detailed_stats(self) -> Dict[str, Any]:
    """Get detailed statistics for analysis"""
    stats = await self.get_strategy_stats()
    
    # Add detailed information
    stats['detailed'] = {
        'active_opportunities': [
            {
                'opportunity_id': opp.opportunity_id,
                'strategy': opp.strategy_name,
                'symbol': opp.symbol,
                'expected_profit': float(opp.expected_profit),
                'confidence_level': opp.confidence_level,
                'risk_score': opp.risk_score,
                'time_remaining': max(0, opp.valid_until - time.time())
            }
            for opp in self.active_opportunities.values()
        ],
        'strategy_configs': {
            name: strategy.get_config() 
            for name, strategy in self.strategies.items()
        },
        'execution_queue_size': len(self.execution_queue),
        'executing_count': len(self.executing_opportunities)
    }
    
    return stats

def get_active_opportunities(self) -> List[Dict[str, Any]]:
    """Get list of currently active opportunities"""
    return [
        {
            'opportunity_id': opp.opportunity_id,
            'strategy_name': opp.strategy_name,
            'symbol': opp.symbol,
            'amount': float(opp.amount),
            'expected_profit': float(opp.expected_profit),
            'expected_profit_percent': float(opp.expected_profit_percent),
            'confidence_level': opp.confidence_level,
            'risk_score': opp.risk_score,
            'status': opp.status.value,
            'timestamp': opp.timestamp,
            'valid_until': opp.valid_until,
            'time_remaining': max(0, opp.valid_until - time.time())
        }
        for opp in self.active_opportunities.values()
    ]

def get_strategy_list(self) -> List[Dict[str, Any]]:
    """Get list of all strategies with their basic info"""
    return [
        {
            'name': strategy.name,
            'enabled': strategy.enabled,
            'priority': strategy.priority,
            'type': type(strategy).__name__,
            'last_scan': self.last_scan_times.get(strategy.name, 0),
            'scan_frequency': strategy.scan_frequency,
            'opportunities_found': self.strategy_performance.get(strategy.name, {}).get('opportunities_found', 0),
            'opportunities_executed': self.strategy_performance.get(strategy.name, {}).get('opportunities_executed', 0)
        }
        for strategy in self.strategies.values()
    ]

async def emergency_stop_all_strategies(self) -> None:
    """Emergency stop all strategy operations"""
    logger.critical("emergency_stop_all_strategies_triggered")
    
    try:
        # Disable all strategies
        for strategy_name in list(self.enabled_strategies):
            self.disable_strategy(strategy_name)
        
        # Cancel all active opportunities
        cancelled_count = await self.cancel_active_opportunities()
        
        logger.critical("emergency_stop_completed",
                       strategies_disabled=len(self.strategies),
                       opportunities_cancelled=cancelled_count)
        
    except Exception as e:
        logger.critical("emergency_stop_failed", error=str(e))

def reset_performance_metrics(self) -> None:
    """Reset all performance metrics"""
    self.total_opportunities_found = 0
    self.total_opportunities_executed = 0
    self.total_profit = Decimal('0')
    self.total_loss = Decimal('0')
    
    # Reset strategy performance
    for strategy_name in self.strategy_performance:
        self.strategy_performance[strategy_name] = {
            'opportunities_found': 0,
            'opportunities_executed': 0,
            'total_profit': Decimal('0'),
            'total_loss': Decimal('0'),
            'success_rate': 0.0,
            'avg_profit_per_trade': Decimal('0'),
            'last_opportunity_time': 0,
            'execution_times': [],
            'error_count': 0
        }
    
    logger.info("performance_metrics_reset")

def get_manager_status(self) -> Dict[str, Any]:
    """Get strategy manager status"""
    return {
        'total_strategies': len(self.strategies),
        'enabled_strategies': len(self.enabled_strategies),
        'active_opportunities': len(self.active_opportunities),
        'execution_queue_size': len(self.execution_queue),
        'executing_count': len(self.executing_opportunities),
        'max_concurrent_opportunities': self.max_concurrent_opportunities,
        'scan_interval': self.scan_interval,
        'total_opportunities_found': self.total_opportunities_found,
        'total_opportunities_executed': self.total_opportunities_executed,
        'total_profit': float(self.total_profit),
        'total_loss': float(self.total_loss),
        'net_profit': float(self.total_profit - self.total_loss)
    }
```