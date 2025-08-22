“””
Portfolio Manager for SmartArb Engine
Manages portfolio balances, positions, and performance tracking across exchanges
“””

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime, timedelta
import structlog

from ..exchanges.base_exchange import BaseExchange, Balance

logger = structlog.get_logger(**name**)

@dataclass
class PortfolioBalance:
“”“Portfolio balance across all exchanges”””
asset: str
total_balance: Decimal
available_balance: Decimal
locked_balance: Decimal
exchange_balances: Dict[str, Balance]
last_updated: float

```
@property
def exchange_count(self) -> int:
    return len(self.exchange_balances)

@property
def concentration_risk(self) -> float:
    """Calculate concentration risk (highest single exchange %)"""
    if self.total_balance == 0:
        return 0.0
    
    max_balance = max(
        balance.total for balance in self.exchange_balances.values()
    )
    return float(max_balance / self.total_balance * 100)
```

@dataclass
class PortfolioSnapshot:
“”“Snapshot of portfolio at a point in time”””
timestamp: float
total_value_usd: Decimal
balances: Dict[str, PortfolioBalance]
pnl_24h: Decimal
pnl_7d: Decimal
pnl_30d: Decimal

```
@property
def asset_count(self) -> int:
    return len(self.balances)

@property
def total_assets_value(self) -> Decimal:
    return sum(balance.total_balance for balance in self.balances.values())
```

class PortfolioManager:
“””
Advanced Portfolio Management System

```
Features:
- Multi-exchange balance tracking
- Real-time portfolio valuation
- Performance analytics
- Risk metrics calculation
- Rebalancing recommendations
- Historical tracking
"""

def __init__(self, exchanges: Dict[str, BaseExchange], config: Dict[str, Any]):
    self.exchanges = exchanges
    self.config = config
    
    # Portfolio state
    self.current_balances: Dict[str, PortfolioBalance] = {}
    self.portfolio_history: List[PortfolioSnapshot] = []
    self.last_update_time = 0
    
    # Configuration
    self.update_frequency = config.get('portfolio', {}).get('update_frequency', 30)  # seconds
    self.min_balance_threshold = Decimal(str(config.get('portfolio', {}).get('min_balance_threshold', 1.0)))  # $1 minimum
    self.price_cache_duration = 300  # 5 minutes
    
    # Price tracking for valuation
    self.price_cache: Dict[str, Tuple[Decimal, float]] = {}  # symbol -> (price, timestamp)
    self.reference_currency = config.get('portfolio', {}).get('reference_currency', 'USDT')
    
    # Performance tracking
    self.total_profit_loss = Decimal('0')
    self.daily_pnl = Decimal('0')
    self.max_portfolio_value = Decimal('0')
    self.max_drawdown = Decimal('0')
    
    # Risk metrics
    self.risk_metrics = {
        'var_95': Decimal('0'),  # Value at Risk 95%
        'max_concentration': 0.0,  # Max single asset concentration %
        'exchange_concentration': 0.0,  # Max single exchange concentration %
        'correlation_risk': 0.0  # Portfolio correlation risk
    }
    
    logger.info("portfolio_manager_initialized",
               exchanges=len(self.exchanges),
               reference_currency=self.reference_currency,
               update_frequency=self.update_frequency)

async def update_portfolio(self, force_update: bool = False) -> None:
    """Update portfolio balances from all exchanges"""
    now = time.time()
    
    if not force_update and (now - self.last_update_time) < self.update_frequency:
        return
    
    try:
        logger.debug("updating_portfolio_balances")
        
        # Fetch balances from all exchanges concurrently
        balance_tasks = []
        for exchange_name, exchange in self.exchanges.items():
            if exchange.is_connected:
                task = asyncio.create_task(
                    self._fetch_exchange_balances(exchange_name, exchange)
                )
                balance_tasks.append(task)
        
        # Wait for all balance updates
        exchange_balances_list = await asyncio.gather(*balance_tasks, return_exceptions=True)
        
        # Consolidate balances across exchanges
        consolidated_balances = {}
        
        for result in exchange_balances_list:
            if isinstance(result, Exception):
                logger.warning("exchange_balance_fetch_failed", error=str(result))
                continue
            
            exchange_name, exchange_balances = result
            
            for asset, balance in exchange_balances.items():
                if asset not in consolidated_balances:
                    consolidated_balances[asset] = {
                        'total_balance': Decimal('0'),
                        'available_balance': Decimal('0'),
                        'locked_balance': Decimal('0'),
                        'exchange_balances': {}
                    }
                
                # Add to consolidated totals
                consolidated_balances[asset]['total_balance'] += balance.total
                consolidated_balances[asset]['available_balance'] += balance.free
                consolidated_balances[asset]['locked_balance'] += balance.locked
                consolidated_balances[asset]['exchange_balances'][exchange_name] = balance
        
        # Create PortfolioBalance objects
        new_balances = {}
        for asset, data in consolidated_balances.items():
            # Only include assets with meaningful balances
            if data['total_balance'] >= self.min_balance_threshold:
                new_balances[asset] = PortfolioBalance(
                    asset=asset,
                    total_balance=data['total_balance'],
                    available_balance=data['available_balance'],
                    locked_balance=data['locked_balance'],
                    exchange_balances=data['exchange_balances'],
                    last_updated=now
                )
        
        # Update current balances
        self.current_balances = new_balances
        self.last_update_time = now
        
        # Update risk metrics
        await self._update_risk_metrics()
        
        # Create portfolio snapshot
        snapshot = await self._create_portfolio_snapshot()
        self.portfolio_history.append(snapshot)
        
        # Limit history to last 1000 snapshots
        if len(self.portfolio_history) > 1000:
            self.portfolio_history = self.portfolio_history[-1000:]
        
        logger.info("portfolio_updated",
                   assets=len(new_balances),
                   total_value=float(snapshot.total_value_usd) if snapshot else 0)
        
    except Exception as e:
        logger.error("portfolio_update_failed", error=str(e))

async def _fetch_exchange_balances(self, exchange_name: str, 
                                 exchange: BaseExchange) -> Tuple[str, Dict[str, Balance]]:
    """Fetch balances from a single exchange"""
    try:
        balances = await exchange.get_balance()
        return exchange_name, balances
    except Exception as e:
        logger.warning("exchange_balance_error",
                     exchange=exchange_name,
                     error=str(e))
        return exchange_name, {}

async def _create_portfolio_snapshot(self) -> PortfolioSnapshot:
    """Create a snapshot of current portfolio state"""
    # Calculate total USD value
    total_value_usd = await self._calculate_total_value_usd()
    
    # Calculate P&L metrics
    pnl_24h = await self._calculate_pnl_period(24)
    pnl_7d = await self._calculate_pnl_period(24 * 7)
    pnl_30d = await self._calculate_pnl_period(24 * 30)
    
    snapshot = PortfolioSnapshot(
        timestamp=time.time(),
        total_value_usd=total_value_usd,
        balances=self.current_balances.copy(),
        pnl_24h=pnl_24h,
        pnl_7d=pnl_7d,
        pnl_30d=pnl_30d
    )
    
    # Update max portfolio value and drawdown
    if total_value_usd > self.max_portfolio_value:
        self.max_portfolio_value = total_value_usd
    
    current_drawdown = (self.max_portfolio_value - total_value_usd) / self.max_portfolio_value * 100
    if current_drawdown > self.max_drawdown:
        self.max_drawdown = current_drawdown
    
    return snapshot

async def _calculate_total_value_usd(self) -> Decimal:
    """Calculate total portfolio value in USD"""
    total_value = Decimal('0')
    
    for asset, balance in self.current_balances.items():
        if asset == self.reference_currency:
            # Direct USD/USDT value
            total_value += balance.total_balance
        else:
            # Convert to USD using price
            usd_price = await self._get_asset_price_usd(asset)
            if usd_price > 0:
                total_value += balance.total_balance * usd_price
    
    return total_value

async def _get_asset_price_usd(self, asset: str) -> Decimal:
    """Get current USD price for an asset"""
    if asset == self.reference_currency:
        return Decimal('1')
    
    symbol = f"{asset}/{self.reference_currency}"
    now = time.time()
    
    # Check cache first
    if symbol in self.price_cache:
        price, timestamp = self.price_cache[symbol]
        if now - timestamp < self.price_cache_duration:
            return price
    
    # Fetch current price from exchanges
    for exchange in self.exchanges.values():
        if not exchange.is_connected:
            continue
        
        try:
            ticker = await exchange.get_ticker(symbol)
            price = ticker.last
            
            # Cache the price
            self.price_cache[symbol] = (price, now)
            return price
            
        except Exception:
            continue  # Try next exchange
    
    logger.warning("price_not_found", asset=asset, symbol=symbol)
    return Decimal('0')

async def _calculate_pnl_period(self, hours: int) -> Decimal:
    """Calculate P&L for a specific time period"""
    if not self.portfolio_history:
        return Decimal('0')
    
    current_time = time.time()
    target_time = current_time - (hours * 3600)
    
    # Find closest historical snapshot
    historical_snapshot = None
    for snapshot in reversed(self.portfolio_history):
        if snapshot.timestamp <= target_time:
            historical_snapshot = snapshot
            break
    
    if not historical_snapshot:
        return Decimal('0')
    
    # Calculate current value
    current_value = await self._calculate_total_value_usd()
    
    # Calculate P&L
    return current_value - historical_snapshot.total_value_usd

async def _update_risk_metrics(self) -> None:
    """Update portfolio risk metrics"""
    if not self.current_balances:
        return
    
    # Calculate asset concentration risk
    total_value = await self._calculate_total_value_usd()
    max_asset_value = Decimal('0')
    
    for balance in self.current_balances.values():
        asset_value_usd = balance.total_balance
        if balance.asset != self.reference_currency:
            price = await self._get_asset_price_usd(balance.asset)
            asset_value_usd = balance.total_balance * price
        
        if asset_value_usd > max_asset_value:
            max_asset_value = asset_value_usd
    
    self.risk_metrics['max_concentration'] = float(max_asset_value / total_value * 100) if total_value > 0 else 0
    
    # Calculate exchange concentration risk
    exchange_values = {}
    for balance in self.current_balances.values():
        for exchange_name, exchange_balance in balance.exchange_balances.items():
            if exchange_name not in exchange_values:
                exchange_values[exchange_name] = Decimal('0')
            
            balance_value_usd = exchange_balance.total
            if balance.asset != self.reference_currency:
                price = await self._get_asset_price_usd(balance.asset)
                balance_value_usd = exchange_balance.total * price
            
            exchange_values[exchange_name] += balance_value_usd
    
    max_exchange_value = max(exchange_values.values()) if exchange_values else Decimal('0')
    self.risk_metrics['exchange_concentration'] = float(max_exchange_value / total_value * 100) if total_value > 0 else 0

# Portfolio Analysis Methods
async def get_portfolio_summary(self) -> Dict[str, Any]:
    """Get comprehensive portfolio summary"""
    await self.update_portfolio()
    
    total_value = await self._calculate_total_value_usd()
    
    # Asset breakdown
    asset_breakdown = []
    for asset, balance in self.current_balances.items():
        asset_value_usd = balance.total_balance
        if asset != self.reference_currency:
            price = await self._get_asset_price_usd(asset)
            asset_value_usd = balance.total_balance * price
        
        percentage = float(asset_value_usd / total_value * 100) if total_value > 0 else 0
        
        asset_breakdown.append({
            'asset': asset,
            'balance': float(balance.total_balance),
            'available': float(balance.available_balance),
            'locked': float(balance.locked_balance),
            'value_usd': float(asset_value_usd),
            'percentage': percentage,
            'exchanges': len(balance.exchange_balances),
            'concentration_risk': balance.concentration_risk
        })
    
    # Exchange breakdown
    exchange_breakdown = {}
    for balance in self.current_balances.values():
        for exchange_name, exchange_balance in balance.exchange_balances.items():
            if exchange_name not in exchange_breakdown:
                exchange_breakdown[exchange_name] = {
                    'total_value_usd': Decimal('0'),
                    'assets': 0,
                    'balances': []
                }
            
            balance_value_usd = exchange_balance.total
            if balance.asset != self.reference_currency:
                price = await self._get_asset_price_usd(balance.asset)
                balance_value_usd = exchange_balance.total * price
            
            exchange_breakdown[exchange_name]['total_value_usd'] += balance_value_usd
            exchange_breakdown[exchange_name]['assets'] += 1
            exchange_breakdown[exchange_name]['balances'].append({
                'asset': balance.asset,
                'balance': float(exchange_balance.total),
                'value_usd': float(balance_value_usd)
            })
    
    # Convert exchange breakdown to serializable format
    exchange_summary = {}
    for exchange_name, data in exchange_breakdown.items():
        percentage = float(data['total_value_usd'] / total_value * 100) if total_value > 0 else 0
        exchange_summary[exchange_name] = {
            'total_value_usd': float(data['total_value_usd']),
            'assets': data['assets'],
            'percentage': percentage,
            'balances': data['balances']
        }
    
    return {
        'summary': {
            'total_value_usd': float(total_value),
            'total_assets': len(self.current_balances),
            'total_exchanges': len(self.exchanges),
            'last_updated': self.last_update_time
        },
        'performance': {
            'total_pnl': float(self.total_profit_loss),
            'daily_pnl': float(self.daily_pnl),
            'max_portfolio_value': float(self.max_portfolio_value),
            'max_drawdown_percent': float(self.max_drawdown),
            'pnl_24h': float(await self._calculate_pnl_period(24)),
            'pnl_7d': float(await self._calculate_pnl_period(24 * 7)),
            'pnl_30d': float(await self._calculate_pnl_period(24 * 30))
        },
        'risk_metrics': self.risk_metrics,
        'asset_breakdown': sorted(asset_breakdown, key=lambda x: x['value_usd'], reverse=True),
        'exchange_breakdown': exchange_summary
    }

async def get_rebalancing_recommendations(self) -> List[Dict[str, Any]]:
    """Get portfolio rebalancing recommendations"""
    recommendations = []
    
    await self.update_portfolio()
    total_value = await self._calculate_total_value_usd()
    
    # Check for concentration risks
    for asset, balance in self.current_balances.items():
        asset_value_usd = balance.total_balance
        if asset != self.reference_currency:
            price = await self._get_asset_price_usd(asset)
            asset_value_usd = balance.total_balance * price
        
        concentration = float(asset_value_usd / total_value * 100) if total_value > 0 else 0
        
        # Recommend rebalancing if single asset > 50%
        if concentration > 50:
            recommendations.append({
                'type': 'REDUCE_CONCENTRATION',
                'asset': asset,
                'current_percentage': concentration,
                'recommended_percentage': 30.0,
                'action': f'Reduce {asset} position from {concentration:.1f}% to ~30%',
                'priority': 'HIGH'
            })
        
        # Check exchange concentration within asset
        if balance.concentration_risk > 80:
            recommendations.append({
                'type': 'DIVERSIFY_EXCHANGES',
                'asset': asset,
                'concentration_risk': balance.concentration_risk,
                'action': f'Distribute {asset} across more exchanges',
                'priority': 'MEDIUM'
            })
    
    # Check for exchange concentration risks
    exchange_values = {}
    for balance in self.current_balances.values():
        for exchange_name, exchange_balance in balance.exchange_balances.items():
            if exchange_name not in exchange_values:
                exchange_values[exchange_name] = Decimal('0')
            
            balance_value_usd = exchange_balance.total
            if balance.asset != self.reference_currency:
                price = await self._get_asset_price_usd(balance.asset)
                balance_value_usd = exchange_balance.total * price
            
            exchange_values[exchange_name] += balance_value_usd
    
    for exchange_name, exchange_value in exchange_values.items():
        concentration = float(exchange_value / total_value * 100) if total_value > 0 else 0
        
        if concentration > 60:
            recommendations.append({
                'type': 'REDUCE_EXCHANGE_CONCENTRATION',
                'exchange': exchange_name,
                'current_percentage': concentration,
                'recommended_percentage': 40.0,
                'action': f'Reduce exposure on {exchange_name} from {concentration:.1f}% to ~40%',
                'priority': 'HIGH'
            })
    
    return recommendations

async def get_asset_balance(self, asset: str, exchange: Optional[str] = None) -> Decimal:
    """Get balance for a specific asset, optionally from specific exchange"""
    await self.update_portfolio()
    
    if asset not in self.current_balances:
        return Decimal('0')
    
    if exchange:
        # Get balance from specific exchange
        exchange_balances = self.current_balances[asset].exchange_balances
        if exchange in exchange_balances:
            return exchange_balances[exchange].free
        return Decimal('0')
    else:
        # Get total available balance across all exchanges
        return self.current_balances[asset].available_balance

async def check_sufficient_balance(self, asset: str, required_amount: Decimal, 
                                 exchange: Optional[str] = None) -> bool:
    """Check if sufficient balance is available for a trade"""
    available = await self.get_asset_balance(asset, exchange)
    return available >= required_amount

async def get_optimal_exchange_for_asset(self, asset: str, 
                                       required_amount: Decimal) -> Optional[str]:
    """Get the exchange with the most suitable balance for a trade"""
    await self.update_portfolio()
    
    if asset not in self.current_balances:
        return None
    
    best_exchange = None
    best_score = 0
    
    for exchange_name, balance in self.current_balances[asset].exchange_balances.items():
        if balance.free >= required_amount:
            # Score based on available balance and exchange reliability
            # Higher balance = better score, but not the only factor
            score = float(balance.free) * 0.7  # 70% weight on balance
            
            # Add reliability score if available (from risk manager)
            # This would need to be passed in or accessed somehow
            score += 100 * 0.3  # 30% weight on reliability (placeholder)
            
            if score > best_score:
                best_score = score
                best_exchange = exchange_name
    
    return best_exchange

def get_portfolio_history(self, hours: int = 24) -> List[Dict[str, Any]]:
    """Get portfolio history for specified time period"""
    cutoff_time = time.time() - (hours * 3600)
    
    relevant_history = [
        {
            'timestamp': snapshot.timestamp,
            'total_value_usd': float(snapshot.total_value_usd),
            'asset_count': snapshot.asset_count,
            'pnl_24h': float(snapshot.pnl_24h),
            'datetime': datetime.fromtimestamp(snapshot.timestamp).isoformat()
        }
        for snapshot in self.portfolio_history
        if snapshot.timestamp >= cutoff_time
    ]
    
    return sorted(relevant_history, key=lambda x: x['timestamp'])

def reset_performance_tracking(self) -> None:
    """Reset performance tracking metrics"""
    self.total_profit_loss = Decimal('0')
    self.daily_pnl = Decimal('0')
    self.max_portfolio_value = Decimal('0')
    self.max_drawdown = Decimal('0')
    self.portfolio_history.clear()
    
    logger.info("portfolio_performance_tracking_reset")
```