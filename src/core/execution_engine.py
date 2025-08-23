#!/usr/bin/env python3
“””
Execution Engine for SmartArb Engine
Handles order execution, trade management, and arbitrage execution coordination
“””

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import structlog
import time
from datetime import datetime, timedelta
import uuid

from ..exchanges.base_exchange import BaseExchange, Order, OrderSide, OrderType, OrderStatus
from .risk_manager import RiskManager

logger = structlog.get_logger(**name**)

class ExecutionStatus(Enum):
“”“Execution status enumeration”””
PENDING = “pending”
PREPARING = “preparing”
EXECUTING = “executing”
COMPLETED = “completed”
FAILED = “failed”
CANCELLED = “cancelled”
PARTIAL = “partial”

class ExecutionType(Enum):
“”“Execution type enumeration”””
SINGLE_ORDER = “single_order”
ARBITRAGE = “arbitrage”
SPREAD_TRADE = “spread_trade”
PORTFOLIO_REBALANCE = “portfolio_rebalance”

@dataclass
class ExecutionPlan:
“”“Execution plan structure”””
id: str
execution_type: ExecutionType
orders: List[Dict[str, Any]]  # Order specifications
expected_profit: Decimal
max_slippage: Decimal
timeout_seconds: int
risk_checks: bool
created_time: float

```
def to_dict(self) -> Dict[str, Any]:
    return {
        'id': self.id,
        'execution_type': self.execution_type.value,
        'orders': self.orders,
        'expected_profit': float(self.expected_profit),
        'max_slippage': float(self.max_slippage),
        'timeout_seconds': self.timeout_seconds,
        'risk_checks': self.risk_checks,
        'created_time': self.created_time
    }
```

@dataclass
class ExecutionResult:
“”“Execution result structure”””
plan_id: str
status: ExecutionStatus
executed_orders: List[Order]
actual_profit: Decimal
total_fees: Decimal
slippage: Decimal
execution_time: float
error_message: Optional[str] = None
partial_fills: List[Order] = None

```
def to_dict(self) -> Dict[str, Any]:
    return {
        'plan_id': self.plan_id,
        'status': self.status.value,
        'executed_orders_count': len(self.executed_orders),
        'actual_profit': float(self.actual_profit),
        'total_fees': float(self.total_fees),
        'slippage': float(self.slippage),
        'execution_time': self.execution_time,
        'error_message': self.error_message,
        'success': self.status == ExecutionStatus.COMPLETED
    }
```

class OrderExecutor:
“”“Handles individual order execution with retry logic”””

```
def __init__(self, exchange: BaseExchange, config: Dict[str, Any]):
    self.exchange = exchange
    self.config = config
    self.max_retries = config.get('max_retries', 3)
    self.retry_delay = config.get('retry_delay_seconds', 1)
    self.order_timeout = config.get('order_timeout_seconds', 60)
    
    self.logger = structlog.get_logger(f"executor.{exchange.name}")

async def execute_order(self, order_spec: Dict[str, Any]) -> Tuple[Order, bool]:
    """Execute a single order with retry logic"""
    
    symbol = order_spec['symbol']
    side = OrderSide(order_spec['side'])
    amount = Decimal(str(order_spec['amount']))
    order_type = OrderType(order_spec.get('type', 'market'))
    price = Decimal(str(order_spec['price'])) if order_spec.get('price') else None
    
    last_error = None
    
    for attempt in range(self.max_retries + 1):
        try:
            self.logger.info("executing_order",
                           attempt=attempt + 1,
                           symbol=symbol,
                           side=side.value,
                           amount=float(amount),
                           type=order_type.value)
            
            # Place order
            order = await self.exchange.place_order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                order_type=order_type
            )
            
            # Wait for fill if market order
            if order_type == OrderType.MARKET:
                filled_order = await self._wait_for_fill(order, symbol)
                return filled_order, True
            
            # For limit orders, return immediately
            return order, True
            
        except Exception as e:
            last_error = e
            self.logger.warning("order_execution_attempt_failed",
                              attempt=attempt + 1,
                              error=str(e))
            
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay * (attempt + 1))
            else:
                self.logger.error("order_execution_failed_all_attempts",
                                symbol=symbol,
                                error=str(e))
    
    # All attempts failed
    return None, False

async def _wait_for_fill(self, order: Order, symbol: str, 
                       max_wait: Optional[int] = None) -> Order:
    """Wait for order to be filled"""
    
    max_wait = max_wait or self.order_timeout
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            # Get updated order status
            updated_order = await self.exchange.get_order(order.id, symbol)
            
            if updated_order.status == OrderStatus.FILLED:
                self.logger.info("order_filled",
                               order_id=order.id,
                               fill_time=time.time() - start_time)
                return updated_order
            
            elif updated_order.status in [OrderStatus.CANCELLED, 
                                         OrderStatus.REJECTED, 
                                         OrderStatus.EXPIRED]:
                raise Exception(f"Order {order.id} ended with status: {updated_order.status}")
            
            # Wait before checking again
            await asyncio.sleep(0.5)
            
        except Exception as e:
            self.logger.warning("order_status_check_failed",
                              order_id=order.id,
                              error=str(e))
            await asyncio.sleep(1)
    
    # Timeout reached
    self.logger.error("order_fill_timeout", order_id=order.id)
    
    # Try to cancel the order
    try:
        await self.exchange.cancel_order(order.id, symbol)
    except:
        pass
    
    raise Exception(f"Order {order.id} timed out waiting for fill")
```

class ArbitrageExecutor:
“”“Specialized executor for arbitrage opportunities”””

```
def __init__(self, exchanges: Dict[str, BaseExchange], 
             risk_manager: RiskManager, config: Dict[str, Any]):
    self.exchanges = exchanges
    self.risk_manager = risk_manager
    self.config = config
    
    # Execution settings
    self.max_execution_time = config.get('arbitrage', {}).get('max_execution_time', 30)
    self.slippage_tolerance = Decimal(str(config.get('arbitrage', {}).get('slippage_tolerance', 0.1)))
    self.enable_partial_fills = config.get('arbitrage', {}).get('enable_partial_fills', False)
    
    # Order executors for each exchange
    self.executors = {}
    for name, exchange in exchanges.items():
        self.executors[name] = OrderExecutor(exchange, config)
    
    self.logger = structlog.get_logger("executor.arbitrage")

async def execute_arbitrage(self, opportunity) -> ExecutionResult:
    """Execute arbitrage opportunity"""
    
    execution_id = str(uuid.uuid4())
    start_time = time.time()
    
    self.logger.info("arbitrage_execution_started",
                    execution_id=execution_id,
                    opportunity_id=opportunity.id,
                    expected_profit=float(opportunity.potential_profit))
    
    try:
        # Create execution plan
        plan = await self._create_arbitrage_plan(opportunity, execution_id)
        
        # Validate execution conditions
        validation_result = await self._validate_execution_conditions(opportunity)
        if not validation_result['valid']:
            return ExecutionResult(
                plan_id=execution_id,
                status=ExecutionStatus.FAILED,
                executed_orders=[],
                actual_profit=Decimal('0'),
                total_fees=Decimal('0'),
                slippage=Decimal('0'),
                execution_time=time.time() - start_time,
                error_message=validation_result['reason']
            )
        
        # Execute the arbitrage
        result = await self._execute_plan(plan)
        
        # Calculate actual profit and metrics
        actual_profit = self._calculate_actual_profit(result.executed_orders)
        total_fees = self._calculate_total_fees(result.executed_orders)
        slippage = self._calculate_slippage(opportunity, result.executed_orders)
        
        # Update result
        result.actual_profit = actual_profit
        result.total_fees = total_fees
        result.slippage = slippage
        result.execution_time = time.time() - start_time
        
        # Report to risk manager
        self.risk_manager.add_trade_result(actual_profit, opportunity.symbol)
        
        self.logger.info("arbitrage_execution_completed",
                       execution_id=execution_id,
                       status=result.status.value,
                       actual_profit=float(actual_profit),
                       execution_time=result.execution_time)
        
        return result
        
    except Exception as e:
        self.logger.error("arbitrage_execution_error",
                        execution_id=execution_id,
                        error=str(e))
        
        return ExecutionResult(
            plan_id=execution_id,
            status=ExecutionStatus.FAILED,
            executed_orders=[],
            actual_profit=Decimal('0'),
            total_fees=Decimal('0'),
            slippage=Decimal('0'),
            execution_time=time.time() - start_time,
            error_message=str(e)
        )

async def _create_arbitrage_plan(self, opportunity, execution_id: str) -> ExecutionPlan:
    """Create execution plan for arbitrage"""
    
    # Calculate trade amounts
    trade_amount = self._calculate_trade_amount(opportunity)
    
    # Create order specifications
    orders = [
        {
            'exchange': opportunity.buy_exchange,
            'symbol': opportunity.symbol,
            'side': 'buy',
            'amount': float(trade_amount),
            'type': 'market',
            'price': None
        },
        {
            'exchange': opportunity.sell_exchange,
            'symbol': opportunity.symbol,
            'side': 'sell',
            'amount': float(trade_amount),
            'type': 'market',
            'price': None
        }
    ]
    
    return ExecutionPlan(
        id=execution_id,
        execution_type=ExecutionType.ARBITRAGE,
        orders=orders,
        expected_profit=opportunity.potential_profit,
        max_slippage=self.slippage_tolerance,
        timeout_seconds=self.max_execution_time,
        risk_checks=True,
        created_time=time.time()
    )

def _calculate_trade_amount(self, opportunity) -> Decimal:
    """Calculate optimal trade amount for arbitrage"""
    
    # Start with required capital
    base_amount = opportunity.required_capital / opportunity.buy_price
    
    # Apply safety margin
    safety_margin = Decimal('0.95')  # 5% safety margin
    safe_amount = base_amount * safety_margin
    
    # Check minimum order sizes
    buy_exchange = self.exchanges[opportunity.buy_exchange]
    sell_exchange = self.exchanges[opportunity.sell_exchange]
    
    min_buy = buy_exchange.get_min_order_size(opportunity.symbol)
    min_sell = sell_exchange.get_min_order_size(opportunity.symbol)
    
    min_amount = max(min_buy, min_sell)
    
    return max(safe_amount, min_amount)

async def _validate_execution_conditions(self, opportunity) -> Dict[str, Any]:
    """Validate conditions before execution"""
    
    validation_errors = []
    
    # Check exchange connectivity
    buy_exchange = self.exchanges[opportunity.buy_exchange]
    sell_exchange = self.exchanges[opportunity.sell_exchange]
    
    if not buy_exchange.connected:
        validation_errors.append(f"Buy exchange {opportunity.buy_exchange} not connected")
    
    if not sell_exchange.connected:
        validation_errors.append(f"Sell exchange {opportunity.sell_exchange} not connected")
    
    # Check opportunity expiry
    if opportunity.is_expired:
        validation_errors.append("Opportunity has expired")
    
    # Check current prices (basic staleness check)
    try:
        current_buy_ticker = await buy_exchange.get_ticker(opportunity.symbol)
        current_sell_ticker = await sell_exchange.get_ticker(opportunity.symbol)
        
        # Check if prices have moved significantly
        price_tolerance = Decimal('0.05')  # 5% tolerance
        
        buy_price_diff = abs(current_buy_ticker.ask - opportunity.buy_price) / opportunity.buy_price
        sell_price_diff = abs(current_sell_ticker.bid - opportunity.sell_price) / opportunity.sell_price
        
        if buy_price_diff > price_tolerance:
            validation_errors.append(f"Buy price moved by {buy_price_diff:.2%}")
        
        if sell_price_diff > price_tolerance:
            validation_errors.append(f"Sell price moved by {sell_price_diff:.2%}")
            
    except Exception as e:
        validation_errors.append(f"Price validation failed: {str(e)}")
    
    # Check balances (simplified)
    try:
        trade_amount = self._calculate_trade_amount(opportunity)
        required_base = trade_amount * opportunity.buy_price
        
        # Check if we have enough balance on buy exchange
        # This is a simplified check - in practice you'd want more sophisticated balance management
        
    except Exception as e:
        validation_errors.append(f"Balance check failed: {str(e)}")
    
    return {
        'valid': len(validation_errors) == 0,
        'reason': '; '.join(validation_errors) if validation_errors else 'Validation passed'
    }

async def _execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
    """Execute the arbitrage plan"""
    
    executed_orders = []
    
    try:
        # Execute orders simultaneously for arbitrage
        if plan.execution_type == ExecutionType.ARBITRAGE:
            return await self._execute_simultaneous_orders(plan)
        
        # Execute orders sequentially for other types
        else:
            return await self._execute_sequential_orders(plan)
            
    except Exception as e:
        return ExecutionResult(
            plan_id=plan.id,
            status=ExecutionStatus.FAILED,
            executed_orders=executed_orders,
            actual_profit=Decimal('0'),
            total_fees=Decimal('0'),
            slippage=Decimal('0'),
            execution_time=0,
            error_message=str(e)
        )

async def _execute_simultaneous_orders(self, plan: ExecutionPlan) -> ExecutionResult:
    """Execute orders simultaneously for arbitrage"""
    
    # Create tasks for concurrent execution
    tasks = []
    
    for order_spec in plan.orders:
        exchange_name = order_spec['exchange']
        executor = self.executors[exchange_name]
        
        task = asyncio.create_task(
            executor.execute_order(order_spec),
            name=f"order_{exchange_name}_{order_spec['side']}"
        )
        tasks.append(task)
    
    # Execute with timeout
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=plan.timeout_seconds
        )
        
        executed_orders = []
        failed_orders = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error("order_execution_failed",
                                order_index=i,
                                error=str(result))
                failed_orders.append(str(result))
            else:
                order, success = result
                if success and order:
                    executed_orders.append(order)
                else:
                    failed_orders.append(f"Order {i} failed")
        
        # Determine overall status
        if len(executed_orders) == len(plan.orders):
            status = ExecutionStatus.COMPLETED
        elif len(executed_orders) > 0:
            status = ExecutionStatus.PARTIAL
        else:
            status = ExecutionStatus.FAILED
        
        error_message = None
        if failed_orders:
            error_message = '; '.join(failed_orders)
        
        return ExecutionResult(
            plan_id=plan.id,
            status=status,
            executed_orders=executed_orders,
            actual_profit=Decimal('0'),  # Will be calculated later
            total_fees=Decimal('0'),     # Will be calculated later
            slippage=Decimal('0'),       # Will be calculated later
            execution_time=0,            # Will be set later
            error_message=error_message
        )
        
    except asyncio.TimeoutError:
        self.logger.error("arbitrage_execution_timeout", plan_id=plan.id)
        
        # Cancel any remaining orders
        await self._cancel_pending_orders(tasks)
        
        return ExecutionResult(
            plan_id=plan.id,
            status=ExecutionStatus.FAILED,
            executed_orders=[],
            actual_profit=Decimal('0'),
            total_fees=Decimal('0'),
            slippage=Decimal('0'),
            execution_time=0,
            error_message="Execution timeout"
        )

async def _execute_sequential_orders(self, plan: ExecutionPlan) -> ExecutionResult:
    """Execute orders sequentially"""
    
    executed_orders = []
    
    for order_spec in plan.orders:
        exchange_name = order_spec['exchange']
        executor = self.executors[exchange_name]
        
        try:
            order, success = await executor.execute_order(order_spec)
            
            if success and order:
                executed_orders.append(order)
            else:
                # Order failed - stop execution
                return ExecutionResult(
                    plan_id=plan.id,
                    status=ExecutionStatus.FAILED,
                    executed_orders=executed_orders,
                    actual_profit=Decimal('0'),
                    total_fees=Decimal('0'),
                    slippage=Decimal('0'),
                    execution_time=0,
                    error_message=f"Order failed on {exchange_name}"
                )
                
        except Exception as e:
            self.logger.error("sequential_order_failed",
                            exchange=exchange_name,
                            error=str(e))
            
            return ExecutionResult(
                plan_id=plan.id,
                status=ExecutionStatus.FAILED,
                executed_orders=executed_orders,
                actual_profit=Decimal('0'),
                total_fees=Decimal('0'),
                slippage=Decimal('0'),
                execution_time=0,
                error_message=str(e)
            )
    
    # All orders executed successfully
    return ExecutionResult(
        plan_id=plan.id,
        status=ExecutionStatus.COMPLETED,
        executed_orders=executed_orders,
        actual_profit=Decimal('0'),  # Will be calculated later
        total_fees=Decimal('0'),     # Will be calculated later
        slippage=Decimal('0'),       # Will be calculated later
        execution_time=0             # Will be set later
    )

async def _cancel_pending_orders(self, tasks: List[asyncio.Task]):
    """Cancel pending order tasks"""
    for task in tasks:
        if not task.done():
            task.cancel()
    
    # Wait for cancellation
    await asyncio.gather(*tasks, return_exceptions=True)

def _calculate_actual_profit(self, orders: List[Order]) -> Decimal:
    """Calculate actual profit from executed orders"""
    
    total_revenue = Decimal('0')
    total_cost = Decimal('0')
    
    for order in orders:
        if order.side == OrderSide.BUY:
            total_cost += order.cost + order.fee
        else:  # SELL
            total_revenue += order.cost - order.fee
    
    return total_revenue - total_cost

def _calculate_total_fees(self, orders: List[Order]) -> Decimal:
    """Calculate total fees from executed orders"""
    return sum(order.fee for order in orders)

def _calculate_slippage(self, opportunity, orders: List[Order]) -> Decimal:
    """Calculate slippage from expected vs actual prices"""
    
    # Simplified slippage calculation
    # In practice, you'd want more sophisticated slippage analysis
    
    expected_buy_price = opportunity.buy_price
    expected_sell_price = opportunity.sell_price
    
    actual_buy_price = None
    actual_sell_price = None
    
    for order in orders:
        if order.side == OrderSide.BUY:
            actual_buy_price = order.price
        else:  # SELL
            actual_sell_price = order.price
    
    if actual_buy_price and actual_sell_price:
        expected_spread = expected_sell_price - expected_buy_price
        actual_spread = actual_sell_price - actual_buy_price
        
        if expected_spread != 0:
            slippage_percentage = (expected_spread - actual_spread) / expected_spread * 100
            return Decimal(str(slippage_percentage))
    
    return Decimal('0')
```

class ExecutionEngine:
“”“Main execution engine coordinating all trade execution”””

```
def __init__(self, exchanges: Dict[str, BaseExchange], 
             risk_manager: RiskManager, config: Dict[str, Any]):
    
    self.exchanges = exchanges
    self.risk_manager = risk_manager
    self.config = config
    
    # Initialize specialized executors
    self.arbitrage_executor = ArbitrageExecutor(exchanges, risk_manager, config)
    
    # Order executors for individual exchanges
    self.order_executors = {}
    for name, exchange in exchanges.items():
        self.order_executors[name] = OrderExecutor(exchange, config)
    
    # Execution tracking
    self.active_executions = {}
    self.execution_history = []
    self.max_history_size = 1000
    
    # Performance metrics
    self.total_executions = 0
    self.successful_executions = 0
    self.failed_executions = 0
    
    self.logger = structlog.get_logger("execution_engine")

async def execute_arbitrage(self, opportunity) -> Dict[str, Any]:
    """Execute arbitrage opportunity"""
    
    self.total_executions += 1
    
    try:
        result = await self.arbitrage_executor.execute_arbitrage(opportunity)
        
        # Track execution
        self.active_executions[result.plan_id] = result
        self._add_to_history(result)
        
        # Update metrics
        if result.status == ExecutionStatus.COMPLETED:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        return result.to_dict()
        
    except Exception as e:
        self.failed_executions += 1
        self.logger.error("arbitrage_execution_error", error=str(e))
        return {
            'success': False,
            'error': str(e),
            'status': ExecutionStatus.FAILED.value
        }

async def execute_single_order(self, exchange_name: str, order_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Execute single order on specified exchange"""
    
    if exchange_name not in self.order_executors:
        return {
            'success': False,
            'error': f'Exchange {exchange_name} not available'
        }
    
    try:
        executor = self.order_executors[exchange_name]
        order, success = await executor.execute_order(order_spec)
        
        if success and order:
            return {
                'success': True,
                'order': {
                    'id': order.id,
                    'symbol': order.symbol,
                    'side': order.side.value,
                    'amount': float(order.amount),
                    'price': float(order.price) if order.price else None,
                    'status': order.status.value,
                    'filled': float(order.filled),
                    'cost': float(order.cost),
                    'fee': float(order.fee)
                }
            }
        else:
            return {
                'success': False,
                'error': 'Order execution failed'
            }
            
    except Exception as e:
        self.logger.error("single_order_execution_error",
                        exchange=exchange_name,
                        error=str(e))
        return {
            'success': False,
            'error': str(e)
        }

def _add_to_history(self, result: ExecutionResult):
    """Add execution result to history"""
    
    self.execution_history.append(result)
    
    # Manage history size
    if len(self.execution_history) > self.max_history_size:
        self.execution_history = self.execution_history[-self.max_history_size:]

def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
    """Get status of specific execution"""
    
    if execution_id in self.active_executions:
        return self.active_executions[execution_id].to_dict()
    
    # Search in history
    for result in self.execution_history:
        if result.plan_id == execution_id:
            return result.to_dict()
    
    return None

def get_performance_metrics(self) -> Dict[str, Any]:
    """Get execution engine performance metrics"""
    
    success_rate = (self.successful_executions / max(self.total_executions, 1)) * 100
    
    # Calculate recent performance (last 24 hours)
    recent_cutoff = time.time() - (24 * 60 * 60)
    recent_executions = [r for r in self.execution_history 
                       if r.execution_time > recent_cutoff]
    
    recent_successful = len([r for r in recent_executions 
                           if r.status == ExecutionStatus.COMPLETED])
    recent_success_rate = (recent_successful / max(len(recent_executions), 1)) * 100
    
    # Calculate average execution time
    completed_executions = [r for r in self.execution_history 
                          if r.status == ExecutionStatus.COMPLETED]
    avg_execution_time = (sum(r.execution_time for r in completed_executions) / 
                        max(len(completed_executions), 1))
    
    return {
        'total_executions': self.total_executions,
        'successful_executions': self.successful_executions,
        'failed_executions': self.failed_executions,
        'success_rate_percent': success_rate,
        'recent_24h_executions': len(recent_executions),
        'recent_24h_success_rate_percent': recent_success_rate,
        'average_execution_time_seconds': avg_execution_time,
        'active_executions': len(self.active_executions)
    }
```