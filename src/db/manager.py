“””
Database Manager for SmartArb Engine
Handles database connections, operations, and data access layer
“””

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any, Type, Union
from datetime import datetime, timedelta
from decimal import Decimal
import structlog

from sqlalchemy import create_engine, text, and_, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from .models import (
Base, Exchange, TradingPair, Strategy, Opportunity, Execution,
Order, Balance, MarketData, PerformanceMetric, SystemLog,
RiskAssessment, AIAnalysis, CodeUpdate
)

logger = structlog.get_logger(**name**)

class DatabaseManager:
“””
Advanced Database Manager

```
Features:
- Async and sync support
- Connection pooling
- Transaction management
- Error handling
- Performance optimization
- Data access layer
"""

def __init__(self, config: Dict[str, Any]):
    self.config = config
    self.db_config = config.get('database', {}).get('postgresql', {})
    
    # Connection settings
    self.host = self.db_config.get('host', 'localhost')
    self.port = self.db_config.get('port', 5432)
    self.database = self.db_config.get('database', 'smartarb')
    self.username = self.db_config.get('username', 'smartarb_user')
    self.password = self.db_config.get('password', '')
    
    # Pool settings optimized for Raspberry Pi
    self.min_connections = self.db_config.get('min_connections', 2)
    self.max_connections = self.db_config.get('max_connections', 8)
    self.connection_timeout = self.db_config.get('connection_timeout', 30)
    self.query_timeout = self.db_config.get('query_timeout', 10)
    
    # Connection URLs
    self.sync_url = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    self.async_url = f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    # Engines
    self.sync_engine = None
    self.async_engine = None
    self.sync_session_factory = None
    self.async_session_factory = None
    
    # Status
    self.is_connected = False
    
    logger.info("database_manager_initialized",
               host=self.host,
               database=self.database,
               max_connections=self.max_connections)

async def initialize(self) -> bool:
    """Initialize database connections"""
    try:
        # Create sync engine
        self.sync_engine = create_engine(
            self.sync_url,
            poolclass=QueuePool,
            pool_size=self.min_connections,
            max_overflow=self.max_connections - self.min_connections,
            pool_timeout=self.connection_timeout,
            pool_recycle=3600,  # Recycle connections every hour
            echo=self.config.get('debug', False)
        )
        
        # Create async engine
        self.async_engine = create_async_engine(
            self.async_url,
            pool_size=self.min_connections,
            max_overflow=self.max_connections - self.min_connections,
            pool_timeout=self.connection_timeout,
            pool_recycle=3600,
            echo=self.config.get('debug', False)
        )
        
        # Create session factories
        self.sync_session_factory = sessionmaker(
            bind=self.sync_engine,
            expire_on_commit=False
        )
        
        self.async_session_factory = async_sessionmaker(
            bind=self.async_engine,
            expire_on_commit=False
        )
        
        # Test connections
        await self._test_connections()
        
        self.is_connected = True
        logger.info("database_connections_initialized")
        return True
        
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        return False

async def _test_connections(self):
    """Test database connections"""
    # Test sync connection
    with self.sync_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    # Test async connection
    async with self.async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    logger.info("database_connections_tested")

async def create_tables(self):
    """Create all database tables"""
    try:
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("database_tables_created")
        return True
        
    except Exception as e:
        logger.error("table_creation_failed", error=str(e))
        return False

async def drop_tables(self):
    """Drop all database tables (use with caution!)"""
    try:
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("database_tables_dropped")
        return True
        
    except Exception as e:
        logger.error("table_drop_failed", error=str(e))
        return False

@asynccontextmanager
async def get_async_session(self):
    """Get async database session with context manager"""
    session = self.async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("database_session_error", error=str(e))
        raise
    finally:
        await session.close()

@asynccontextmanager
def get_sync_session(self):
    """Get sync database session with context manager"""
    session = self.sync_session_factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("database_session_error", error=str(e))
        raise
    finally:
        session.close()

# Exchange operations
async def get_exchanges(self, enabled_only: bool = False) -> List[Exchange]:
    """Get all exchanges"""
    async with self.get_async_session() as session:
        query = session.query(Exchange)
        if enabled_only:
            query = query.filter(Exchange.is_enabled == True)
        
        result = await query.all()
        return result

async def get_exchange_by_name(self, name: str) -> Optional[Exchange]:
    """Get exchange by name"""
    async with self.get_async_session() as session:
        result = await session.query(Exchange).filter(Exchange.name == name).first()
        return result

async def update_exchange_health(self, exchange_name: str, health_data: Dict[str, Any]):
    """Update exchange health metrics"""
    async with self.get_async_session() as session:
        exchange = await session.query(Exchange).filter(Exchange.name == exchange_name).first()
        if exchange:
            for key, value in health_data.items():
                if hasattr(exchange, key):
                    setattr(exchange, key, value)
            
            await session.commit()
            logger.debug("exchange_health_updated", exchange=exchange_name)

# Trading pair operations
async def get_trading_pairs(self, enabled_only: bool = True) -> List[TradingPair]:
    """Get trading pairs"""
    async with self.get_async_session() as session:
        query = session.query(TradingPair)
        if enabled_only:
            query = query.filter(TradingPair.is_enabled == True)
        
        result = await query.all()
        return result

async def get_trading_pair_by_symbol(self, symbol: str) -> Optional[TradingPair]:
    """Get trading pair by symbol"""
    async with self.get_async_session() as session:
        result = await session.query(TradingPair).filter(TradingPair.symbol == symbol).first()
        return result

# Strategy operations
async def get_strategies(self, enabled_only: bool = True) -> List[Strategy]:
    """Get strategies"""
    async with self.get_async_session() as session:
        query = session.query(Strategy)
        if enabled_only:
            query = query.filter(Strategy.is_enabled == True)
        
        result = await query.order_by(Strategy.priority).all()
        return result

async def update_strategy_metrics(self, strategy_name: str, metrics: Dict[str, Any]):
    """Update strategy performance metrics"""
    async with self.get_async_session() as session:
        strategy = await session.query(Strategy).filter(Strategy.name == strategy_name).first()
        if strategy:
            for key, value in metrics.items():
                if hasattr(strategy, key):
                    setattr(strategy, key, value)
            
            await session.commit()
            logger.debug("strategy_metrics_updated", strategy=strategy_name)

# Opportunity operations
async def save_opportunity(self, opportunity_data: Dict[str, Any]) -> Opportunity:
    """Save new opportunity"""
    async with self.get_async_session() as session:
        # Get strategy and trading pair
        strategy = await session.query(Strategy).filter(
            Strategy.name == opportunity_data.get('strategy_name')
        ).first()
        
        trading_pair = await session.query(TradingPair).filter(
            TradingPair.symbol == opportunity_data.get('symbol')
        ).first()
        
        if not strategy or not trading_pair:
            raise ValueError("Strategy or trading pair not found")
        
        opportunity = Opportunity(
            opportunity_id=opportunity_data['opportunity_id'],
            strategy_id=strategy.id,
            trading_pair_id=trading_pair.id,
            opportunity_type=opportunity_data.get('opportunity_type', 'spatial_arbitrage'),
            amount=Decimal(str(opportunity_data['amount'])),
            expected_profit=Decimal(str(opportunity_data['expected_profit'])),
            expected_profit_percent=Decimal(str(opportunity_data['expected_profit_percent'])),
            risk_score=opportunity_data.get('risk_score', 0),
            confidence_level=opportunity_data.get('confidence_level', 0),
            buy_exchange=opportunity_data.get('buy_exchange'),
            sell_exchange=opportunity_data.get('sell_exchange'),
            buy_price=Decimal(str(opportunity_data.get('buy_price', 0))),
            sell_price=Decimal(str(opportunity_data.get('sell_price', 0))),
            spread_percent=Decimal(str(opportunity_data.get('spread_percent', 0))),
            metadata=opportunity_data.get('metadata', {})
        )
        
        session.add(opportunity)
        await session.commit()
        await session.refresh(opportunity)
        
        logger.info("opportunity_saved", opportunity_id=opportunity.opportunity_id)
        return opportunity

async def update_opportunity_status(self, opportunity_id: str, status: str, **kwargs):
    """Update opportunity status and related fields"""
    async with self.get_async_session() as session:
        opportunity = await session.query(Opportunity).filter(
            Opportunity.opportunity_id == opportunity_id
        ).first()
        
        if opportunity:
            opportunity.status = status
            
            # Update timestamps based on status
            if status == 'validated':
                opportunity.validated_at = datetime.utcnow()
            elif status == 'executed':
                opportunity.executed_at = datetime.utcnow()
            elif status == 'expired':
                opportunity.expired_at = datetime.utcnow()
            
            # Update additional fields
            for key, value in kwargs.items():
                if hasattr(opportunity, key):
                    setattr(opportunity, key, value)
            
            await session.commit()
            logger.debug("opportunity_status_updated", 
                       opportunity_id=opportunity_id, status=status)

# Execution operations
async def save_execution(self, execution_data: Dict[str, Any]) -> Execution:
    """Save execution record"""
    async with self.get_async_session() as session:
        # Get opportunity
        opportunity = await session.query(Opportunity).filter(
            Opportunity.opportunity_id == execution_data.get('opportunity_id')
        ).first()
        
        if not opportunity:
            raise ValueError("Opportunity not found")
        
        execution = Execution(
            execution_id=execution_data['execution_id'],
            opportunity_id=opportunity.id,
            status=execution_data.get('status', 'pending'),
            execution_type=execution_data.get('execution_type', 'market'),
            actual_profit=Decimal(str(execution_data.get('actual_profit', 0))),
            fees_paid=Decimal(str(execution_data.get('fees_paid', 0))),
            slippage=Decimal(str(execution_data.get('slippage', 0))),
            started_at=execution_data.get('started_at'),
            completed_at=execution_data.get('completed_at'),
            execution_time=execution_data.get('execution_time'),
            error_message=execution_data.get('error_message'),
            execution_data=execution_data.get('execution_data', {})
        )
        
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        
        logger.info("execution_saved", execution_id=execution.execution_id)
        return execution

# Balance operations
async def save_balance_snapshot(self, exchange_name: str, balances: Dict[str, Any]):
    """Save balance snapshot for an exchange"""
    async with self.get_async_session() as session:
        exchange = await session.query(Exchange).filter(Exchange.name == exchange_name).first()
        if not exchange:
            raise ValueError(f"Exchange {exchange_name} not found")
        
        snapshot_time = datetime.utcnow()
        
        for asset, balance_data in balances.items():
            balance = Balance(
                exchange_id=exchange.id,
                asset=asset,
                total_balance=Decimal(str(balance_data.get('total', 0))),
                available_balance=Decimal(str(balance_data.get('free', 0))),
                locked_balance=Decimal(str(balance_data.get('locked', 0))),
                usd_value=Decimal(str(balance_data.get('usd_value', 0))),
                snapshot_at=snapshot_time
            )
            session.add(balance)
        
        await session.commit()
        logger.debug("balance_snapshot_saved", exchange=exchange_name, assets=len(balances))

async def get_latest_balances(self, exchange_name: Optional[str] = None) -> List[Balance]:
    """Get latest balance snapshots"""
    async with self.get_async_session() as session:
        query = session.query(Balance)
        
        if exchange_name:
            query = query.join(Exchange).filter(Exchange.name == exchange_name)
        
        # Get latest snapshot for each exchange-asset combination
        subquery = session.query(
            Balance.exchange_id,
            Balance.asset,
            func.max(Balance.snapshot_at).label('latest_snapshot')
        ).group_by(Balance.exchange_id, Balance.asset).subquery()
        
        query = query.join(
            subquery,
            and_(
                Balance.exchange_id == subquery.c.exchange_id,
                Balance.asset == subquery.c.asset,
                Balance.snapshot_at == subquery.c.latest_snapshot
            )
        )
        
        result = await query.all()
        return result

# Market data operations
async def save_market_data(self, exchange_name: str, symbol: str, market_data: Dict[str, Any]):
    """Save market data snapshot"""
    async with self.get_async_session() as session:
        exchange = await session.query(Exchange).filter(Exchange.name == exchange_name).first()
        trading_pair = await session.query(TradingPair).filter(TradingPair.symbol == symbol).first()
        
        if not exchange or not trading_pair:
            raise ValueError("Exchange or trading pair not found")
        
        data = MarketData(
            exchange_id=exchange.id,
            trading_pair_id=trading_pair.id,
            bid=Decimal(str(market_data['bid'])),
            ask=Decimal(str(market_data['ask'])),
            last=Decimal(str(market_data['last'])),
            volume_24h=Decimal(str(market_data.get('volume_24h', 0))),
            bid_depth=Decimal(str(market_data.get('bid_depth', 0))),
            ask_depth=Decimal(str(market_data.get('ask_depth', 0))),
            spread=Decimal(str(market_data.get('spread', 0))),
            spread_percent=Decimal(str(market_data.get('spread_percent', 0))),
            exchange_timestamp=market_data.get('timestamp'),
            orderbook_data=market_data.get('orderbook_data', {})
        )
        
        session.add(data)
        await session.commit()

# Performance metrics
async def save_performance_metric(self, metric_type: str, metric_name: str, 
                                value: Union[int, float, Decimal], 
                                period_start: Optional[datetime] = None,
                                period_end: Optional[datetime] = None,
                                metadata: Optional[Dict[str, Any]] = None):
    """Save performance metric"""
    async with self.get_async_session() as session:
        metric = PerformanceMetric(
            metric_type=metric_type,
            metric_name=metric_name,
            value=Decimal(str(value)),
            period_start=period_start,
            period_end=period_end,
            metadata=metadata or {}
        )
        
        session.add(metric)
        await session.commit()

async def get_performance_metrics(self, metric_type: Optional[str] = None,
                                days_back: int = 7) -> List[PerformanceMetric]:
    """Get performance metrics"""
    async with self.get_async_session() as session:
        query = session.query(PerformanceMetric)
        
        if metric_type:
            query = query.filter(PerformanceMetric.metric_type == metric_type)
        
        # Filter by date range
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        query = query.filter(PerformanceMetric.created_at >= cutoff_date)
        
        result = await query.order_by(PerformanceMetric.created_at.desc()).all()
        return result

# System logs
async def save_system_log(self, level: str, logger_name: str, message: str,
                        module: Optional[str] = None, function: Optional[str] = None,
                        line_number: Optional[int] = None, extra_data: Optional[Dict] = None):
    """Save system log entry"""
    async with self.get_async_session() as session:
        log_entry = SystemLog(
            level=level,
            logger_name=logger_name,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            extra_data=extra_data or {}
        )
        
        session.add(log_entry)
        await session.commit()

# Analytics and reporting
async def get_trading_summary(self, days_back: int = 7) -> Dict[str, Any]:
    """Get trading summary statistics"""
    async with self.get_async_session() as session:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Opportunities
        opportunities_query = session.query(Opportunity).filter(
            Opportunity.created_at >= cutoff_date
        )
        total_opportunities = await opportunities_query.count()
        executed_opportunities = await opportunities_query.filter(
            Opportunity.status == 'executed'
        ).count()
        
        # Executions
        executions_query = session.query(Execution).filter(
            Execution.created_at >= cutoff_date
        )
        total_executions = await executions_query.count()
        successful_executions = await executions_query.filter(
            Execution.status == 'completed'
        ).count()
        
        # Profit calculation
        profit_result = await session.query(
            func.sum(Execution.actual_profit).label('total_profit'),
            func.avg(Execution.actual_profit).label('avg_profit')
        ).filter(
            and_(
                Execution.created_at >= cutoff_date,
                Execution.status == 'completed'
            )
        ).first()
        
        return {
            'period_days': days_back,
            'total_opportunities': total_opportunities,
            'executed_opportunities': executed_opportunities,
            'opportunity_success_rate': (executed_opportunities / total_opportunities * 100) if total_opportunities > 0 else 0,
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'execution_success_rate': (successful_executions / total_executions * 100) if total_executions > 0 else 0,
            'total_profit': float(profit_result.total_profit or 0),
            'average_profit': float(profit_result.avg_profit or 0)
        }

async def cleanup_old_data(self, days_to_keep: int = 30):
    """Clean up old data to free space"""
    async with self.get_async_session() as session:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Clean up old market data (keep less)
        market_data_cutoff = datetime.utcnow() - timedelta(days=7)
        await session.query(MarketData).filter(
            MarketData.created_at < market_data_cutoff
        ).delete()
        
        # Clean up old balance snapshots (keep less)
        balance_cutoff = datetime.utcnow() - timedelta(days=14)
        await session.query(Balance).filter(
            Balance.created_at < balance_cutoff
        ).delete()
        
        # Clean up old system logs
        await session.query(SystemLog).filter(
            SystemLog.created_at < cutoff_date
        ).delete()
        
        # Clean up old performance metrics
        await session.query(PerformanceMetric).filter(
            PerformanceMetric.created_at < cutoff_date
        ).delete()
        
        await session.commit()
        logger.info("old_data_cleaned", cutoff_date=cutoff_date)

async def get_database_stats(self) -> Dict[str, Any]:
    """Get database statistics"""
    try:
        async with self.get_async_session() as session:
            # Table row counts
            tables = {
                'exchanges': Exchange,
                'trading_pairs': TradingPair,
                'strategies': Strategy,
                'opportunities': Opportunity,
                'executions': Execution,
                'orders': Order,
                'balances': Balance,
                'market_data': MarketData,
                'performance_metrics': PerformanceMetric,
                'system_logs': SystemLog
            }
            
            stats = {}
            for table_name, model in tables.items():
                count = await session.query(model).count()
                stats[f"{table_name}_count"] = count
            
            # Database size (PostgreSQL specific)
            size_result = await session.execute(text(
                f"SELECT pg_size_pretty(pg_database_size('{self.database}'))"
            ))
            stats['database_size'] = size_result.scalar()
            
            return stats
            
    except Exception as e:
        logger.error("database_stats_error", error=str(e))
        return {'error': str(e)}

async def shutdown(self):
    """Shutdown database connections"""
    try:
        if self.async_engine:
            await self.async_engine.dispose()
        
        if self.sync_engine:
            self.sync_engine.dispose()
        
        self.is_connected = False
        logger.info("database_connections_closed")
        
    except Exception as e:
        logger.error("database_shutdown_error", error=str(e))
```