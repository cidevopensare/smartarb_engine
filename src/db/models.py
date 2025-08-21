"""
Database Models for SmartArb Engine
SQLAlchemy models for data persistence
"""

from sqlalchemy import (
    Column, Integer, String, Decimal, DateTime, Boolean, 
    Text, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from decimal import Decimal as PyDecimal

Base = declarative_base()


class Exchange(Base):
    """Exchange information"""
    __tablename__ = 'exchanges'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100))
    api_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    opportunities_buy = relationship("Opportunity", foreign_keys="Opportunity.buy_exchange_id", back_populates="buy_exchange")
    opportunities_sell = relationship("Opportunity", foreign_keys="Opportunity.sell_exchange_id", back_populates="sell_exchange")
    orders = relationship("Order", back_populates="exchange")
    balances = relationship("Balance", back_populates="exchange")
    
    def __repr__(self):
        return f"<Exchange(name='{self.name}', active={self.is_active})>"


class TradingPair(Base):
    """Trading pair information"""
    __tablename__ = 'trading_pairs'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    base_asset = Column(String(10), nullable=False)
    quote_asset = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    min_trade_amount = Column(Decimal(20, 8), default=0)
    max_trade_amount = Column(Decimal(20, 8))
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    opportunities = relationship("Opportunity", back_populates="trading_pair")
    orders = relationship("Order", back_populates="trading_pair")
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('symbol', name='uq_trading_pair_symbol'),
        Index('idx_trading_pair_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<TradingPair(symbol='{self.symbol}', active={self.is_active})>"


class Opportunity(Base):
    """Arbitrage opportunities"""
    __tablename__ = 'opportunities'
    
    id = Column(Integer, primary_key=True)
    opportunity_id = Column(String(100), unique=True, nullable=False)
    strategy_name = Column(String(50), nullable=False)
    trading_pair_id = Column(Integer, ForeignKey('trading_pairs.id'), nullable=False)
    
    # Exchange information
    buy_exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    sell_exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    
    # Price and amount information
    buy_price = Column(Decimal(20, 8), nullable=False)
    sell_price = Column(Decimal(20, 8), nullable=False)
    amount = Column(Decimal(20, 8), nullable=False)
    
    # Profitability metrics
    spread_percentage = Column(Decimal(10, 4), nullable=False)
    expected_profit_percentage = Column(Decimal(10, 4), nullable=False)
    estimated_fees = Column(Decimal(10, 4), default=0)
    net_profit_percentage = Column(Decimal(10, 4))
    
    # Execution tracking
    status = Column(String(20), default='detected')  # detected, executing, completed, failed, expired
    confidence_score = Column(Decimal(3, 2))  # 0.00 to 1.00
    
    # Timestamps
    detected_at = Column(DateTime, default=func.now())
    executed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Execution results
    actual_profit = Column(Decimal(20, 8))
    actual_fees = Column(Decimal(20, 8))
    execution_time_ms = Column(Integer)
    
    # Relationships
    trading_pair = relationship("TradingPair", back_populates="opportunities")
    buy_exchange = relationship("Exchange", foreign_keys=[buy_exchange_id], back_populates="opportunities_buy")
    sell_exchange = relationship("Exchange", foreign_keys=[sell_exchange_id], back_populates="opportunities_sell")
    orders = relationship("Order", back_populates="opportunity")
    
    # Indexes
    __table_args__ = (
        Index('idx_opportunity_strategy', 'strategy_name'),
        Index('idx_opportunity_status', 'status'),
        Index('idx_opportunity_detected_at', 'detected_at'),
        Index('idx_opportunity_profit', 'expected_profit_percentage'),
    )
    
    def __repr__(self):
        return f"<Opportunity(id='{self.opportunity_id}', strategy='{self.strategy_name}', profit={self.expected_profit_percentage}%)>"


class Order(Base):
    """Order execution tracking"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), nullable=False)  # Exchange order ID
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'))
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    trading_pair_id = Column(Integer, ForeignKey('trading_pairs.id'), nullable=False)
    
    # Order details
    side = Column(String(10), nullable=False)  # buy, sell
    order_type = Column(String(10), default='limit')  # limit, market
    amount = Column(Decimal(20, 8), nullable=False)
    price = Column(Decimal(20, 8))
    
    # Execution tracking
    status = Column(String(20), default='pending')  # pending, filled, cancelled, failed, partially_filled
    filled_amount = Column(Decimal(20, 8), default=0)
    average_fill_price = Column(Decimal(20, 8))
    total_fee = Column(Decimal(20, 8), default=0)
    fee_currency = Column(String(10))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    filled_at = Column(DateTime)
    
    # Relationships
    opportunity = relationship("Opportunity", back_populates="orders")
    exchange = relationship("Exchange", back_populates="orders")
    trading_pair = relationship("TradingPair", back_populates="orders")
    trades = relationship("Trade", back_populates="order")
    
    # Indexes
    __table_args__ = (
        Index('idx_order_exchange_order_id', 'exchange_id', 'order_id'),
        Index('idx_order_status', 'status'),
        Index('idx_order_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Order(id='{self.order_id}', side='{self.side}', status='{self.status}')>"


class Trade(Base):
    """Individual trade executions (fills)"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(String(100), nullable=False)  # Exchange trade ID
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    
    # Trade details
    amount = Column(Decimal(20, 8), nullable=False)
    price = Column(Decimal(20, 8), nullable=False)
    fee = Column(Decimal(20, 8), default=0)
    fee_currency = Column(String(10))
    
    # Timestamp
    executed_at = Column(DateTime, default=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="trades")
    
    # Indexes
    __table_args__ = (
        Index('idx_trade_order_id', 'order_id'),
        Index('idx_trade_executed_at', 'executed_at'),
    )
    
    def __repr__(self):
        return f"<Trade(id='{self.trade_id}', amount={self.amount}, price={self.price})>"


class Balance(Base):
    """Account balances per exchange"""
    __tablename__ = 'balances'
    
    id = Column(Integer, primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    asset = Column(String(10), nullable=False)
    
    # Balance information
    free_balance = Column(Decimal(20, 8), nullable=False, default=0)
    locked_balance = Column(Decimal(20, 8), nullable=False, default=0)
    total_balance = Column(Decimal(20, 8), nullable=False, default=0)
    
    # Valuation
    usd_value = Column(Decimal(20, 8))
    last_price = Column(Decimal(20, 8))
    
    # Timestamp
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    exchange = relationship("Exchange", back_populates="balances")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('exchange_id', 'asset', name='uq_balance_exchange_asset'),
        Index('idx_balance_updated_at', 'updated_at'),
    )
    
    def __repr__(self):
        return f"<Balance(exchange_id={self.exchange_id}, asset='{self.asset}', total={self.total_balance})>"


class PerformanceMetric(Base):
    """Performance tracking metrics"""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String(50), nullable=False)
    metric_value = Column(Decimal(20, 8), nullable=False)
    metric_type = Column(String(20), default='counter')  # counter, gauge, histogram
    
    # Dimensions
    strategy_name = Column(String(50))
    exchange_name = Column(String(50))
    trading_pair = Column(String(20))
    
    # Timestamp
    recorded_at = Column(DateTime, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_performance_metric_name', 'metric_name'),
        Index('idx_performance_recorded_at', 'recorded_at'),
        Index('idx_performance_strategy', 'strategy_name'),
    )
    
    def __repr__(self):
        return f"<PerformanceMetric(name='{self.metric_name}', value={self.metric_value})>"


class SystemLog(Base):
    """System log entries for important events"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    level = Column(String(10), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    component = Column(String(50), nullable=False)
    event_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    
    # Additional context
    metadata = Column(Text)  # JSON string for additional data
    
    # Timestamp
    created_at = Column(DateTime, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_system_log_level', 'level'),
        Index('idx_system_log_component', 'component'),
        Index('idx_system_log_created_at', 'created_at'),
        Index('idx_system_log_event_type', 'event_type'),
    )
    
    def __repr__(self):
        return f"<SystemLog(level='{self.level}', component='{self.component}', event='{self.event_type}')>"


class Configuration(Base):
    """Runtime configuration storage"""
    __tablename__ = 'configurations'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), default='string')  # string, int, float, bool, json
    description = Column(Text)
    is_sensitive = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Configuration(key='{self.key}', type='{self.value_type}')>"


# Database initialization functions
def create_tables(engine):
    """Create all tables"""
    Base.metadata.create_all(engine)


def get_table_names():
    """Get list of all table names"""
    return [table.name for table in Base.metadata.tables.values()]


# Utility functions for common queries
class DatabaseUtils:
    """Utility functions for database operations"""
    
    @staticmethod
    def get_active_exchanges(session):
        """Get all active exchanges"""
        return session.query(Exchange).filter(Exchange.is_active == True).all()
    
    @staticmethod
    def get_recent_opportunities(session, hours=24, limit=100):
        """Get recent opportunities"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return session.query(Opportunity).filter(
            Opportunity.detected_at >= cutoff
        ).order_by(
            Opportunity.detected_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_profitable_opportunities(session, min_profit=0.1):
        """Get opportunities above minimum profit threshold"""
        return session.query(Opportunity).filter(
            Opportunity.expected_profit_percentage >= min_profit,
            Opportunity.status == 'completed',
            Opportunity.actual_profit > 0
        ).all()
    
    @staticmethod
    def get_exchange_performance(session, exchange_name):
        """Get performance metrics for specific exchange"""
        exchange = session.query(Exchange).filter(
            Exchange.name == exchange_name
        ).first()
        
        if not exchange:
            return None
        
        # Get successful opportunities
        successful_opportunities = session.query(Opportunity).filter(
            (Opportunity.buy_exchange_id == exchange.id) | 
            (Opportunity.sell_exchange_id == exchange.id),
            Opportunity.status == 'completed',
            Opportunity.actual_profit > 0
        ).all()
        
        return {
            'exchange_name': exchange_name,
            'successful_trades': len(successful_opportunities),
            'total_profit': sum(opp.actual_profit or 0 for opp in successful_opportunities)
        }
