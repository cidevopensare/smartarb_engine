#!/usr/bin/env python3
“””
Portfolio Manager for SmartArb Engine
Manages portfolio balances, exposure tracking, and capital allocation across exchanges
“””

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import structlog
import time
from datetime import datetime, timedelta
import json

from ..exchanges.base_exchange import BaseExchange, Balance

logger = structlog.get_logger(**name**)

class AssetType(Enum):
“”“Asset type enumeration”””
FIAT = “fiat”
CRYPTO = “crypto”
STABLECOIN = “stablecoin”

@dataclass
class AssetInfo:
“”“Asset information structure”””
symbol: str
name: str
asset_type: AssetType
decimals: int
is_tradeable: bool

@dataclass
class PortfolioAsset:
“”“Portfolio asset holding”””
symbol: str
total_balance: Decimal
available_balance: Decimal
locked_balance: Decimal
usd_value: Decimal
percentage: float
exchanges: Dict[str, Balance]  # Exchange name -> Balance
last_updated: float

```
@property
def total_exchange_balance(self) -> Decimal:
    """Calculate total balance across all exchanges"""
    return sum(balance.total for balance in self.exchanges.values())
```

@dataclass
class PortfolioSnapshot:
“”“Portfolio snapshot at a point in time”””
timestamp: float
total_value_usd: Decimal
assets: Dict[str, PortfolioAsset]
pnl_24h: Decimal
pnl_percentage_24h: float
exchange_breakdown: Dict[str, Decimal]

```
def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary"""
    return {
        'timestamp': self.timestamp,
        'total_value_usd': float(self.total_value_usd),
        'total_assets': len(self.assets),
        'pnl_24h': float(self.pnl_24h),
        'pnl_percentage_24h': self.pnl_percentage_24h,
        'exchange_breakdown': {k: float(v) for k, v in self.exchange_breakdown.items()},
        'top_assets': [
            {
                'symbol': asset.symbol,
                'value_usd': float(asset.usd_value),
                'percentage': asset.percentage
            }
            for asset in sorted(self.assets.values(), 
                              key=lambda x: x.usd_value, reverse=True)[:5]
        ]
    }
```

class PriceProvider:
“”“Simple price provider for asset valuation”””

```
def __init__(self):
    self.prices = {}
    self.last_update = 0
    self.update_interval = 60  # 1 minute
    
    # Static prices for stablecoins
    self.stable_prices = {
        'USDT': Decimal('1.0'),
        'USDC': Decimal('1.0'),
        'BUSD': Decimal('1.0'),
        'DAI': Decimal('1.0'),
        'FDUSD': Decimal('1.0')
    }
    
    self.logger = structlog.get_logger("portfolio.price_provider")

async def get_price(self, symbol: str, base: str = "USD") -> Decimal:
    """Get asset price in base currency"""
    
    # Handle stablecoins
    if symbol in self.stable_prices:
        return self.stable_prices[symbol]
    
    # Handle direct USD pairs
    if base == "USD":
        price_key = f"{symbol}/USD"
        if price_key in self.prices:
            return self.prices[price_key]
        
        # Try USDT as proxy for USD
        usdt_key = f"{symbol}/USDT"
        if usdt_key in self.prices:
            return self.prices[usdt_key]
    
    # Default fallback
    self.logger.warning("price_not_found", symbol=symbol, base=base)
    return Decimal('0')

async def update_prices(self, exchanges: Dict[str, BaseExchange]):
    """Update prices from exchanges"""
    current_time = time.time()
    
    if current_time - self.last_update < self.update_interval:
        return
    
    try:
        # Get prices from the first available exchange
        for exchange_name, exchange in exchanges.items():
            if not exchange.connected:
                continue
            
            try:
                # Common trading pairs for price discovery
                price_pairs = [
                    'BTC/USDT', 'ETH/USDT', 'BNB/USDT',
                    'ADA/USDT', 'DOT/USDT', 'LINK/USDT',
                    'MATIC/USDT', 'SOL/USDT', 'AVAX/USDT'
                ]
                
                for pair in price_pairs:
                    try:
                        ticker = await exchange.get_ticker(pair)
                        self.prices[pair] = ticker.last
                        
                    except Exception as e:
                        self.logger.debug("price_fetch_failed", 
                                        pair=pair, 
                                        exchange=exchange_name,
                                        error=str(e))
                
                # If we got some prices, break
                if self.prices:
                    break
                    
            except Exception as e:
                self.logger.warning("exchange_price_update_failed",
                                  exchange=exchange_name,
                                  error=str(e))
        
        self.last_update = current_time
        self.logger.debug("prices_updated", count=len(self.prices))
        
    except Exception as e:
        self.logger.error("price_update_failed", error=str(e))
```

class PortfolioManager:
“”“Main portfolio management system”””

```
def __init__(self, exchanges: Dict[str, BaseExchange], config: Dict[str, Any]):
    self.exchanges = exchanges
    self.config = config
    self.portfolio_config = config.get('portfolio', {})
    
    # Price provider
    self.price_provider = PriceProvider()
    
    # Portfolio tracking
    self.current_portfolio = None
    self.portfolio_history = []
    self.max_history_size = 1000
    
    # Asset management
    self.tracked_assets = set()
    self.asset_info = {}
    self._initialize_asset_info()
    
    # Rebalancing
    self.target_allocation = self.portfolio_config.get('target_allocation', {})
    self.rebalance_threshold = Decimal(str(self.portfolio_config.get('rebalance_threshold', 0.05)))
    
    # Performance tracking
    self.daily_snapshots = []
    self.performance_metrics = {}
    
    # Update intervals
    self.update_interval = self.portfolio_config.get('update_interval_seconds', 30)
    self.last_update = 0
    
    self.logger = structlog.get_logger("portfolio_manager")

def _initialize_asset_info(self):
    """Initialize asset information"""
    
    # Common cryptocurrencies
    crypto_assets = {
        'BTC': AssetInfo('BTC', 'Bitcoin', AssetType.CRYPTO, 8, True),
        'ETH': AssetInfo('ETH', 'Ethereum', AssetType.CRYPTO, 18, True),
        'BNB': AssetInfo('BNB', 'Binance Coin', AssetType.CRYPTO, 18, True),
        'ADA': AssetInfo('ADA', 'Cardano', AssetType.CRYPTO, 6, True),
        'DOT': AssetInfo('DOT', 'Polkadot', AssetType.CRYPTO, 10, True),
        'LINK': AssetInfo('LINK', 'Chainlink', AssetType.CRYPTO, 18, True),
        'MATIC': AssetInfo('MATIC', 'Polygon', AssetType.CRYPTO, 18, True),
        'SOL': AssetInfo('SOL', 'Solana', AssetType.CRYPTO, 9, True),
        'AVAX': AssetInfo('AVAX', 'Avalanche', AssetType.CRYPTO, 18, True),
    }
    
    # Stablecoins
    stablecoin_assets = {
        'USDT': AssetInfo('USDT', 'Tether', AssetType.STABLECOIN, 6, True),
        'USDC': AssetInfo('USDC', 'USD Coin', AssetType.STABLECOIN, 6, True),
        'BUSD': AssetInfo('BUSD', 'Binance USD', AssetType.STABLECOIN, 18, True),
        'DAI': AssetInfo('DAI', 'Dai', AssetType.STABLECOIN, 18, True),
        'FDUSD': AssetInfo('FDUSD', 'First Digital USD', AssetType.STABLECOIN, 18, True),
    }
    
    # Fiat currencies
    fiat_assets = {
        'USD': AssetInfo('USD', 'US Dollar', AssetType.FIAT, 2, False),
        'EUR': AssetInfo('EUR', 'Euro', AssetType.FIAT, 2, False),
    }
    
    self.asset_info = {**crypto_assets, **stablecoin_assets, **fiat_assets}
    
    # Track all assets by default
    self.tracked_assets = set(self.asset_info.keys())

async def update_portfolio(self) -> PortfolioSnapshot:
    """Update and return current portfolio snapshot"""
    
    current_time = time.time()
    
    # Check if update is needed
    if (self.current_portfolio and 
        current_time - self.last_update < self.update_interval):
        return self.current_portfolio
    
    try:
        # Update prices first
        await self.price_provider.update_prices(self.exchanges)
        
        # Collect balances from all exchanges
        all_balances = await self._collect_all_balances()
        
        # Aggregate balances by asset
        portfolio_assets = await self._aggregate_asset_balances(all_balances)
        
        # Calculate USD values
        total_value_usd = Decimal('0')
        for asset in portfolio_assets.values():
            asset.usd_value = await self._calculate_asset_value(asset)
            total_value_usd += asset.usd_value
        
        # Calculate percentages
        for asset in portfolio_assets.values():
            if total_value_usd > 0:
                asset.percentage = float(asset.usd_value / total_value_usd * 100)
            else:
                asset.percentage = 0.0
        
        # Calculate exchange breakdown
        exchange_breakdown = await self._calculate_exchange_breakdown(all_balances)
        
        # Calculate 24h PnL
        pnl_24h, pnl_percentage_24h = self._calculate_24h_pnl(total_value_usd)
        
        # Create portfolio snapshot
        portfolio_snapshot = PortfolioSnapshot(
            timestamp=current_time,
            total_value_usd=total_value_usd,
            assets=portfolio_assets,
            pnl_24h=pnl_24h,
            pnl_percentage_24h=pnl_percentage_24h,
            exchange_breakdown=exchange_breakdown
        )
        
        # Update tracking
        self.current_portfolio = portfolio_snapshot
        self.last_update = current_time
        
        # Add to history
        self._add_to_history(portfolio_snapshot)
        
        self.logger.info("portfolio_updated",
                       total_value=float(total_value_usd),
                       asset_count=len(portfolio_assets),
                       pnl_24h=float(pnl_24h),
                       pnl_percentage=pnl_percentage_24h)
        
        return portfolio_snapshot
        
    except Exception as e:
        self.logger.error("portfolio_update_failed", error=str(e))
        
        # Return last known portfolio or empty one
        if self.current_portfolio:
            return self.current_portfolio
        else:
            return PortfolioSnapshot(
                timestamp=current_time,
                total_value_usd=Decimal('0'),
                assets={},
                pnl_24h=Decimal('0'),
                pnl_percentage_24h=0.0,
                exchange_breakdown={}
            )

async def _collect_all_balances(self) -> Dict[str, Dict[str, Balance]]:
    """Collect balances from all exchanges"""
    all_balances = {}
    
    for exchange_name, exchange in self.exchanges.items():
        if not exchange.connected:
            continue
        
        try:
            balances = await exchange.get_balance()
            
            # Filter out zero balances and non-tracked assets
            filtered_balances = {}
            for asset, balance in balances.items():
                if (balance.total > 0 and asset in self.tracked_assets):
                    filtered_balances[asset] = balance
            
            all_balances[exchange_name] = filtered_balances
            
            self.logger.debug("balances_collected",
                            exchange=exchange_name,
                            asset_count=len(filtered_balances))
            
        except Exception as e:
            self.logger.warning("balance_collection_failed",
                              exchange=exchange_name,
                              error=str(e))
            all_balances[exchange_name] = {}
    
    return all_balances

async def _aggregate_asset_balances(self, all_balances: Dict[str, Dict[str, Balance]]) -> Dict[str, PortfolioAsset]:
    """Aggregate balances by asset across exchanges"""
    
    aggregated = {}
    
    # Get all unique assets
    all_assets = set()
    for exchange_balances in all_balances.values():
        all_assets.update(exchange_balances.keys())
    
    # Aggregate each asset
    for asset in all_assets:
        total_balance = Decimal('0')
        available_balance = Decimal('0')
        locked_balance = Decimal('0')
        exchanges = {}
        
        for exchange_name, exchange_balances in all_balances.items():
            if asset in exchange_balances:
                balance = exchange_balances[asset]
                total_balance += balance.total
                available_balance += balance.free
                locked_balance += balance.locked
                exchanges[exchange_name] = balance
        
        if total_balance > 0:
            aggregated[asset] = PortfolioAsset(
                symbol=asset,
                total_balance=total_balance,
                available_balance=available_balance,
                locked_balance=locked_balance,
                usd_value=Decimal('0'),  # Will be calculated later
                percentage=0.0,  # Will be calculated later
                exchanges=exchanges,
                last_updated=time.time()
            )
    
    return aggregated

async def _calculate_asset_value(self, asset: PortfolioAsset) -> Decimal:
    """Calculate USD value of asset"""
    
    if asset.total_balance == 0:
        return Decimal('0')
    
    # Get asset price in USD
    price_usd = await self.price_provider.get_price(asset.symbol, "USD")
    
    if price_usd == 0:
        self.logger.warning("asset_price_unavailable", asset=asset.symbol)
        return Decimal('0')
    
    return asset.total_balance * price_usd

async def _calculate_exchange_breakdown(self, all_balances: Dict[str, Dict[str, Balance]]) -> Dict[str, Decimal]:
    """Calculate portfolio value breakdown by exchange"""
    
    breakdown = {}
    
    for exchange_name, exchange_balances in all_balances.items():
        exchange_value = Decimal('0')
        
        for asset, balance in exchange_balances.items():
            if balance.total > 0:
                price_usd = await self.price_provider.get_price(asset, "USD")
                asset_value = balance.total * price_usd
                exchange_value += asset_value
        
        breakdown[exchange_name] = exchange_value
    
    return breakdown

def _calculate_24h_pnl(self, current_value: Decimal) -> Tuple[Decimal, float]:
    """Calculate 24-hour profit/loss"""
    
    # Find snapshot from 24 hours ago
    cutoff_time = time.time() - (24 * 60 * 60)
    
    baseline_value = None
    for snapshot in reversed(self.portfolio_history):
        if snapshot.timestamp <= cutoff_time:
            baseline_value = snapshot.total_value_usd
            break
    
    if baseline_value is None or baseline_value == 0:
        return Decimal('0'), 0.0
    
    pnl_24h = current_value - baseline_value
    pnl_percentage_24h = float(pnl_24h / baseline_value * 100)
    
    return pnl_24h, pnl_percentage_24h

def _add_to_history(self, snapshot: PortfolioSnapshot):
    """Add snapshot to history with size management"""
    
    self.portfolio_history.append(snapshot)
    
    # Manage history size
    if len(self.portfolio_history) > self.max_history_size:
        # Keep recent snapshots and some older ones for long-term tracking
        recent_snapshots = self.portfolio_history[-int(self.max_history_size * 0.8):]
        
        # Keep every 10th older snapshot
        older_snapshots = self.portfolio_history[:-int(self.max_history_size * 0.8)]
        sampled_older = [older_snapshots[i] for i in range(0, len(older_snapshots), 10)]
        
        self.portfolio_history = sampled_older + recent_snapshots

async def get_asset_allocation(self) -> Dict[str, float]:
    """Get current asset allocation percentages"""
    
    if not self.current_portfolio:
        await self.update_portfolio()
    
    allocation = {}
    for asset_symbol, asset in self.current_portfolio.assets.items():
        allocation[asset_symbol] = asset.percentage
    
    return allocation

async def get_exchange_allocation(self) -> Dict[str, float]:
    """Get current exchange allocation percentages"""
    
    if not self.current_portfolio:
        await self.update_portfolio()
    
    total_value = self.current_portfolio.total_value_usd
    
    if total_value == 0:
        return {}
    
    allocation = {}
    for exchange_name, exchange_value in self.current_portfolio.exchange_breakdown.items():
        allocation[exchange_name] = float(exchange_value / total_value * 100)
    
    return allocation

async def check_rebalancing_needed(self) -> Dict[str, Any]:
    """Check if portfolio rebalancing is needed"""
    
    current_allocation = await self.get_asset_allocation()
    
    rebalancing_actions = []
    
    for asset, target_percentage in self.target_allocation.items():
        current_percentage = current_allocation.get(asset, 0.0)
        deviation = abs(current_percentage - target_percentage)
        
        if deviation > float(self.rebalance_threshold) * 100:
            rebalancing_actions.append({
                'asset': asset,
                'current_percentage': current_percentage,
                'target_percentage': target_percentage,
                'deviation': deviation,
                'action': 'buy' if current_percentage < target_percentage else 'sell'
            })
    
    needs_rebalancing = len(rebalancing_actions) > 0
    
    return {
        'needs_rebalancing': needs_rebalancing,
        'actions': rebalancing_actions,
        'current_allocation': current_allocation,
        'target_allocation': self.target_allocation
    }

def get_portfolio_summary(self) -> Dict[str, Any]:
    """Get portfolio summary"""
    
    if not self.current_portfolio:
        return {'error': 'Portfolio not initialized'}
    
    summary = self.current_portfolio.to_dict()
    
    # Add additional metrics
    summary.update({
        'last_updated': self.last_update,
        'tracked_assets': len(self.tracked_assets),
        'connected_exchanges': len([ex for ex in self.exchanges.values() if ex.connected]),
        'history_size': len(self.portfolio_history)
    })
    
    return summary

def get_asset_details(self, asset_symbol: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific asset"""
    
    if not self.current_portfolio or asset_symbol not in self.current_portfolio.assets:
        return None
    
    asset = self.current_portfolio.assets[asset_symbol]
    asset_info = self.asset_info.get(asset_symbol)
    
    return {
        'symbol': asset.symbol,
        'total_balance': float(asset.total_balance),
        'available_balance': float(asset.available_balance),
        'locked_balance': float(asset.locked_balance),
        'usd_value': float(asset.usd_value),
        'percentage': asset.percentage,
        'asset_type': asset_info.asset_type.value if asset_info else 'unknown',
        'exchanges': {
            exchange_name: {
                'total': float(balance.total),
                'free': float(balance.free),
                'locked': float(balance.locked)
            }
            for exchange_name, balance in asset.exchanges.items()
        },
        'last_updated': asset.last_updated
    }
```