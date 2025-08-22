“””
Advanced Logging System for SmartArb Engine
Provides structured logging with multiple outputs and specialized loggers
“””

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
from structlog.stdlib import LoggerFactory
import json
from datetime import datetime
import traceback

def setup_logging(config: Dict[str, Any]) -> None:
“””
Setup comprehensive logging system for SmartArb Engine

```
Features:
- Structured logging with structlog
- Multiple output formats (JSON, human-readable)
- Rotating file logs
- Console logging with colors
- Separate logs for trades, errors, and performance
"""

# Get logging configuration
log_config = config.get('logging', {})
log_level = log_config.get('level', 'INFO')
log_dir = Path(log_config.get('file_logging', {}).get('log_dir', 'logs'))

# Create logs directory
log_dir.mkdir(exist_ok=True)

# Configure standard library logging
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=getattr(logging, log_level.upper())
)

# Setup timestamper
timestamper = structlog.processors.TimeStamper(fmt="ISO")

# Setup processors based on environment
shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.filter_by_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    timestamper,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]

# Console logging processors
console_processors = shared_processors + [
    structlog.dev.ConsoleRenderer(colors=log_config.get('console_logging', {}).get('colored', True))
]

# File logging processors (JSON format)
file_processors = shared_processors + [
    structlog.processors.JSONRenderer()
]

# Configure structlog
structlog.configure(
    processors=console_processors,
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Setup file logging if enabled
if log_config.get('file_logging', {}).get('enabled', True):
    _setup_file_logging(log_config, log_dir, file_processors)

# Setup specialized loggers
_setup_specialized_loggers(log_config, log_dir)

# Log initial setup message
logger = structlog.get_logger("smartarb.logging")
logger.info("logging_system_initialized",
            level=log_level,
            log_dir=str(log_dir),
            file_logging=log_config.get('file_logging', {}).get('enabled', True))
```

def _setup_file_logging(log_config: Dict[str, Any], log_dir: Path, processors: list):
“”“Setup rotating file logging”””

```
file_config = log_config.get('file_logging', {})
max_bytes = file_config.get('max_file_size_mb', 50) * 1024 * 1024  # Convert to bytes
backup_count = file_config.get('backup_count', 5)

# Main application log
main_log_file = log_dir / "smartarb.log"
main_handler = logging.handlers.RotatingFileHandler(
    main_log_file,
    maxBytes=max_bytes,
    backupCount=backup_count,
    encoding='utf-8'
)

# Create a separate logger for file output with JSON formatting
file_logger = logging.getLogger("smartarb_file")
file_logger.setLevel(getattr(logging, log_config.get('level', 'INFO').upper()))
file_logger.addHandler(main_handler)

# Configure structlog to also log to file
structlog.configure_once(
    processors=processors,
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

def _setup_specialized_loggers(log_config: Dict[str, Any], log_dir: Path):
“”“Setup specialized loggers for different components”””

```
file_config = log_config.get('file_logging', {})
if not file_config.get('enabled', True):
    return

max_bytes = file_config.get('max_file_size_mb', 50) * 1024 * 1024
backup_count = file_config.get('backup_count', 5)

# Trading activity logger
trade_logger = logging.getLogger("smartarb.trades")
trade_handler = logging.handlers.RotatingFileHandler(
    log_dir / "trades.log",
    maxBytes=max_bytes,
    backupCount=backup_count,
    encoding='utf-8'
)
trade_handler.setFormatter(JSONLogFormatter())
trade_logger.addHandler(trade_handler)
trade_logger.setLevel(logging.INFO)

# Error logger
error_logger = logging.getLogger("smartarb.errors")
error_handler = logging.handlers.RotatingFileHandler(
    log_dir / "errors.log",
    maxBytes=max_bytes,
    backupCount=backup_count,
    encoding='utf-8'
)
error_handler.setFormatter(JSONLogFormatter())
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.ERROR)

# Performance logger
perf_logger = logging.getLogger("smartarb.performance")
perf_handler = logging.handlers.RotatingFileHandler(
    log_dir / "performance.log",
    maxBytes=max_bytes,
    backupCount=backup_count,
    encoding='utf-8'
)
perf_handler.setFormatter(JSONLogFormatter())
perf_logger.addHandler(perf_handler)
perf_logger.setLevel(logging.INFO)

# AI Analysis logger
ai_logger = logging.getLogger("smartarb.ai")
ai_handler = logging.handlers.RotatingFileHandler(
    log_dir / "ai_analysis.log",
    maxBytes=max_bytes,
    backupCount=backup_count,
    encoding='utf-8'
)
ai_handler.setFormatter(JSONLogFormatter())
ai_logger.addHandler(ai_handler)
ai_logger.setLevel(logging.INFO)

# Risk management logger
risk_logger = logging.getLogger("smartarb.risk")
risk_handler = logging.handlers.RotatingFileHandler(
    log_dir / "risk.log",
    maxBytes=max_bytes,
    backupCount=backup_count,
    encoding='utf-8'
)
risk_handler.setFormatter(JSONLogFormatter())
risk_logger.addHandler(risk_handler)
risk_logger.setLevel(logging.WARNING)
```

class JSONLogFormatter(logging.Formatter):
“”“Custom JSON formatter for structured file logging”””

```
def format(self, record):
    log_entry = {
        'timestamp': datetime.fromtimestamp(record.created).isoformat(),
        'level': record.levelname,
        'logger': record.name,
        'message': record.getMessage(),
        'module': record.module,
        'function': record.funcName,
        'line': record.lineno
    }
    
    # Add exception info if present
    if record.exc_info:
        log_entry['exception'] = {
            'type': record.exc_info[0].__name__,
            'message': str(record.exc_info[1]),
            'traceback': traceback.format_exception(*record.exc_info)
        }
    
    # Add extra fields from the log record
    for key, value in record.__dict__.items():
        if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                      'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 
                      'relativeCreated', 'thread', 'threadName', 'processName', 
                      'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
            log_entry[key] = value
    
    return json.dumps(log_entry, default=str)
```

def get_specialized_loggers() -> Dict[str, Any]:
“”“Get all specialized loggers for different components”””

```
return {
    'main': structlog.get_logger("smartarb.main"),
    'engine': structlog.get_logger("smartarb.engine"),
    'trading': structlog.get_logger("smartarb.trades"),
    'risk': structlog.get_logger("smartarb.risk"),
    'portfolio': structlog.get_logger("smartarb.portfolio"),
    'execution': structlog.get_logger("smartarb.execution"),
    'strategies': structlog.get_logger("smartarb.strategies"),
    'exchanges': structlog.get_logger("smartarb.exchanges"),
    'ai': structlog.get_logger("smartarb.ai"),
    'performance': structlog.get_logger("smartarb.performance"),
    'notifications': structlog.get_logger("smartarb.notifications"),
    'config': structlog.get_logger("smartarb.config"),
    'database': structlog.get_logger("smartarb.database"),
    'websocket': structlog.get_logger("smartarb.websocket"),
    'api': structlog.get_logger("smartarb.api"),
    'monitoring': structlog.get_logger("smartarb.monitoring")
}
```

class TradeLogger:
“”“Specialized logger for trading activities”””

```
def __init__(self):
    self.logger = structlog.get_logger("smartarb.trades")

def log_opportunity_found(self, opportunity: Any):
    """Log when an arbitrage opportunity is found"""
    self.logger.info("opportunity_found",
                    opportunity_id=opportunity.opportunity_id,
                    strategy=opportunity.strategy_name,
                    symbol=opportunity.symbol,
                    expected_profit=float(opportunity.expected_profit),
                    profit_percent=float(opportunity.expected_profit_percent),
                    risk_score=opportunity.risk_score,
                    confidence=opportunity.confidence_level)

def log_trade_executed(self, execution_result: Any):
    """Log completed trade execution"""
    self.logger.info("trade_executed",
                    execution_id=execution_result.execution_id,
                    success=execution_result.success,
                    profit_loss=float(execution_result.profit_loss),
                    execution_time=execution_result.execution_time,
                    fees_paid=float(execution_result.fees_paid),
                    slippage=float(execution_result.slippage) if execution_result.slippage else 0)

def log_trade_failed(self, execution_result: Any):
    """Log failed trade execution"""
    self.logger.error("trade_failed",
                     execution_id=execution_result.execution_id,
                     error_message=execution_result.error_message,
                     status=execution_result.status.value if execution_result.status else "unknown")

def log_risk_violation(self, opportunity: Any, violations: list):
    """Log risk management violations"""
    self.logger.warning("trade_blocked_by_risk",
                       opportunity_id=opportunity.opportunity_id,
                       violations=[v.value for v in violations],
                       risk_score=opportunity.risk_score)
```

class PerformanceLogger:
“”“Logger for performance metrics and monitoring”””

```
def __init__(self):
    self.logger = structlog.get_logger("smartarb.performance")

def log_system_metrics(self, metrics: Dict[str, Any]):
    """Log system performance metrics"""
    self.logger.info("system_metrics",
                    cpu_percent=metrics.get('cpu_percent', 0),
                    memory_percent=metrics.get('memory_percent', 0),
                    disk_usage=metrics.get('disk_usage', 0),
                    temperature=metrics.get('temperature', 0),
                    network_io=metrics.get('network_io', {}))

def log_exchange_latency(self, exchange: str, endpoint: str, latency_ms: float):
    """Log exchange API latency"""
    self.logger.info("exchange_latency",
                    exchange=exchange,
                    endpoint=endpoint,
                    latency_ms=latency_ms)

def log_strategy_performance(self, strategy: str, metrics: Dict[str, Any]):
    """Log strategy performance metrics"""
    self.logger.info("strategy_performance",
                    strategy=strategy,
                    opportunities_found=metrics.get('opportunities_found', 0),
                    opportunities_executed=metrics.get('opportunities_executed', 0),
                    success_rate=metrics.get('success_rate', 0),
                    total_profit=metrics.get('total_profit', 0))
```

class AILogger:
“”“Specialized logger for AI analysis activities”””

```
def __init__(self):
    self.logger = structlog.get_logger("smartarb.ai")

def log_analysis_started(self, analysis_type: str, trigger: str):
    """Log AI analysis start"""
    self.logger.info("ai_analysis_started",
                    analysis_type=analysis_type,
                    trigger=trigger,
                    timestamp=datetime.now().isoformat())

def log_analysis_completed(self, analysis_type: str, duration: float, 
                         recommendations_count: int):
    """Log AI analysis completion"""
    self.logger.info("ai_analysis_completed",
                    analysis_type=analysis_type,
                    duration_seconds=duration,
                    recommendations_count=recommendations_count)

def log_code_update_applied(self, update_id: str, file_path: str, 
                          success: bool, description: str):
    """Log code update application"""
    self.logger.info("ai_code_update_applied",
                    update_id=update_id,
                    file_path=file_path,
                    success=success,
                    description=description)

def log_analysis_error(self, analysis_type: str, error: str):
    """Log AI analysis errors"""
    self.logger.error("ai_analysis_error",
                     analysis_type=analysis_type,
                     error=error)
```

def setup_raspberry_pi_logging():
“”“Special logging configuration for Raspberry Pi”””

```
# Reduce log verbosity for memory-constrained environment
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=False)  # Disable colors for Pi
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Setup syslog for system-wide logging
try:
    import logging.handlers
    syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
    syslog_handler.setFormatter(
        logging.Formatter('smartarb[%(process)d]: %(levelname)s - %(message)s')
    )
    
    root_logger = logging.getLogger()
    root_logger.addHandler(syslog_handler)
    
except Exception:
    pass  # Syslog not available
```

def log_startup_info(config: Dict[str, Any]):
“”“Log important startup information”””

```
logger = structlog.get_logger("smartarb.startup")

# System information
try:
    import platform
    import psutil
    
    logger.info("system_info",
               platform=platform.platform(),
               python_version=platform.python_version(),
               cpu_count=psutil.cpu_count(),
               memory_gb=round(psutil.virtual_memory().total / (1024**3), 2),
               disk_free_gb=round(psutil.disk_usage('/').free / (1024**3), 2))
except ImportError:
    logger.info("system_info", status="unavailable")

# Configuration summary
logger.info("configuration_loaded",
           exchanges_enabled=len([ex for ex in config.get('exchanges', {}).values() 
                                if ex.get('enabled', False)]),
           strategies_enabled=len([st for st in config.get('strategies', {}).values() 
                                 if st.get('enabled', False)]),
           paper_trading=config.get('trading', {}).get('paper_trading', True),
           ai_enabled=config.get('ai', {}).get('enabled', False))
```

# Context manager for performance timing

class LogTimer:
“”“Context manager for logging execution times”””

```
def __init__(self, logger, operation: str, **context):
    self.logger = logger
    self.operation = operation
    self.context = context
    self.start_time = None

def __enter__(self):
    self.start_time = datetime.now()
    self.logger.debug(f"{self.operation}_started", **self.context)
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    duration = (datetime.now() - self.start_time).total_seconds()
    
    if exc_type is None:
        self.logger.info(f"{self.operation}_completed", 
                       duration_seconds=duration, **self.context)
    else:
        self.logger.error(f"{self.operation}_failed",
                        duration_seconds=duration,
                        error_type=exc_type.__name__,
                        error_message=str(exc_val),
                        **self.context)
```