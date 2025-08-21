"""
Strategy Manager for SmartArb Engine
Manages multiple trading strategies and coordinates their execution
"""

import asyncio
from typing import Dict, List, Optional, Any
from decimal import Decimal
import time
import structlog

from ..exchanges.base_exchange import BaseExchange
from ..strategies.base_strategy import BaseStrategy, Opportunity
from ..strategies.spatial_arbitrage import SpatialArbitrageStrategy
from .risk_manager import RiskManager
from .execution_engine import ExecutionEngine

logger = structlog.get_logger(__name__)


class StrategyManager:
    """
    Strategy Management System
    
    Features:
    - Multiple strategy coordination
    - Opportunity prioritization
    - Execution scheduling
    - Performance monitoring
    - Resource allocation
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
        self.max_concurrent_opportunities = config.get('max_concurrent_opportunities', 3)
        self.scan_interval = config.get('scan_interval', 5)  # seconds
        
        # Performance tracking
        self.total_opportunities_found = 0
        self.total_opportunities_executed = 0
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}
        
        # Active opportunity tracking
        self.active_opportunities: Dict[str, Opportunity] = {}
        self.opportunity_queue: List[Opportunity] = []
        
        # Initialize strategies
        self._initialize_strategies()
        
        logger.info("strategy_manager_initialized",
                   strategies=list(self.strategies.keys()),
                   enabled=self.enabled_strategies,
                   max_concurrent=self.max_concurrent_opportunities)
    
    def _initialize_strategies(self):
        """Initialize all configured strategies"""
        strategy_configs = self.config
        
        # Initialize Spatial Arbitrage Strategy
        if strategy_configs.get('spatial_arbitrage', {}).get('enabled', False):
            try:
                spatial_config = strategy_configs['spatial_arbitrage']
                spatial_config['trading_pairs'] = self.config.get('trading_pairs', [
                    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'DOT/USDT', 'LINK/USDT', 'MATIC/USDT'
                ])
                
                spatial_strategy = SpatialArbitrageStrategy(self.exchanges, spatial_config)
                self.strategies['spatial_arbitrage'] = spatial_strategy
                self.enabled_strategies.append('spatial_arbitrage')
                
                logger.info("strategy_initialized", 
                           strategy="spatial_arbitrage",
                           pairs=len(spatial_config['trading_pairs']))
                
            except Exception as e:
                logger.error("strategy_initialization_failed",
                           strategy="spatial_arbitrage", error=str(e))
        
        # Initialize Triangular Arbitrage (placeholder for future)
        if strategy_configs.get('triangular_arbitrage', {}).get('enabled', False):
            logger.info("triangular_arbitrage_not_implemented")
        
        # Validate we have at least one strategy
        if not self.enabled_strategies:
            logger.warning("no_strategies_enabled")
    
    async def scan_opportunities(self) -> List[Opportunity]:
        """
        Scan all enabled strategies for opportunities
        
        Returns:
            List[Opportunity]: All valid opportunities found across strategies
        """
        all_opportunities = []
        
        try:
            # Scan each enabled strategy
            scan_tasks = []
            for strategy_name in self.enabled_strategies:
                strategy = self.strategies[strategy_name]
                if strategy.enabled and strategy.can_take_opportunity():
                    task = self._scan_strategy_safe(strategy)
                    scan_tasks.append(task)
            
            # Wait for all scans to complete
            if scan_tasks:
                results = await asyncio.gather(*scan_tasks, return_exceptions=True)
                
                # Process results
                for result in results:
                    if isinstance(result, Exception):
                        logger.warning("strategy_scan_failed", error=str(result))
                        continue
                    
                    if isinstance(result, list):
                        all_opportunities.extend(result)
            
            # Update tracking
            self.total_opportunities_found += len(all_opportunities)
            
            # Prioritize opportunities
            prioritized_opportunities = self._prioritize_opportunities(all_opportunities)
            
            # Clean up expired opportunities
            self._cleanup_expired_opportunities()
            
            if prioritized_opportunities:
                logger.info("opportunities_found",
                           total=len(all_opportunities),
                           prioritized=len(prioritized_opportunities))
            
            return prioritized_opportunities
            
        except Exception as e:
            logger.error("opportunity_scan_failed", error=str(e))
            return []
    
    async def _scan_strategy_safe(self, strategy: BaseStrategy) -> List[Opportunity]:
        """Safely scan a strategy with error handling"""
        try:
            return await strategy.scan_and_validate()
        except Exception as e:
            logger.error("strategy_scan_error", 
                        strategy=strategy.name, error=str(e))
            return []
    
    def _prioritize_opportunities(self, opportunities: List[Opportunity]) -> List[Opportunity]:
        """
        Prioritize opportunities based on multiple criteria
        
        Priority factors:
        1. Expected profit percentage
        2. Confidence score (if available)
        3. Trade size
        4. Strategy performance history
        """
        if not opportunities:
            return []
        
        def priority_score(opp: Opportunity) -> float:
            score = 0.0
            
            # Base score from expected profit
            score += float(opp.expected_profit_percent) * 10
            
            # Confidence bonus (if available)
            if hasattr(opp, 'confidence_score'):
                score += opp.confidence_score * 50
            
            # Size factor (prefer moderate sizes)
            size_factor = min(float(opp.amount) / 1000, 1.0)  # Normalize to 1000 USDT
            score += size_factor * 20
            
            # Strategy performance factor
            strategy_perf = self.strategy_performance.get(opp.strategy, {})
            success_rate = strategy_perf.get('success_rate_percent', 50)
            score += (success_rate / 100) * 30
            
            # Age penalty (prefer newer opportunities)
            age_penalty = min(opp.age_seconds / 60, 5)  # Max 5 point penalty
            score -= age_penalty
            
            return score
        
        # Sort by priority score (highest first)
        sorted_opportunities = sorted(opportunities, key=priority_score, reverse=True)
        
        # Limit to max concurrent opportunities
        max_opportunities = self.max_concurrent_opportunities - len(self.active_opportunities)
        return sorted_opportunities[:max_opportunities]
    
    async def execute_opportunities(self, opportunities: List[Opportunity]) -> List[Dict[str, Any]]:
        """
        Execute a list of opportunities
        
        Returns:
            List of execution results
        """
        results = []
        
        for opportunity in opportunities:
            # Final validation before execution
            if not await self.risk_manager.validate_opportunity(opportunity):
                logger.info("opportunity_rejected_by_risk_manager",
                           opportunity_id=opportunity.opportunity_id)
                continue
            
            # Add to active tracking
            self.active_opportunities[opportunity.opportunity_id] = opportunity
            strategy = self.strategies[opportunity.strategy]
            strategy.add_active_opportunity(opportunity)
            
            try:
                # Execute opportunity
                execution_result = await self.execution_engine.execute_opportunity(opportunity)
                
                if execution_result:
                    # Record result in strategy
                    strategy.record_execution_result(
                        opportunity, 
                        execution_result.success, 
                        execution_result.realized_profit
                    )
                    
                    # Update our tracking
                    if execution_result.success:
                        self.total_opportunities_executed += 1
                    
                    results.append({
                        'opportunity_id': opportunity.opportunity_id,
                        'execution_id': execution_result.execution_id,
                        'success': execution_result.success,
                        'profit': float(execution_result.realized_profit),
                        'fees': float(execution_result.total_fees),
                        'execution_time_ms': execution_result.execution_time_ms
                    })
                    
                    logger.info("opportunity_executed",
                               opportunity_id=opportunity.opportunity_id,
                               success=execution_result.success,
                               profit=float(execution_result.realized_profit))
                
            except Exception as e:
                logger.error("opportunity_execution_failed",
                           opportunity_id=opportunity.opportunity_id,
                           error=str(e))
                
                # Record failure
                strategy.record_execution_result(opportunity, False)
            
            finally:
                # Remove from active tracking
                self.active_opportunities.pop(opportunity.opportunity_id, None)
        
        return results
    
    async def run_strategy_cycle(self) -> Dict[str, Any]:
        """
        Run a complete strategy cycle: scan + execute
        
        Returns:
            Dict with cycle results
        """
        cycle_start = time.time()
        
        # Scan for opportunities
        opportunities = await self.scan_opportunities()
        
        # Execute opportunities
        execution_results = []
        if opportunities:
            execution_results = await self.execute_opportunities(opportunities)
        
        cycle_time = (time.time() - cycle_start) * 1000  # ms
        
        # Update performance metrics
        self._update_strategy_performance()
        
        return {
            'cycle_time_ms': cycle_time,
            'opportunities_found': len(opportunities),
            'opportunities_executed': len(execution_results),
            'successful_executions': sum(1 for r in execution_results if r['success']),
            'total_profit': sum(r['profit'] for r in execution_results),
            'execution_results': execution_results
        }
    
    def _update_strategy_performance(self):
        """Update strategy performance metrics"""
        for strategy_name, strategy in self.strategies.items():
            self.strategy_performance[strategy_name] = strategy.get_performance_stats()
    
    def _cleanup_expired_opportunities(self):
        """Clean up expired opportunities from tracking"""
        current_time = time.time()
        expired_ids = []
        
        for opp_id, opportunity in self.active_opportunities.items():
            if opportunity.is_expired(300):  # 5 minutes
                expired_ids.append(opp_id)
        
        for opp_id in expired_ids:
            self.active_opportunities.pop(opp_id, None)
            logger.debug("expired_opportunity_removed", opportunity_id=opp_id)
    
    async def stop(self):
        """Stop strategy manager and all strategies"""
        logger.info("strategy_manager_stopping")
        
        # Cancel any active opportunities
        for opportunity in self.active_opportunities.values():
            logger.info("cancelling_active_opportunity", 
                       opportunity_id=opportunity.opportunity_id)
        
        self.active_opportunities.clear()
        
        # Clean up strategies
        for strategy in self.strategies.values():
            strategy.cleanup_expired_opportunities(0)  # Force cleanup all
        
        logger.info("strategy_manager_stopped")
    
    def get_strategy_status(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Get status of specific strategy"""
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            return None
        
        return strategy.get_status()
    
    def get_all_strategies_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all strategies"""
        return {
            name: strategy.get_status() 
            for name, strategy in self.strategies.items()
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        total_strategies = len(self.strategies)
        active_strategies = len(self.enabled_strategies)
        
        # Aggregate metrics across strategies
        total_profit = Decimal('0')
        total_trades = 0
        
        for strategy in self.strategies.values():
            total_profit += strategy.total_profit
            total_trades += strategy.total_opportunities_executed
        
        success_rate = 0
        if self.total_opportunities_found > 0:
            success_rate = (self.total_opportunities_executed / self.total_opportunities_found) * 100
        
        return {
            'total_strategies': total_strategies,
            'active_strategies': active_strategies,
            'enabled_strategies': self.enabled_strategies,
            'total_opportunities_found': self.total_opportunities_found,
            'total_opportunities_executed': self.total_opportunities_executed,
            'overall_success_rate_percent': success_rate,
            'total_profit': float(total_profit),
            'active_opportunities': len(self.active_opportunities),
            'max_concurrent_opportunities': self.max_concurrent_opportunities,
            'strategy_performance': self.strategy_performance
        }
    
    def enable_strategy(self, strategy_name: str) -> bool:
        """Enable a strategy"""
        if strategy_name in self.strategies and strategy_name not in self.enabled_strategies:
            self.strategies[strategy_name].enabled = True
            self.enabled_strategies.append(strategy_name)
            logger.info("strategy_enabled", strategy=strategy_name)
            return True
        return False
    
    def disable_strategy(self, strategy_name: str) -> bool:
        """Disable a strategy"""
        if strategy_name in self.enabled_strategies:
            self.strategies[strategy_name].enabled = False
            self.enabled_strategies.remove(strategy_name)
            logger.info("strategy_disabled", strategy=strategy_name)
            return True
        return False
