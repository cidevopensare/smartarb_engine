“””
Execution Engine for SmartArb Engine
Handles the execution of arbitrage opportunities with advanced order management
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
from ..strategies.base_strategy import Opportunity, OpportunityStatus
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

class ExecutionMode(Enum):
“”“Execution mode enumeration”””
PAPER_TRADING = “paper_trading”
LIVE_TRADING = “live_trading”
SIMULATION = “simulation”

@dataclass
class ExecutionPlan:
“”“Execution plan for an opportunity”””
opportunity_id: str
orders: List[Dict[str, Any]]  # List of orders to execute
total_amount: Decimal
expected_profit: Decimal
execution_sequence: List[str]  # Order of execution
contingency_plan: Optional[Dict[str, Any]] = None
timeout_seconds: float = 30.0

```
@property
def order_count(self) -> int:
    return len(self.orders)
```

@dataclass
class ExecutionResult:
“”“Result of opportunity execution”””
opportunity_id: str
status: ExecutionStatus
executed_orders: List[Order]
failed_orders: List[Dict[str, Any]]
actual_profit: Decimal
execution_time: float
fees_paid: Decimal
slippage: Decimal
error_message: Optional[str] = None

```
@property
def success_rate(self) -> float:
    total_orders = len(self.executed_orders) + len(self.failed_orders)
    return len(self.executed_orders) / max(total_orders, 1) * 100

@property
def profit_vs_expected(self) -> float:
    """Calculate actual profit vs expected profit ratio"""
    if self.actual_profit == 0:
        return 0.0
    return float(self.actual_profit / self.actual_profit) * 100
```

class ExecutionEngine:
“””
Advanced Trade Execution Engine

```
Features:
- Simultaneous multi-exchange execution
- Paper trading mode
- Advanced order management
- Slippage protection
- Timeout handling
- Partial fill management
- Execution analytics
"""

def __init__(self, exchanges: Dict[str, BaseExchange], 
             risk_manager: RiskManager, config: Dict[str, Any]):
    self.exchanges = exchanges
    self.risk_manager = risk_manager
    self.config = config
    
    # Execution settings
    trading_config = config.get('trading', {})
    self.execution_mode = ExecutionMode.PAPER_TRADING if trading_config.get('paper_trading', True) else ExecutionMode.LIVE_TRADING
    self.default_order_type = trading_config.get('default_order_type', 'limit')
    self.order_timeout = trading_config.get('order_timeout', 30)
    self.max_slippage_percent = Decimal(str(trading_config.get('max_slippage_percent', 0.10)))
    
    # Execution tracking
    self.pending_executions: Dict[str, ExecutionPlan] = {}
    self.active_executions: Dict[str, Dict[str, Any]] = {}
    self.execution_history: List[ExecutionResult] = []
    
    # Performance metrics
    self.total_executions = 0
    self.successful_executions = 0
    self.total_profit = Decimal('0')
    self.total_fees = Decimal('0')
    self.average_execution_time = 0.0
    
    # Paper trading tracking
    self.paper_balance = Decimal('10000')  # Start with $10,000 paper money
    self.paper_positions: Dict[str, Decimal] = {}
    
    logger.info("execution_engine_initialized",
               mode=self.execution_mode.value,
               order_timeout=self.order_timeout,
               paper_balance=float(self.paper_balance) if self.execution_mode == ExecutionMode.PAPER_TRADING else None)

async def execute_opportunity(self, opportunity: Opportunity, 
                            risk_assessment: RiskAssessment) -> ExecutionResult:
    """
    Execute a trading opportunity
    
    Args:
        opportunity: The opportunity to execute
        risk_assessment: Risk assessment for the opportunity
        
    Returns:
        ExecutionResult with details of the execution
    """
    start_time = time.time()
    
    try:
        logger.info("execution_started",
                   opportunity_id=opportunity.opportunity_id,
                   mode=self.execution_mode.value,
                   risk_level=risk_assessment.risk_level.value)
        
        # Update opportunity status
        opportunity.update_status(OpportunityStatus.EXECUTING)
        
        # Create execution plan
        execution_plan = await self._create_execution_plan(opportunity, risk_assessment)
        if not execution_plan:
            return ExecutionResult(
                opportunity_id=opportunity.opportunity_id,
                status=ExecutionStatus.FAILED,
                executed_orders=[],
                failed_orders=[],
                actual_profit=Decimal('0'),
                execution_time=time.time() - start_time,
                fees_paid=Decimal('0'),
                slippage=Decimal('0'),
                error_message="Failed to create execution plan"
            )
        
        # Add to tracking
        self.pending_executions[opportunity.opportunity_id] = execution_plan
        self.active_executions[opportunity.opportunity_id] = {
            'start_time': start_time,
            'plan': execution_plan,
            'orders': []
        }
        
        # Execute based on mode
        if self.execution_mode == ExecutionMode.PAPER_TRADING:
            result = await self._execute_paper_trading(opportunity, execution_plan)
        else:
            result = await self._execute_live_trading(opportunity, execution_plan)
        
        # Update tracking
        self._update_execution_metrics(result)
        self.execution_history.append(result)
        
        # Cleanup
        self.pending_executions.pop(opportunity.opportunity_id, None)
        self.active_executions.pop(opportunity.opportunity_id, None)
        
        # Update opportunity status
        if result.status == ExecutionStatus.COMPLETED:
            opportunity.update_status(OpportunityStatus.EXECUTED)
            opportunity.actual_profit = result.actual_profit
        else:
            opportunity.update_status(OpportunityStatus.FAILED)
        
        logger.info("execution_completed",
                   opportunity_id=opportunity.opportunity_id,
                   status=result.status.value,
                   profit=float(result.actual_profit),
                   execution_time=result.execution_time)
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = str(e)
        
        logger.error("execution_failed",
                    opportunity_id=opportunity.opportunity_id,
                    error=error_msg,
                    execution_time=execution_time)
        
        # Cleanup on error
        self.pending_executions.pop(opportunity.opportunity_id, None)
        self.active_executions.pop(opportunity.opportunity_id, None)
        
        return ExecutionResult(
            opportunity_id=opportunity.opportunity_id,
            status=ExecutionStatus.FAILED,
            executed_orders=[],
            failed_orders=[],
            actual_profit=Decimal('0'),
            execution_time=execution_time,
            fees_paid=Decimal('0'),
            slippage=Decimal('0'),
            error_message=error_msg
        )

async def _create_execution_plan(self, opportunity: Opportunity, 
                               risk_assessment: RiskAssessment) -> Optional[ExecutionPlan]:
    """Create detailed execution plan for the opportunity"""
    try:
        # Use recommended position size from risk assessment
        position_size = risk_assessment.recommended_position_size
        
        if position_size <= 0:
            logger.warning("zero_position_size_recommended", 
                         opportunity_id=opportunity.opportunity_id)
            return None
        
        # Create orders based on opportunity type
        orders = []
        
        # Check if this is a spatial arbitrage opportunity
        if hasattr(opportunity, 'buy_exchange') and hasattr(opportunity, 'sell_exchange'):
            # Spatial arbitrage - simultaneous buy and sell
            base_asset, quote_asset = opportunity.symbol.split('/')
            
            # Buy order (on cheaper exchange)
            buy_order = {
                'exchange': opportunity.buy_exchange,
                'symbol': opportunity.symbol,
                'side': OrderSide.BUY,
                'amount': position_size,
                'price': getattr(opportunity, 'buy_price', Decimal('0')),
                'type': self.default_order_type,
                'order_id': str(uuid.uuid4())
            }
            
            # Sell order (on more expensive exchange)
            sell_order = {
                'exchange': opportunity.sell_exchange,
                'symbol': opportunity.symbol,
                'side': OrderSide.SELL,
                'amount': position_size,
                'price': getattr(opportunity, 'sell_price', Decimal('0')),
                'type': self.default_order_type,
                'order_id': str(uuid.uuid4())
            }
            
            orders = [buy_order, sell_order]
            execution_sequence = ['simultaneous']  # Execute both simultaneously
        
        else:
            # Single exchange opportunity (future implementation)
            orders = [{
                'exchange': list(self.exchanges.keys())[0],  # Default to first exchange
                'symbol': opportunity.symbol,
                'side': OrderSide.BUY,  # Default action
                'amount': position_size,
                'price': Decimal('0'),  # Market order
                'type': 'market',
                'order_id': str(uuid.uuid4())
            }]
            execution_sequence = ['sequential']
        
        plan = ExecutionPlan(
            opportunity_id=opportunity.opportunity_id,
            orders=orders,
            total_amount=position_size,
            expected_profit=opportunity.expected_profit,
            execution_sequence=execution_sequence,
            timeout_seconds=self.order_timeout
        )
        
        logger.debug("execution_plan_created",
                    opportunity_id=opportunity.opportunity_id,
                    order_count=len(orders),
                    total_amount=float(position_size))
        
        return plan
        
    except Exception as e:
        logger.error("execution_plan_creation_failed",
                    opportunity_id=opportunity.opportunity_id,
                    error=str(e))
        return None

async def _execute_paper_trading(self, opportunity: Opportunity, 
                               plan: ExecutionPlan) -> ExecutionResult:
    """Execute opportunity in paper trading mode"""
    start_time = time.time()
    executed_orders = []
    failed_orders = []
    total_fees = Decimal('0')
    
    try:
        logger.debug("paper_trading_execution",
                    opportunity_id=opportunity.opportunity_id)
        
        # Simulate execution delay
        await asyncio.sleep(0.1)  # 100ms simulated execution time
        
        for order_data in plan.orders:
            try:
                # Simulate order execution
                exchange_name = order_data['exchange']
                
                # Get exchange for fee calculation
                exchange = self.exchanges.get(exchange_name)
                if not exchange:
                    failed_orders.append({**order_data, 'error': 'Exchange not available'})
                    continue
                
                # Calculate fees
                trade_value = order_data['amount'] * order_data['price']
                fee = trade_value * exchange.get_trading_fee(is_maker=True)
                total_fees += fee
                
                # Create simulated order
                simulated_order = Order(
                    order_id=order_data['order_id'],
                    symbol=order_data['symbol'],
                    side=order_data['side'],
                    amount=order_data['amount'],
                    price=order_data['price'],
                    status=OrderStatus.FILLED,
                    filled_amount=order_data['amount'],
                    average_price=order_data['price'],
                    fees=fee,
                    timestamp=time.time()
                )
                
                executed_orders.append(simulated_order)
                
                # Update paper balance
                if order_data['side'] == OrderSide.BUY:
                    self.paper_balance -= trade_value + fee
                else:
                    self.paper_balance += trade_value - fee
                
                logger.debug("paper_order_executed",
                           order_id=order_data['order_id'],
                           side=order_data['side'].value,
                           amount=float(order_data['amount']),
                           price=float(order_data['price']))
            
            except Exception as e:
                logger.error("paper_order_failed",
                           order_id=order_data['order_id'],
                           error=str(e))
                failed_orders.append({**order_data, 'error': str(e)})
        
        # Calculate actual profit (simplified for paper trading)
        actual_profit = plan.expected_profit - total_fees
        
        # Determine execution status
        if len(failed_orders) == 0:
            status = ExecutionStatus.COMPLETED
        elif len(executed_orders) > 0:
            status = ExecutionStatus.PARTIALLY_FILLED
        else:
            status = ExecutionStatus.FAILED
            actual_profit = Decimal('0')
        
        execution_time = time.time() - start_time
        
        return ExecutionResult(
            opportunity_id=opportunity.opportunity_id,
            status=status,
            executed_orders=executed_orders,
            failed_orders=failed_orders,
            actual_profit=actual_profit,
            execution_time=execution_time,
            fees_paid=total_fees,
            slippage=Decimal('0')  # No slippage in paper trading
        )
        
    except Exception as e:
        logger.error("paper_trading_execution_failed",
                    opportunity_id=opportunity.opportunity_id,
                    error=str(e))
        
        return ExecutionResult(
            opportunity_id=opportunity.opportunity_id,
            status=ExecutionStatus.FAILED,
            executed_orders=executed_orders,
            failed_orders=failed_orders,
            actual_profit=Decimal('0'),
            execution_time=time.time() - start_time,
            fees_paid=total_fees,
            slippage=Decimal('0'),
            error_message=str(e)
        )

async def _execute_live_trading(self, opportunity: Opportunity, 
                              plan: ExecutionPlan) -> ExecutionResult:
    """Execute opportunity in live trading mode"""
    start_time = time.time()
    executed_orders = []
    failed_orders = []
    total_fees = Decimal('0')
    
    try:
        logger.info("live_trading_execution",
                   opportunity_id=opportunity.opportunity_id,
                   order_count=len(plan.orders))
        
        # Execute orders based on execution sequence
        if plan.execution_sequence[0] == 'simultaneous':
            # Execute all orders simultaneously
            tasks = []
            for order_data in plan.orders:
                task = asyncio.create_task(
                    self._execute_single_order(order_data)
                )
                tasks.append(task)
            
            # Wait for all orders with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=plan.timeout_seconds
                )
                
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed_orders.append({
                            **plan.orders[i], 
                            'error': str(result)
                        })
                    else:
                        executed_orders.append(result)
                        total_fees += result.fees
                        
            except asyncio.TimeoutError:
                logger.warning("execution_timeout",
                             opportunity_id=opportunity.opportunity_id)
                # Cancel any pending tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()
                
                return ExecutionResult(
                    opportunity_id=opportunity.opportunity_id,
                    status=ExecutionStatus.TIMEOUT,
                    executed_orders=executed_orders,
                    failed_orders=failed_orders,
                    actual_profit=Decimal('0'),
                    execution_time=time.time() - start_time,
                    fees_paid=total_fees,
                    slippage=Decimal('0'),
                    error_message="Execution timeout"
                )
        
        else:  # Sequential execution
            for order_data in plan.orders:
                try:
                    order = await self._execute_single_order(order_data)
                    executed_orders.append(order)
                    total_fees += order.fees
                except Exception as e:
                    logger.error("order_execution_failed",
                               order_id=order_data['order_id'],
                               error=str(e))
                    failed_orders.append({**order_data, 'error': str(e)})
                    break  # Stop on first failure in sequential mode
        
        # Calculate actual profit
        actual_profit = await self._calculate_actual_profit(
            executed_orders, plan.expected_profit
        )
        
        # Calculate slippage
        slippage = await self._calculate_slippage(executed_orders, plan.orders)
        
        # Determine execution status
        if len(failed_orders) == 0 and len(executed_orders) == len(plan.orders):
            status = ExecutionStatus.COMPLETED
        elif len(executed_orders) > 0:
            status = ExecutionStatus.PARTIALLY_FILLED
            # Handle partial fills - might need to cancel remaining orders
        else:
            status = ExecutionStatus.FAILED
            actual_profit = Decimal('0')
        
        execution_time = time.time() - start_time
        
        return ExecutionResult(
            opportunity_id=opportunity.opportunity_id,
            status=status,
            executed_orders=executed_orders,
            failed_orders=failed_orders,
            actual_profit=actual_profit,
            execution_time=execution_time,
            fees_paid=total_fees,
            slippage=slippage
        )
        
    except Exception as e:
        logger.error("live_trading_execution_failed",
                    opportunity_id=opportunity.opportunity_id,
                    error=str(e))
        
        return ExecutionResult(
            opportunity_id=opportunity.opportunity_id,
            status=ExecutionStatus.FAILED,
            executed_orders=executed_orders,
            failed_orders=failed_orders,
            actual_profit=Decimal('0'),
            execution_time=time.time() - start_time,
            fees_paid=total_fees,
            slippage=Decimal('0'),
            error_message=str(e)
        )

async def _execute_single_order(self, order_data: Dict[str, Any]) -> Order:
    """Execute a single order on the specified exchange"""
    exchange_name = order_data['exchange']
    exchange = self.exchanges.get(exchange_name)
    
    if not exchange:
        raise Exception(f"Exchange {exchange_name} not available")
    
    if not exchange.is_connected:
        raise Exception(f"Exchange {exchange_name} not connected")
    
    try:
        # Place the order
        order = await exchange.place_order(
            symbol=order_data['symbol'],
            side=order_data['side'],
            amount=order_data['amount'],
            price=order_data['price'],
            order_type=order_data['type']
        )
        
        # Monitor order until filled or timeout
        timeout = 30  # 30 seconds timeout for individual orders
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            order_status = await exchange.get_order_status(order.order_id, order_data['symbol'])
            
            if order_status.status == OrderStatus.FILLED:
                logger.info("order_filled",
                           order_id=order.order_id,
                           exchange=exchange_name,
                           symbol=order_data['symbol'],
                           side=order_data['side'].value)
                return order_status
            
            elif order_status.status == OrderStatus.CANCELED:
                raise Exception(f"Order {order.order_id} was canceled")
            
            elif order_status.status == OrderStatus.REJECTED:
                raise Exception(f"Order {order.order_id} was rejected")
            
            await asyncio.sleep(0.5)  # Check every 500ms
        
        # Timeout - cancel order
        await exchange.cancel_order(order.order_id, order_data['symbol'])
        raise Exception(f"Order {order.order_id} timed out")
        
    except Exception as e:
        # Update exchange reliability
        self.risk_manager.update_exchange_reliability(exchange_name, False)
        raise e

async def _calculate_actual_profit(self, executed_orders: List[Order], 
                                 expected_profit: Decimal) -> Decimal:
    """Calculate actual profit from executed orders"""
    if not executed_orders:
        return Decimal('0')
    
    # Simple implementation - for spatial arbitrage
    buy_value = Decimal('0')
    sell_value = Decimal('0')
    total_fees = Decimal('0')
    
    for order in executed_orders:
        trade_value = order.filled_amount * order.average_price
        total_fees += order.fees
        
        if order.side == OrderSide.BUY:
            buy_value += trade_value
        else:
            sell_value += trade_value
    
    # Profit = sell_value - buy_value - fees
    actual_profit = sell_value - buy_value - total_fees
    
    return actual_profit

async def _calculate_slippage(self, executed_orders: List[Order], 
                            planned_orders: List[Dict[str, Any]]) -> Decimal:
    """Calculate slippage between planned and executed prices"""
    if not executed_orders or not planned_orders:
        return Decimal('0')
    
    total_slippage = Decimal('0')
    order_count = 0
    
    # Match executed orders with planned orders
    for executed in executed_orders:
        for planned in planned_orders:
            if (planned['order_id'] == executed.order_id or 
                (planned['symbol'] == executed.symbol and 
                 planned['side'] == executed.side)):
                
                planned_price = planned['price']
                executed_price = executed.average_price
                
                if planned_price > 0:
                    slippage = abs(executed_price - planned_price) / planned_price * 100
                    total_slippage += slippage
                    order_count += 1
                break
    
    return total_slippage / max(order_count, 1)

def _update_execution_metrics(self, result: ExecutionResult) -> None:
    """Update execution performance metrics"""
    self.total_executions += 1
    
    if result.status == ExecutionStatus.COMPLETED:
        self.successful_executions += 1
        self.total_profit += result.actual_profit
    
    self.total_fees += result.fees_paid
    
    # Update average execution time
    self.average_execution_time = (
        (self.average_execution_time * (self.total_executions - 1) + result.execution_time) 
        / self.total_executions
    )

# Status and Control Methods
async def cancel_execution(self, opportunity_id: str) -> bool:
    """Cancel an ongoing execution"""
    if opportunity_id not in self.active_executions:
        return False
    
    try:
        # Cancel any active orders
        execution_data = self.active_executions[opportunity_id]
        for order_info in execution_data.get('orders', []):
            if 'order_id' in order_info and 'exchange' in order_info:
                exchange = self.exchanges.get(order_info['exchange'])
                if exchange:
                    await exchange.cancel_order(
                        order_info['order_id'], 
                        order_info.get('symbol', '')
                    )
        
        # Remove from tracking
        self.pending_executions.pop(opportunity_id, None)
        self.active_executions.pop(opportunity_id, None)
        
        logger.info("execution_cancelled", opportunity_id=opportunity_id)
        return True
        
    except Exception as e:
        logger.error("execution_cancellation_failed",
                    opportunity_id=opportunity_id,
                    error=str(e))
        return False

def get_execution_status(self) -> Dict[str, Any]:
    """Get current execution engine status"""
    success_rate = 0.0
    if self.total_executions > 0:
        success_rate = (self.successful_executions / self.total_executions) * 100
    
    return {
        'execution_mode': self.execution_mode.value,
        'active_executions': len(self.active_executions),
        'pending_executions': len(self.pending_executions),
        'total_executions': self.total_executions,
        'successful_executions': self.successful_executions,
        'success_rate': success_rate,
        'total_profit': float(self.total_profit),
        'total_fees': float(self.total_fees),
        'average_execution_time': self.average_execution_time,
        'paper_balance': float(self.paper_balance) if self.execution_mode == ExecutionMode.PAPER_TRADING else None
    }

def get_recent_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent execution results"""
    recent = self.execution_history[-limit:]
    return [
        {
            'opportunity_id': result.opportunity_id,
            'status': result.status.value,
            'actual_profit': float(result.actual_profit),
            'execution_time': result.execution_time,
            'fees_paid': float(result.fees_paid),
            'slippage': float(result.slippage),
            'success_rate': result.success_rate,
            'error_message': result.error_message
        }
        for result in recent
    ]

def set_execution_mode(self, mode: ExecutionMode) -> None:
    """Change execution mode"""
    old_mode = self.execution_mode
    self.execution_mode = mode
    
    logger.info("execution_mode_changed",
               old_mode=old_mode.value,
               new_mode=mode.value)
    
    if mode == ExecutionMode.PAPER_TRADING and old_mode != ExecutionMode.PAPER_TRADING:
        # Reset paper trading balance
        self.paper_balance = Decimal('10000')
        self.paper_positions = {}

async def emergency_stop_all(self) -> None:
    """Emergency stop all active executions"""
    logger.critical("emergency_stop_all_executions",
                   active_count=len(self.active_executions))
    
    # Cancel all active executions
    for opportunity_id in list(self.active_executions.keys()):
        await self.cancel_execution(opportunity_id)
    
    # Clear all pending executions
    self.pending_executions.clear()
```