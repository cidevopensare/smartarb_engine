“””
Database Models for SmartArb Engine
SQLAlchemy models for storing trading data, performance metrics, and system logs
“””

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy import (
Column, Integer, String, DateTime, Numeric, Boolean,
Text, JSON, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import structlog

logger = structlog.get_logger(**name**)

Base = declarative_base()

class TimestampMixin:
“”“Mixin for timestamp fields”””
created_at = Column(DateTime, default=func.now(), nullable=False)
updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class Exchange(Base, TimestampMixin):
“”“Exchange configuration and status”””
**tablename** = ‘exchanges’

```
id = Column(Integer, primary_key=True)
name = Column(String(50), unique=True, nullable=False)
display_name = Column(String(100), nullable=False)
is_enabled = Column(Boolean, default=True, nullable=False)
is_connected = Column(Boolean, default=False, nullable=False)

# Configuration
base_url = Column(String(255), nullable=False)
api_version = Column(String(20))
rate_limit = Column(Integer, default=100)  # requests per minute
timeout = Column(Integer, default=30)  # seconds

# Fees
maker_fee = Column(Numeric(10, 6), default=0.001)
taker_fee = Column(Numeric(10, 6), default=0.001)

# Health metrics
last_ping_ms = Column(Integer)
error_count = Column(Integer, default=0)
consecutive_errors = Column(Integer, default=0)
reliability_score = Column(Numeric(3, 2), default=1.0)
last_error_at = Column(DateTime)

# Relationships
balances = relationship("Balance", back_populates="exchange")
orders = relationship("Order", back_populates="exchange")
market_data = relationship("MarketData", back_populates="exchange")

def __repr__(self):
    return f"<Exchange(name='{self.name}', enabled={self.is_enabled})>"
```

class TradingPair(Base, TimestampMixin):
“”“Trading pair configuration”””
**tablename** = ‘trading_pairs’

```
id = Column(Integer, primary_key=True)
symbol = Column(String(20), nullable=False)  # BTC/USDT
base_asset = Column(String(10), nullable=False)  # BTC
quote_asset = Column(String(10), nullable=False)  # USDT
is_enabled = Column(Boolean, default=True)

# Configuration
min_trade_amount = Column(Numeric(20, 8), default=10)
max_trade_amount = Column(Numeric(20, 8), default=10000)
price_precision = Column(Integer, default=8)
amount_precision = Column(Integer, default=8)

# Risk parameters
max_position_size = Column(Numeric(20, 8))
min_spread_percent = Column(Numeric(5, 4), default=0.002)

# Relationships
opportunities = relationship("Opportunity", back_populates="trading_pair")
market_data = relationship("MarketData", back_populates="trading_pair")

__table_args__ = (
    Index('ix_trading_pairs_symbol', 'symbol'),
    UniqueConstraint('symbol', name='uq_trading_pairs_symbol'),
)

def __repr__(self):
    return f"<TradingPair(symbol='{self.symbol}', enabled={self.is_enabled})>"
```

class Strategy(Base, TimestampMixin):
“”“Trading strategy configuration and status”””
**tablename** = ‘strategies’

```
id = Column(Integer, primary_key=True)
name = Column(String(100), unique=True, nullable=False)
strategy_type = Column(String(50), nullable=False)  # spatial_arbitrage, triangular, etc.
is_enabled = Column(Boolean, default=True)
priority = Column(Integer, default=1)

# Configuration
config = Column(JSON)

# Performance metrics
opportunities_found = Column(Integer, default=0)
opportunities_executed = Column(Integer, default=0)
total_profit = Column(Numeric(20, 8), default=0)
total_loss = Column(Numeric(20, 8), default=0)
success_rate = Column(Numeric(5, 2), default=0)
avg_execution_time = Column(Numeric(10, 3), default=0)

# Status
last_scan_at = Column(DateTime)
last_opportunity_at = Column(DateTime)
error_count = Column(Integer, default=0)

# Relationships
opportunities = relationship("Opportunity", back_populates="strategy")

def __repr__(self):
    return f"<Strategy(name='{self.name}', type='{self.strategy_type}')>"
```

class Opportunity(Base, TimestampMixin):
“”“Detected arbitrage opportunities”””
**tablename** = ‘opportunities’

```
id = Column(Integer, primary_key=True)
opportunity_id = Column(String(100), unique=True, nullable=False)

# References
strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
trading_pair_id = Column(Integer, ForeignKey('trading_pairs.id'), nullable=False)

# Opportunity details
opportunity_type = Column(String(50), nullable=False)
status = Column(String(20), default='detected')  # detected, validated, executing, executed, failed, expired

# Financial data
amount = Column(Numeric(20, 8), nullable=False)
expected_profit = Column(Numeric(20, 8), nullable=False)
expected_profit_percent = Column(Numeric(8, 4), nullable=False)

# Risk assessment
risk_score = Column(Numeric(3, 2), default=0)
confidence_level = Column(Numeric(3, 2), default=0)
max_drawdown = Column(Numeric(20, 8), default=0)

# Execution details (for spatial arbitrage)
buy_exchange = Column(String(50))
sell_exchange = Column(String(50))
buy_price = Column(Numeric(20, 8))
sell_price = Column(Numeric(20, 8))
spread_percent = Column(Numeric(8, 4))

# Timestamps
detected_at = Column(DateTime, default=func.now())
validated_at = Column(DateTime)
executed_at = Column(DateTime)
expired_at = Column(DateTime)

# Additional data
metadata = Column(JSON)

# Relationships
strategy = relationship("Strategy", back_populates="opportunities")
trading_pair = relationship("TradingPair", back_populates="opportunities")
executions = relationship("Execution", back_populates="opportunity")

__table_args__ = (
    Index('ix_opportunities_status', 'status'),
    Index('ix_opportunities_detected_at', 'detected_at'),
    Index('ix_opportunities_strategy_id', 'strategy_id'),
)

def __repr__(self):
    return f"<Opportunity(id='{self.opportunity_id}', profit={self.expected_profit})>"
```

class Execution(Base, TimestampMixin):
“”“Trade execution records”””
**tablename** = ‘executions’

```
id = Column(Integer, primary_key=True)
execution_id = Column(String(100), unique=True, nullable=False)

# References
opportunity_id = Column(Integer, ForeignKey('opportunities.id'), nullable=False)

# Execution details
status = Column(String(20), default='pending')  # pending, executing, completed, failed, cancelled
execution_type = Column(String(20), default='market')  # market, limit

# Financial results
actual_profit = Column(Numeric(20, 8), default=0)
fees_paid = Column(Numeric(20, 8), default=0)
slippage = Column(Numeric(8, 4), default=0)

# Timing
started_at = Column(DateTime)
completed_at = Column(DateTime)
execution_time = Column(Numeric(10, 3))  # seconds

# Error handling
error_message = Column(Text)
retry_count = Column(Integer, default=0)

# Additional data
execution_data = Column(JSON)

# Relationships
opportunity = relationship("Opportunity", back_populates="executions")
orders = relationship("Order", back_populates="execution")

__table_args__ = (
    Index('ix_executions_status', 'status'),
    Index('ix_executions_completed_at', 'completed_at'),
)

def __repr__(self):
    return f"<Execution(id='{self.execution_id}', status='{self.status}')>"
```

class Order(Base, TimestampMixin):
“”“Individual order records”””
**tablename** = ‘orders’

```
id = Column(Integer, primary_key=True)
order_id = Column(String(100), nullable=False)
external_order_id = Column(String(100))  # Exchange's order ID

# References
exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
execution_id = Column(Integer, ForeignKey('executions.id'), nullable=False)

# Order details
symbol = Column(String(20), nullable=False)
side = Column(String(10), nullable=False)  # buy, sell
order_type = Column(String(20), default='market')  # market, limit, stop
status = Column(String(20), default='open')  # open, filled, cancelled, rejected

# Amounts and prices
amount = Column(Numeric(20, 8), nullable=False)
price = Column(Numeric(20, 8))
filled_amount = Column(Numeric(20, 8), default=0)
remaining_amount = Column(Numeric(20, 8))
average_price = Column(Numeric(20, 8))

# Fees
fee = Column(Numeric(20, 8), default=0)
fee_currency = Column(String(10))

# Timestamps
placed_at = Column(DateTime, default=func.now())
filled_at = Column(DateTime)
cancelled_at = Column(DateTime)

# Additional data
order_data = Column(JSON)

# Relationships
exchange = relationship("Exchange", back_populates="orders")
execution = relationship("Execution", back_populates="orders")

__table_args__ = (
    Index('ix_orders_status', 'status'),
    Index('ix_orders_exchange_id', 'exchange_id'),
    Index('ix_orders_placed_at', 'placed_at'),
)

def __repr__(self):
    return f"<Order(id='{self.order_id}', status='{self.status}')>"
```

class Balance(Base, TimestampMixin):
“”“Account balances across exchanges”””
**tablename** = ‘balances’

```
id = Column(Integer, primary_key=True)

# References
exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)

# Balance details
asset = Column(String(10), nullable=False)
total_balance = Column(Numeric(20, 8), default=0)
available_balance = Column(Numeric(20, 8), default=0)
locked_balance = Column(Numeric(20, 8), default=0)

# Valuation (in USDT)
usd_value = Column(Numeric(20, 8))
last_price = Column(Numeric(20, 8))

# Timestamp
snapshot_at = Column(DateTime, default=func.now())

# Relationships
exchange = relationship("Exchange", back_populates="balances")

__table_args__ = (
    Index('ix_balances_exchange_asset', 'exchange_id', 'asset'),
    Index('ix_balances_snapshot_at', 'snapshot_at'),
)

def __repr__(self):
    return f"<Balance(asset='{self.asset}', total={self.total_balance})>"
```

class MarketData(Base, TimestampMixin):
“”“Market data snapshots”””
**tablename** = ‘market_data’

```
id = Column(Integer, primary_key=True)

# References
exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
trading_pair_id = Column(Integer, ForeignKey('trading_pairs.id'), nullable=False)

# Price data
bid = Column(Numeric(20, 8), nullable=False)
ask = Column(Numeric(20, 8), nullable=False)
last = Column(Numeric(20, 8), nullable=False)
volume_24h = Column(Numeric(20, 8), default=0)

# Order book depth (top 5 levels)
bid_depth = Column(Numeric(20, 8), default=0)
ask_depth = Column(Numeric(20, 8), default=0)

# Calculated fields
spread = Column(Numeric(20, 8))
spread_percent = Column(Numeric(8, 4))

# Timestamps
exchange_timestamp = Column(DateTime)
received_at = Column(DateTime, default=func.now())

# Additional data
orderbook_data = Column(JSON)

# Relationships
exchange = relationship("Exchange", back_populates="market_data")
trading_pair = relationship("TradingPair", back_populates="market_data")

__table_args__ = (
    Index('ix_market_data_exchange_pair', 'exchange_id', 'trading_pair_id'),
    Index('ix_market_data_received_at', 'received_at'),
)

def __repr__(self):
    return f"<MarketData(exchange={self.exchange_id}, pair={self.trading_pair_id})>"
```

class PerformanceMetric(Base, TimestampMixin):
“”“Performance metrics and analytics”””
**tablename** = ‘performance_metrics’

```
id = Column(Integer, primary_key=True)

# Metric details
metric_type = Column(String(50), nullable=False)  # daily_pnl, strategy_performance, etc.
metric_name = Column(String(100), nullable=False)
value = Column(Numeric(20, 8), nullable=False)

# Context
period_start = Column(DateTime)
period_end = Column(DateTime)
granularity = Column(String(20))  # hourly, daily, weekly, monthly

# Additional data
metadata = Column(JSON)

__table_args__ = (
    Index('ix_performance_metrics_type_name', 'metric_type', 'metric_name'),
    Index('ix_performance_metrics_period', 'period_start', 'period_end'),
)

def __repr__(self):
    return f"<PerformanceMetric(type='{self.metric_type}', value={self.value})>"
```

class SystemLog(Base, TimestampMixin):
“”“System logs for debugging and analysis”””
**tablename** = ‘system_logs’

```
id = Column(Integer, primary_key=True)

# Log details
level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
logger_name = Column(String(100), nullable=False)
message = Column(Text, nullable=False)

# Context
module = Column(String(100))
function = Column(String(100))
line_number = Column(Integer)

# Additional data
extra_data = Column(JSON)
stack_trace = Column(Text)

# Timestamp
logged_at = Column(DateTime, default=func.now())

__table_args__ = (
    Index('ix_system_logs_level', 'level'),
    Index('ix_system_logs_logger', 'logger_name'),
    Index('ix_system_logs_logged_at', 'logged_at'),
)

def __repr__(self):
    return f"<SystemLog(level='{self.level}', logger='{self.logger_name}')>"
```

class RiskAssessment(Base, TimestampMixin):
“”“Risk assessment records”””
**tablename** = ‘risk_assessments’

```
id = Column(Integer, primary_key=True)

# References
opportunity_id = Column(Integer, ForeignKey('opportunities.id'))

# Assessment details
risk_score = Column(Numeric(3, 2), nullable=False)
risk_level = Column(String(20), nullable=False)  # low, medium, high, critical
approved = Column(Boolean, nullable=False)

# Violations and warnings
violations = Column(JSON)
warnings = Column(JSON)
recommendations = Column(JSON)

# Adjustments
max_position_size = Column(Numeric(20, 8))
confidence_adjustment = Column(Numeric(3, 2), default=1.0)

# Assessment data
assessment_data = Column(JSON)

__table_args__ = (
    Index('ix_risk_assessments_approved', 'approved'),
    Index('ix_risk_assessments_risk_level', 'risk_level'),
)

def __repr__(self):
    return f"<RiskAssessment(score={self.risk_score}, approved={self.approved})>"
```

class AIAnalysis(Base, TimestampMixin):
“”“AI analysis results from Claude”””
**tablename** = ‘ai_analyses’

```
id = Column(Integer, primary_key=True)

# Analysis details
analysis_type = Column(String(50), nullable=False)  # performance, strategy, risk, etc.
trigger = Column(String(50), nullable=False)  # scheduled, emergency, manual
status = Column(String(20), default='pending')  # pending, running, completed, failed

# Input and output
input_data = Column(JSON)
analysis_result = Column(JSON)
recommendations = Column(JSON)

# Execution details
started_at = Column(DateTime)
completed_at = Column(DateTime)
duration_seconds = Column(Numeric(10, 3))

# Error handling
error_message = Column(Text)

__table_args__ = (
    Index('ix_ai_analyses_type', 'analysis_type'),
    Index('ix_ai_analyses_status', 'status'),
    Index('ix_ai_analyses_completed_at', 'completed_at'),
)

def __repr__(self):
    return f"<AIAnalysis(type='{self.analysis_type}', status='{self.status}')>"
```

class CodeUpdate(Base, TimestampMixin):
“”“AI-generated code updates”””
**tablename** = ‘code_updates’

```
id = Column(Integer, primary_key=True)
update_id = Column(String(100), unique=True, nullable=False)

# Update details
file_path = Column(String(500), nullable=False)
description = Column(Text, nullable=False)
change_type = Column(String(50), nullable=False)  # optimization, bug_fix, feature

# Content
original_content = Column(Text)
updated_content = Column(Text, nullable=False)
diff = Column(Text)

# Status
status = Column(String(20), default='pending')  # pending, validated, applied, rejected
applied_at = Column(DateTime)
validation_results = Column(JSON)

# Safety
safety_score = Column(Numeric(3, 2), default=0)
backup_path = Column(String(500))

# AI context
ai_analysis_id = Column(Integer, ForeignKey('ai_analyses.id'))

__table_args__ = (
    Index('ix_code_updates_status', 'status'),
    Index('ix_code_updates_file_path', 'file_path'),
)

def __repr__(self):
    return f"<CodeUpdate(id='{self.update_id}', status='{self.status}')>"
```

# Validation functions

@validates(‘risk_score’)
def validate_risk_score(self, key, risk_score):
“”“Validate risk score is between 0 and 1”””
if risk_score is not None:
if not 0 <= risk_score <= 1:
raise ValueError(“Risk score must be between 0 and 1”)
return risk_score

@validates(‘confidence_level’)
def validate_confidence_level(self, key, confidence_level):
“”“Validate confidence level is between 0 and 1”””
if confidence_level is not None:
if not 0 <= confidence_level <= 1:
raise ValueError(“Confidence level must be between 0 and 1”)
return confidence_level

# Add validation to relevant models

Opportunity.validate_risk_score = validates(‘risk_score’)(validate_risk_score)
Opportunity.validate_confidence_level = validates(‘confidence_level’)(validate_confidence_level)
RiskAssessment.validate_risk_score = validates(‘risk_score’)(validate_risk_score)