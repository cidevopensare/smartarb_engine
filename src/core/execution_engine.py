"""
Execution Engine for SmartArb Engine
Handles trade execution and order management
"""

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
import structlog

from ..exchanges.base_exchange import BaseExchange, Order, OrderSide, OrderStatus
from ..strategies.base_strategy import Opportunity
from .risk_manager import RiskManager

logger = structlog.get_logger(__name__)


class ExecutionStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    """Result of trade execution"""
    opportunity_id: str
    execution_id: str
    status: ExecutionStatus
    success: bool
    orders: List[Order] = field(default_factory=list)
    realized_profit: Decimal = Decimal('0')
    total_fees: Decimal = Decimal('0')
    execution_time_ms: float = 0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """Plan for executing an arbitrage opportunity"""
    opportunity: Opportunity
    buy_order: Dict[str, Any]
    sell_order: Dict[str, Any]
    execution_sequence: str  # 'simultaneous', 'buy_first', 'sell_first'
    timeout_seconds: int = 30
    max_retries: int = 3


class ExecutionEngine:
    """
    Trade Execution Engine
    
    Features:
    - Simultaneous order execution for arbitrage
    - Order management and monitoring
    - Execution result tracking
    - Error handling and retries
    - Slippage monitoring
    """
    
    def __init__(self, exchanges: Dict[str, BaseExchange], 
                 risk_manager: RiskManager, config: Dict[str, Any]):
        self.exchanges = exchanges
        self.risk_manager = risk_manager
        self.config = config
        
        # Execution settings
        self.order_timeout = config.get('order_timeout', 30)
        self.max_retries = config.get('max_order_retries', 3)
        self.order_type = config.get('order_type', 'limit')
        self.slippage_tolerance = Decimal(str(config.get('max_slippage', 0.5)))
        
        # Execution tracking
        self.active_executions: Dict[str, ExecutionResult] = {}
        self.execution_history: List[ExecutionResult] = []
        
        # Performance metrics
        self.total_executions = 0
        self.successful_executions = 0
        self.total_profit = Decimal('0')
        self.total_fees = Decimal('0')
        
        logger.info("execution_engine_initialized",
                   order_timeout=self.order_timeout,
                   order_type=self.order_type)
    
    async def execute_opportunity(self, opportunity: Opportunity) -> Optional[ExecutionResult]:
        """
        Execute an arbitrage opportunity
        
        Args:
            opportunity: Opportunity to execute
            
        Returns:
            ExecutionResult: Result of execution
        """
        execution_id = f"exec_{opportunity.opportunity_id}_{int(time.time())}"
        start_time = time.time()
        
        logger.info("execution_started",
                   execution_id=execution_id,
                   opportunity_id=opportunity.opportunity_id,
                   symbol=opportunity.symbol,
                   amount=float(opportunity.amount))
        
        # Create execution result
        result = ExecutionResult(
            opportunity_id=opportunity.opportunity_id,
            execution_id=execution_id,
            status=ExecutionStatus.PENDING,
            success=False
        )
        
        try:
            # Track active execution
            self.active_executions[execution_id] = result
            
            # Create execution plan
            execution_plan = await self._create_execution_plan(opportunity)
            if not execution_plan:
                result.status = ExecutionStatus.FAILED
                result.error_message = "Failed to create execution plan"
                return result
            
            # Execute the plan
            result.status = ExecutionStatus.EXECUTING
            success = await self._execute_plan(execution_plan, result)
            
            # Update result
            result.success = success
            result.status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED
            result.execution_time_ms = (time.time() - start_time) * 1000
            
            # Update metrics
            self.total_executions += 1
            if success:
                self.successful_executions += 1
                self.total_profit += result.realized_profit
            
            self.total_fees += result.total_fees
            
            # Update risk manager
            self.risk_manager.record_trade_result(
                opportunity, success, result.realized_profit
            )
            
            logger.info("execution_completed",
                       execution_id=execution_id,
                       success=success,
                       profit=float(result.realized_profit),
                       fees=float(result.total_fees),
                       duration_ms=result.execution_time_ms)
            
            return result
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.execution_time_ms = (time.time() - start_time) * 1000
            
            logger.error("execution_failed",
                        execution_id=execution_id,
                        error=str(e))
            
            return result
            
        finally:
            # Move to history
            self.execution_history.append(result)
            self.active_executions.pop(execution_id, None)
    
    async def _create_execution_plan(self, opportunity: Opportunity) -> Optional[ExecutionPlan]:
        """Create execution plan for opportunity"""
        try:
            # Check if this is a spatial arbitrage opportunity
            if hasattr(opportunity, 'buy_exchange') and hasattr(opportunity, 'sell_exchange'):
                return await self._create_spatial_execution_plan(opportunity)
            else:
                logger.warning("unsupported_opportunity_type", 
                             strategy=opportunity.strategy)
                return None
                
        except Exception as e:
            logger.error("execution_plan_creation_failed", error=str(e))
            return None
    
    async def _create_spatial_execution_plan(self, opportunity) -> ExecutionPlan:
        """Create execution plan for spatial arbitrage"""
        base_asset, quote_asset = opportunity.symbol.split('/')
        
        # Buy order (on cheaper exchange)
        buy_order = {
            'exchange': opportunity.buy_exchange,
            'symbol': opportunity.symbol,
            'side': OrderSide.BUY,
            'amount': opportunity.amount,
            'price': opportunity.buy_price,
            'type': self.order_type
        }
        
        # Sell order (on more expensive exchange)
        sell_order = {
            'exchange': opportunity.sell_exchange,
            'symbol': opportunity.symbol,
            'side': OrderSide.SELL,
            'amount': opportunity.amount,
            'price': opportunity.sell_price,
            'type': self.order_type
        }
        
        return ExecutionPlan(
            opportunity=opportunity,
            buy_order=buy_order,
            sell_order=sell_order,
            execution_sequence='simultaneous',  # Execute both orders at same time
            timeout_seconds=self.order_timeout,
            max_retries=self.max_retries
        )
    
    async def _execute_plan(self, plan: ExecutionPlan, result: ExecutionResult) -> bool:
        """Execute the execution plan"""
        try:
            if plan.execution_sequence == 'simultaneous':
                return await self._execute_simultaneous(plan, result)
            elif plan.execution_sequence == 'buy_first':
                return await self._execute_sequential(plan, result, buy_first=True)
            elif plan.execution_sequence == 'sell_first':
                return await self._execute_sequential(plan, result, buy_first=False)
            else:
                logger.error("unknown_execution_sequence", sequence=plan.execution_sequence)
                return False
                
        except Exception as e:
            logger.error("plan_execution_failed", error=str(e))
            result.error_message = str(e)
            return False
    
    async def _execute_simultaneous(self, plan: ExecutionPlan, result: ExecutionResult) -> bool:
        """Execute buy and sell orders simultaneously"""
        try:
            # Prepare both orders
            buy_exchange = self.exchanges[plan.buy_order['exchange']]
            sell_exchange = self.exchanges[plan.sell_order['exchange']]
            
            # Create order tasks
            buy_task = self._place_order_with_retry(buy_exchange, plan.buy_order, plan.max_retries)
            sell_task = self._place_order_with_retry(sell_exchange, plan.sell_order, plan.max_retries)
            
            # Execute both orders simultaneously
            buy_result, sell_result = await asyncio.gather(
                buy_task, sell_task, return_exceptions=True
            )
            
            # Check results
            buy_success = isinstance(buy_result, Order) and buy_result.status != OrderStatus.FAILED
            sell_success = isinstance(sell_result, Order) and sell_result.status != OrderStatus.FAILED
            
            if buy_success:
                result.orders.append(buy_result)
            if sell_success:
                result.orders.append(sell_result)
            
            # Both orders must succeed for arbitrage
            if buy_success and sell_success:
                # Monitor order fills
                await self._monitor_order_fills(result.orders, plan.timeout_seconds)
                
                # Calculate realized profit
                result.realized_profit, result.total_fees = self._calculate_profit_and_fees(
                    result.orders, plan.opportunity
                )
                
                return True
            else:
                # Cancel any successful order if the other failed
                await self._handle_partial_execution(result.orders)
                return False
                
        except Exception as e:
            logger.error("simultaneous_execution_failed", error=str(e))
            return False
    
    async def _execute_sequential(self, plan: ExecutionPlan, result: ExecutionResult, 
                                buy_first: bool) -> bool:
        """Execute orders sequentially"""
        orders_to_execute = [plan.buy_order, plan.sell_order] if buy_first else [plan.sell_order, plan.buy_order]
        
        for order_config in orders_to_execute:
            exchange = self.exchanges[order_config['exchange']]
            
            try:
                order = await self._place_order_with_retry(exchange, order_config, plan.max_retries)
                
                if order and order.status != OrderStatus.FAILED:
                    result.orders.append(order)
                    
                    # Wait for order to fill before next order
                    filled = await self._wait_for_order_fill(order, exchange, plan.timeout_seconds)
                    if not filled:
                        logger.warning("order_not_filled", order_id=order.id)
                        # Cancel remaining orders and return
                        await self._cancel_order_safe(exchange, order.id, order_config['symbol'])
                        return False
                else:
                    # Order failed, cancel any previous orders
                    await self._handle_partial_execution(result.orders)
                    return False
                    
            except Exception as e:
                logger.error("sequential_order_failed", error=str(e))
                await self._handle_partial_execution(result.orders)
                return False
        
        # Calculate results
        result.realized_profit, result.total_fees = self._calculate_profit_and_fees(
            result.orders, plan.opportunity
        )
        
        return True
    
    async def _place_order_with_retry(self, exchange: BaseExchange, 
                                    order_config: Dict[str, Any], max_retries: int) -> Optional[Order]:
        """Place order with retry logic"""
        for attempt in range(max_retries + 1):
            try:
                order = await exchange.place_order(
                    symbol=order_config['symbol'],
                    side=order_config['side'],
                    amount=order_config['amount'],
                    price=order_config['price'],
                    order_type=order_config['type']
                )
                
                logger.debug("order_placed",
                           exchange=exchange.name,
                           order_id=order.id,
                           symbol=order.symbol,
                           side=order.side.value,
                           amount=float(order.amount),
                           price=float(order.price))
                
                return order
                
            except Exception as e:
                logger.warning("order_placement_failed",
                             exchange=exchange.name,
                             attempt=attempt + 1,
                             max_retries=max_retries,
                             error=str(e))
                
                if attempt < max_retries:
                    await asyncio.sleep(1)  # Wait before retry
                else:
                    logger.error("order_placement_failed_all_retries", 
                               exchange=exchange.name)
        
        return None
    
    async def _monitor_order_fills(self, orders: List[Order], timeout_seconds: int):
        """Monitor orders until they are filled or timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            all_filled = True
            
            for order in orders:
                if order.status not in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.FAILED]:
                    # Check order status
                    try:
                        exchange = self._get_exchange_by_name(order)
                        if exchange:
                            updated_order = await exchange.get_order_status(order.id, order.symbol)
                            order.status = updated_order.status
                            order.filled = updated_order.filled
                    except Exception as e:
                        logger.warning("order_status_check_failed", 
                                     order_id=order.id, error=str(e))
                
                if order.status != OrderStatus.FILLED:
                    all_filled = False
            
            if all_filled:
                logger.info("all_orders_filled")
                break
            
            await asyncio.sleep(1)  # Check every second
        
        # Cancel any unfilled orders
        for order in orders:
            if order.status == OrderStatus.PENDING:
                exchange = self._get_exchange_by_name(order)
                if exchange:
                    await self._cancel_order_safe(exchange, order.id, order.symbol)
    
    async def _wait_for_order_fill(self, order: Order, exchange: BaseExchange, 
                                 timeout_seconds: int) -> bool:
        """Wait for single order to fill"""
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                updated_order = await exchange.get_order_status(order.id, order.symbol)
                order.status = updated_order.status
                order.filled = updated_order.filled
                
                if order.status == OrderStatus.FILLED:
                    return True
                elif order.status in [OrderStatus.CANCELLED, OrderStatus.FAILED]:
                    return False
                    
            except Exception as e:
                logger.warning("order_status_check_failed", 
                             order_id=order.id, error=str(e))
            
            await asyncio.sleep(1)
        
        return False
    
    def _get_exchange_by_name(self, order: Order) -> Optional[BaseExchange]:
        """Get exchange instance for order"""
        # Note: We'd need to track which exchange each order belongs to
        # For now, try to find exchange by checking all exchanges
        for exchange in self.exchanges.values():
            if exchange.name in str(order.id):  # Simple heuristic
                return exchange
        return None
    
    async def _handle_partial_execution(self, orders: List[Order]):
        """Handle partial execution by cancelling open orders"""
        for order in orders:
            if order.status == OrderStatus.PENDING:
                exchange = self._get_exchange_by_name(order)
                if exchange:
                    await self._cancel_order_safe(exchange, order.id, order.symbol)
    
    async def _cancel_order_safe(self, exchange: BaseExchange, order_id: str, symbol: str):
        """Safely cancel order with error handling"""
        try:
            success = await exchange.cancel_order(order_id, symbol)
            if success:
                logger.info("order_cancelled", order_id=order_id)
            else:
                logger.warning("order_cancellation_failed", order_id=order_id)
        except Exception as e:
            logger.error("order_cancellation_error", order_id=order_id, error=str(e))
    
    def _calculate_profit_and_fees(self, orders: List[Order], opportunity) -> Tuple[Decimal, Decimal]:
        """Calculate realized profit and total fees"""
        total_profit = Decimal('0')
        total_fees = Decimal('0')
        
        # For spatial arbitrage, we should have one buy and one sell order
        buy_order = None
        sell_order = None
        
        for order in orders:
            if order.side == OrderSide.BUY:
                buy_order = order
            else:
                sell_order = order
        
        if buy_order and sell_order and buy_order.status == OrderStatus.FILLED and sell_order.status == OrderStatus.FILLED:
            # Calculate profit: (sell_price - buy_price) * amount - fees
            profit = (sell_order.price - buy_order.price) * min(buy_order.filled, sell_order.filled)
            
            # Estimate fees (in a real system, you'd get actual fees from exchange)
            buy_fee = buy_order.filled * buy_order.price * Decimal('0.001')  # 0.1% estimate
            sell_fee = sell_order.filled * sell_order.price * Decimal('0.001')  # 0.1% estimate
            
            total_profit = profit - buy_fee - sell_fee
            total_fees = buy_fee + sell_fee
        
        return total_profit, total_fees
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution engine statistics"""
        success_rate = 0
        if self.total_executions > 0:
            success_rate = (self.successful_executions / self.total_executions) * 100
        
        avg_profit_per_trade = Decimal('0')
        if self.successful_executions > 0:
            avg_profit_per_trade = self.total_profit / self.successful_executions
        
        return {
            'total_executions': self.total_executions,
            'successful_executions': self.successful_executions,
            'success_rate_percent': success_rate,
            'total_profit': float(self.total_profit),
            'total_fees': float(self.total_fees),
            'net_profit': float(self.total_profit - self.total_fees),
            'average_profit_per_trade': float(avg_profit_per_trade),
            'active_executions': len(self.active_executions)
        }
