“””
Execution Engine for SmartArb Engine
Handles the execution of arbitrage trades with sophisticated order management
“””

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import uuid
import structlog

from ..exchanges.base_exchange import BaseExchange, Order, OrderSide, OrderStatus
from ..strategies.base_strategy import Opportunity
from .risk_manager import RiskManager, RiskAssessment

logger = structlog.get_logger(**name**)

class ExecutionStatus(Enum):
“”“Execution status enumeration”””
PENDING = “pending”
EXECUTING = “executing”
PARTIALLY_FILLED = “partially_filled”
COMPLETED = “completed”
FAILED = “failed”
CANCELLED = “cancelled”
TIMEOUT = “timeout”

class ExecutionType(Enum):
“”“Type of execution”””
MARKET = “market”
LIMIT = “limit”
STOP_LOSS = “stop_loss”

@dataclass
class ExecutionPlan:
“”“Plan for executing an arbitrage opportunity”””
execution_id: str
opportunity: Opportunity
buy_exchange: str
sell_exchange: str
buy_amount: Decimal
sell_amount: Decimal
buy_price: Decimal
sell_price: Decimal
expected_profit: Decimal
max_slippage: Decimal
timeout: int  # seconds
execution_type: ExecutionType

```
# Order management
buy_order_id: Optional[str] = None
sell_order_id: Optional[str] = None

# Status tracking
status: ExecutionStatus = ExecutionStatus.PENDING
created_at: float = 0
started_at: float = 0
completed_at: float = 0

def __post_init__(self):
    if self.created_at == 0:
        self.created_at = time.time()
```

@dataclass
class ExecutionResult:
“”“Result of an execution”””
execution_id: str
success: bool
status: ExecutionStatus
profit_loss: Decimal
buy_fill_price: Optional[Decimal] = None
sell_fill_price: Optional[Decimal] = None
buy_fill_amount: Optional[Decimal] = None
sell_fill_amount: Optional[Decimal] = None
execution_time: float = 0
fees_paid: Decimal = Decimal(‘0’)
slippage: Decimal = Decimal(‘0’)
error_message: Optional[str] = None

```
# Order details
buy_order: Optional[Order] = None
sell_order: Optional[Order] = None
```

class ExecutionEngine:
“””
Advanced execution engine for arbitrage trades

```
Features:
- Simultaneous order execution
- Slippage management
- Partial fill handling
- Timeout protection
- Error recovery
- Performance tracking
"""

def __init__(self, exchanges: Dict[str, BaseExchange], 
             risk_manager: RiskManager, config: Dict[str, Any]):
    self.exchanges = exchanges
    self.risk_manager = risk_manager
    self.config = config
    
    # Execution configuration
    execution_config = config.get('execution', {})
    self.default_timeout = execution_config.get('timeout', 30)  # seconds
    self.max_slippage = Decimal(str(execution_config.get('max_slippage', 0.5)))  # %
    self.min_profit_threshold = Decimal(str(execution_config.get('min_profit_threshold', 1.0)))  # USDT
    self.enable_partial_fills = execution_config.get('enable_partial_fills', True)
    self.retry_failed_orders = execution_config.get('retry_failed_orders', True)
    self.max_retries = execution_config.get('max_retries', 3)
    
    # Paper trading mode
    self.paper_trading = config.get('trading', {}).get('paper_trading', True)
    
    # Active executions tracking
    self.active_executions: Dict[str, ExecutionPlan] = {}
    self.completed_executions: List[ExecutionResult] = []
    
    # Performance metrics
    self.total_executions = 0
    self.successful_executions = 0
    self.total_profit = Decimal('0')
    self.total_fees = Decimal('0')
    self.avg_execution_time = 0.0
    
    # Order management
    self.pending_orders: Dict[str, Order] = {}
    
    logger.info("execution_engine_initialized",
               paper_trading=self.paper_trading,
               default_timeout=self.default_timeout,
               max_slippage=float(self.max_slippage))

async def execute_opportunity(self, opportunity: Opportunity, 
                            execution_type: ExecutionType = ExecutionType.MARKET) -> ExecutionResult:
    """Execute an arbitrage opportunity"""
    
    try:
        # Create execution plan
        execution_plan = await self._create_execution_plan(opportunity, execution_type)
        if not execution_plan:
            return ExecutionResult(
                execution_id=str(uuid.uuid4()),
                success=False,
                status=ExecutionStatus.FAILED,
                profit_loss=Decimal('0'),
                error_message="Failed to create execution plan"
            )
        
        # Final risk check
        risk_assessment = await self.risk_manager.assess_risk(opportunity)
        if not risk_assessment.approved:
            logger.warning("execution_blocked_by_risk",
                         opportunity_id=opportunity.opportunity_id,
                         risk_score=risk_assessment.risk_score,
                         violations=risk_assessment.violations)
            return ExecutionResult(
                execution_id=execution_plan.execution_id,
                success=False,
                status=ExecutionStatus.FAILED,
                profit_loss=Decimal('0'),
                error_message=f"Risk assessment failed: {risk_assessment.violations}"
            )
        
        # Execute the plan
        self.active_executions[execution_plan.execution_id] = execution_plan
        result = await self._execute_plan(execution_plan)
        
        # Clean up
        if execution_plan.execution_id in self.active_executions:
            del self.active_executions[execution_plan.execution_id]
        
        # Update statistics
        self._update_execution_stats(result)
        self.completed_executions.append(result)
        
        # Limit history size
        if len(self.completed_executions) > 1000:
            self.completed_executions = self.completed_executions[-1000:]
        
        return result
        
    except Exception as e:
        logger.error("execution_error",
                    opportunity_id=opportunity.opportunity_id,
                    error=str(e))
        return ExecutionResult(
            execution_id=str(uuid.uuid4()),
            success=False,
            status=ExecutionStatus.FAILED,
            profit_loss=Decimal('0'),
            error_message=str(e)
        )

async def _create_execution_plan(self, opportunity: Opportunity, 
                               execution_type: ExecutionType) -> Optional[ExecutionPlan]:
    """Create execution plan for opportunity"""
    
    try:
        # Import specific opportunity types
        from ..strategies.spatial_arbitrage import SpatialOpportunity
        
        if isinstance(opportunity, SpatialOpportunity):
            return ExecutionPlan(
                execution_id=str(uuid.uuid4()),
                opportunity=opportunity,
                buy_exchange=opportunity.buy_exchange,
                sell_exchange=opportunity.sell_exchange,
                buy_amount=opportunity.amount,
                sell_amount=opportunity.amount,
                buy_price=opportunity.buy_price,
                sell_price=opportunity.sell_price,
                expected_profit=opportunity.expected_profit,
                max_slippage=self.max_slippage,
                timeout=self.default_timeout,
                execution_type=execution_type
            )
        
        # Add support for other opportunity types here
        logger.warning("unsupported_opportunity_type",
                     type=type(opportunity).__name__)
        return None
        
    except Exception as e:
        logger.error("execution_plan_creation_failed", error=str(e))
        return None

async def _execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
    """Execute the arbitrage plan"""
    
    start_time = time.time()
    plan.started_at = start_time
    plan.status = ExecutionStatus.EXECUTING
    
    try:
        logger.info("starting_arbitrage_execution",
                   execution_id=plan.execution_id,
                   buy_exchange=plan.buy_exchange,
                   sell_exchange=plan.sell_exchange,
                   symbol=plan.opportunity.symbol,
                   amount=float(plan.buy_amount),
                   expected_profit=float(plan.expected_profit))
        
        if self.paper_trading:
            return await self._paper_trade_execution(plan)
        else:
            return await self._live_trade_execution(plan)
            
    except asyncio.TimeoutError:
        logger.error("execution_timeout",
                    execution_id=plan.execution_id,
                    timeout=plan.timeout)
        plan.status = ExecutionStatus.TIMEOUT
        return ExecutionResult(
            execution_id=plan.execution_id,
            success=False,
            status=ExecutionStatus.TIMEOUT,
            profit_loss=Decimal('0'),
            execution_time=time.time() - start_time,
            error_message="Execution timeout"
        )
    
    except Exception as e:
        logger.error("execution_plan_failed",
                    execution_id=plan.execution_id,
                    error=str(e))
        plan.status = ExecutionStatus.FAILED
        return ExecutionResult(
            execution_id=plan.execution_id,
            success=False,
            status=ExecutionStatus.FAILED,
            profit_loss=Decimal('0'),
            execution_time=time.time() - start_time,
            error_message=str(e)
        )

async def _live_trade_execution(self, plan: ExecutionPlan) -> ExecutionResult:
    """Execute live trade with real orders"""
    
    start_time = time.time()
    buy_exchange = self.exchanges[plan.buy_exchange]
    sell_exchange = self.exchanges[plan.sell_exchange]
    
    try:
        # Create tasks for simultaneous execution
        buy_task = asyncio.create_task(
            self._place_buy_order(buy_exchange, plan)
        )
        sell_task = asyncio.create_task(
            self._place_sell_order(sell_exchange, plan)
        )
        
        # Wait for both orders with timeout
        try:
            buy_result, sell_result = await asyncio.wait_for(
                asyncio.gather(buy_task, sell_task),
                timeout=plan.timeout
            )
        except asyncio.TimeoutError:
            # Cancel pending orders
            await self._cancel_pending_orders(plan)
            raise
        
        # Check if both orders were successful
        if not buy_result.success or not sell_result.success:
            # Handle partial execution
            return await self._handle_partial_execution(plan, buy_result, sell_result)
        
        # Calculate actual profit/loss
        actual_profit = self._calculate_actual_profit(buy_result, sell_result)
        
        # Calculate slippage
        slippage = self._calculate_slippage(plan, buy_result, sell_result)
        
        plan.status = ExecutionStatus.COMPLETED
        plan.completed_at = time.time()
        
        logger.info("arbitrage_execution_completed",
                   execution_id=plan.execution_id,
                   actual_profit=float(actual_profit),
                   slippage=float(slippage),
                   execution_time=plan.completed_at - start_time)
        
        return ExecutionResult(
            execution_id=plan.execution_id,
            success=True,
            status=ExecutionStatus.COMPLETED,
            profit_loss=actual_profit,
            buy_fill_price=buy_result.fill_price,
            sell_fill_price=sell_result.fill_price,
            buy_fill_amount=buy_result.fill_amount,
            sell_fill_amount=sell_result.fill_amount,
            execution_time=plan.completed_at - start_time,
            fees_paid=buy_result.fees + sell_result.fees,
            slippage=slippage,
            buy_order=buy_result.order,
            sell_order=sell_result.order
        )
        
    except Exception as e:
        # Ensure orders are cancelled in case of error
        await self._cancel_pending_orders(plan)
        raise e

async def _paper_trade_execution(self, plan: ExecutionPlan) -> ExecutionResult:
    """Simulate execution in paper trading mode"""
    
    start_time = time.time()
    
    # Simulate execution delay
    await asyncio.sleep(0.1)  # 100ms simulation
    
    # Simulate some slippage (0-0.1%)
    import random
    simulated_slippage = Decimal(str(random.uniform(0, 0.001)))
    
    # Calculate simulated fill prices
    buy_fill_price = plan.buy_price * (1 + simulated_slippage)
    sell_fill_price = plan.sell_price * (1 - simulated_slippage)
    
    # Calculate simulated fees (0.1% per side)
    simulated_fees = (plan.buy_amount * plan.buy_price + plan.sell_amount * plan.sell_price) * Decimal('0.001')
    
    # Calculate profit with slippage and fees
    gross_profit = (sell_fill_price - buy_fill_price) * plan.buy_amount
    net_profit = gross_profit - simulated_fees
    
    execution_time = time.time() - start_time
    
    logger.info("paper_trade_executed",
               execution_id=plan.execution_id,
               profit=float(net_profit),
               slippage=float(simulated_slippage),
               fees=float(simulated_fees))
    
    return ExecutionResult(
        execution_id=plan.execution_id,
        success=True,
        status=ExecutionStatus.COMPLETED,
        profit_loss=net_profit,
        buy_fill_price=buy_fill_price,
        sell_fill_price=sell_fill_price,
        buy_fill_amount=plan.buy_amount,
        sell_fill_amount=plan.sell_amount,
        execution_time=execution_time,
        fees_paid=simulated_fees,
        slippage=simulated_slippage * 100
    )

async def _place_buy_order(self, exchange: BaseExchange, plan: ExecutionPlan):
    """Place buy order on exchange"""
    
    try:
        if plan.execution_type == ExecutionType.MARKET:
            order = await exchange.place_market_order(
                plan.opportunity.symbol,
                OrderSide.BUY,
                plan.buy_amount
            )
        else:
            order = await exchange.place_limit_order(
                plan.opportunity.symbol,
                OrderSide.BUY,
                plan.buy_amount,
                plan.buy_price
            )
        
        plan.buy_order_id = order.order_id
        
        # Wait for order to fill
        filled_order = await self._wait_for_order_fill(exchange, order.order_id, plan.timeout)
        
        return self._create_order_result(filled_order, True)
        
    except Exception as e:
        logger.error("buy_order_failed",
                    exchange=exchange.name,
                    symbol=plan.opportunity.symbol,
                    error=str(e))
        return self._create_order_result(None, False, str(e))

async def _place_sell_order(self, exchange: BaseExchange, plan: ExecutionPlan):
    """Place sell order on exchange"""
    
    try:
        if plan.execution_type == ExecutionType.MARKET:
            order = await exchange.place_market_order(
                plan.opportunity.symbol,
                OrderSide.SELL,
                plan.sell_amount
            )
        else:
            order = await exchange.place_limit_order(
                plan.opportunity.symbol,
                OrderSide.SELL,
                plan.sell_amount,
                plan.sell_price
            )
        
        plan.sell_order_id = order.order_id
        
        # Wait for order to fill
        filled_order = await self._wait_for_order_fill(exchange, order.order_id, plan.timeout)
        
        return self._create_order_result(filled_order, True)
        
    except Exception as e:
        logger.error("sell_order_failed",
                    exchange=exchange.name,
                    symbol=plan.opportunity.symbol,
                    error=str(e))
        return self._create_order_result(None, False, str(e))

async def _wait_for_order_fill(self, exchange: BaseExchange, 
                             order_id: str, timeout: int) -> Order:
    """Wait for order to fill with timeout"""
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        order = await exchange.get_order(order_id)
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED]:
            return order
        
        await asyncio.sleep(0.5)  # Check every 500ms
    
    # Timeout reached - cancel order
    try:
        await exchange.cancel_order(order_id)
    except:
        pass  # Ignore cancel errors
    
    raise asyncio.TimeoutError(f"Order {order_id} timed out")

def _create_order_result(self, order: Optional[Order], success: bool, error: str = "") -> Any:
    """Create order result object"""
    
    class OrderResult:
        def __init__(self, order: Optional[Order], success: bool, error: str = ""):
            self.order = order
            self.success = success
            self.error = error
            self.fill_price = order.average_price if order and order.filled_amount > 0 else Decimal('0')
            self.fill_amount = order.filled_amount if order else Decimal('0')
            self.fees = order.fee if order else Decimal('0')
    
    return OrderResult(order, success, error)

async def _handle_partial_execution(self, plan: ExecutionPlan, buy_result, sell_result) -> ExecutionResult:
    """Handle cases where only one order was filled"""
    
    logger.warning("partial_execution_detected",
                  execution_id=plan.execution_id,
                  buy_success=buy_result.success,
                  sell_success=sell_result.success)
    
    # TODO: Implement partial fill recovery logic
    # For now, mark as failed
    
    return ExecutionResult(
        execution_id=plan.execution_id,
        success=False,
        status=ExecutionStatus.PARTIALLY_FILLED,
        profit_loss=Decimal('0'),
        error_message="Partial execution - recovery not implemented"
    )

async def _cancel_pending_orders(self, plan: ExecutionPlan):
    """Cancel any pending orders for the execution plan"""
    
    cancel_tasks = []
    
    if plan.buy_order_id and plan.buy_exchange in self.exchanges:
        cancel_tasks.append(
            self.exchanges[plan.buy_exchange].cancel_order(plan.buy_order_id)
        )
    
    if plan.sell_order_id and plan.sell_exchange in self.exchanges:
        cancel_tasks.append(
            self.exchanges[plan.sell_exchange].cancel_order(plan.sell_order_id)
        )
    
    if cancel_tasks:
        await asyncio.gather(*cancel_tasks, return_exceptions=True)

def _calculate_actual_profit(self, buy_result, sell_result) -> Decimal:
    """Calculate actual profit from execution results"""
    
    if not buy_result.success or not sell_result.success:
        return Decimal('0')
    
    # Revenue from selling
    revenue = sell_result.fill_price * sell_result.fill_amount
    
    # Cost of buying 
    cost = buy_result.fill_price * buy_result.fill_amount
    
    # Net profit minus fees
    profit = revenue - cost - buy_result.fees - sell_result.fees
    
    return profit

def _calculate_slippage(self, plan: ExecutionPlan, buy_result, sell_result) -> Decimal:
    """Calculate slippage from expected prices"""
    
    if not buy_result.success or not sell_result.success:
        return Decimal('0')
    
    # Expected profit
    expected_profit = (plan.sell_price - plan.buy_price) * plan.buy_amount
    
    # Actual profit before fees
    actual_profit = (sell_result.fill_price - buy_result.fill_price) * buy_result.fill_amount
    
    # Slippage as percentage
    if expected_profit > 0:
        slippage = ((expected_profit - actual_profit) / expected_profit) * 100
        return max(slippage, Decimal('0'))
    
    return Decimal('0')

def _update_execution_stats(self, result: ExecutionResult):
    """Update execution statistics"""
    
    self.total_executions += 1
    
    if result.success:
        self.successful_executions += 1
        self.total_profit += result.profit_loss
    
    self.total_fees += result.fees_paid
    
    # Update average execution time
    self.avg_execution_time = (
        (self.avg_execution_time * (self.total_executions - 1) + result.execution_time) 
        / self.total_executions
    )

def get_execution_status(self) -> Dict[str, Any]:
    """Get current execution engine status"""
    
    success_rate = 0.0
    if self.total_executions > 0:
        success_rate = (self.successful_executions / self.total_executions) * 100
    
    return {
        'total_executions': self.total_executions,
        'successful_executions': self.successful_executions,
        'success_rate': success_rate,
        'total_profit': float(self.total_profit),
        'total_fees': float(self.total_fees),
        'avg_execution_time': self.avg_execution_time,
        'active_executions': len(self.active_executions),
        'paper_trading': self.paper_trading
    }

async def cancel_all_active_executions(self):
    """Cancel all active executions"""
    
    cancel_tasks = []
    for execution_id, plan in self.active_executions.items():
        cancel_tasks.append(self._cancel_pending_orders(plan))
    
    if cancel_tasks:
        await asyncio.gather(*cancel_tasks, return_exceptions=True)
        
    self.active_executions.clear()
    logger.info("all_active_executions_cancelled")
```