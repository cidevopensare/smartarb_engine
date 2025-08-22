"""
Logging Configuration for SmartArb Engine
Structured logging setup with multiple outputs and performance tracking
"""

import sys
import os
import logging
import logging.handlers
from typing import Dict, Any, Optional
from pathlib import Path
import structlog
from structlog.stdlib import LoggerFactory
import json
import time


def setup_logging(config: Dict[str, Any]):
    """
    Setup structured logging for SmartArb Engine
    
    Args:
        config: Logging configuration dictionary
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, config.get('level', 'INFO').upper())
    )
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add console processor
    if config.get('console_output', True):
        processors.append(
            structlog.dev.ConsoleRenderer(colors=True)
        )
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup file logging if enabled
    if config.get('file_logging', True):
        setup_file_logging(config)
    
    # Setup component-specific logging levels
    component_levels = config.get('components', {})
    for component, level in component_levels.items():
        logger = logging.getLogger(f"src.{component}")
        logger.setLevel(getattr(logging, level.upper()))
    
    # Log startup message
    logger = structlog.get_logger(__name__)
    logger.info("logging_configured", 
               level=config.get('level', 'INFO'),
               file_logging=config.get('file_logging', True))


def setup_file_logging(config: Dict[str, Any]):
    """Setup file-based logging with rotation"""
    
    log_file = config.get('log_file', 'logs/smartarb.log')
    max_file_size = config.get('max_file_size', 10 * 1024 * 1024)  # 10MB
    backup_count = config.get('backup_count', 5)
    
    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    # Create formatter for file output (JSON format for better parsing)
    formatter = JSONFormatter()
    file_handler.setFormatter(formatter)
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    # Setup separate files for different log levels if configured
    if config.get('separate_error_log', False):
        error_handler = logging.handlers.RotatingFileHandler(
            'logs/smartarb_errors.log',
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for log records"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        
        # Base log data
        log_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created)),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from structlog
        if hasattr(record, '_record'):
            # Structlog record
            for key, value in record._record.items():
                if key not in ['event', 'level', 'logger', 'timestamp']:
                    log_data[key] = value
        
        # Add custom fields
        extra_fields = [
            'module', 'funcName', 'lineno', 'process', 'processName', 
            'thread', 'threadName'
        ]
        
        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


class PerformanceLogger:
    """Performance logging utility for tracking execution times"""
    
    def __init__(self, logger_name: str = __name__):
        self.logger = structlog.get_logger(logger_name)
    
    def __call__(self, operation_name: str):
        """Decorator for timing function execution"""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000
                    self.logger.debug("operation_completed",
                                    operation=operation_name,
                                    duration_ms=execution_time,
                                    success=True)
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    self.logger.error("operation_failed",
                                    operation=operation_name,
                                    duration_ms=execution_time,
                                    error=str(e))
                    raise
            
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000
                    self.logger.debug("operation_completed",
                                    operation=operation_name,
                                    duration_ms=execution_time,
                                    success=True)
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    self.logger.error("operation_failed",
                                    operation=operation_name,
                                    duration_ms=execution_time,
                                    error=str(e))
                    raise
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def time_block(self, block_name: str):
        """Context manager for timing code blocks"""
        return TimeBlock(self.logger, block_name)


class TimeBlock:
    """Context manager for timing code execution"""
    
    def __init__(self, logger, block_name: str):
        self.logger = logger
        self.block_name = block_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug("block_started", block=self.block_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = (time.time() - self.start_time) * 1000
        
        if exc_type is None:
            self.logger.debug("block_completed",
                            block=self.block_name,
                            duration_ms=execution_time,
                            success=True)
        else:
            self.logger.error("block_failed",
                            block=self.block_name,
                            duration_ms=execution_time,
                            error=str(exc_val))


class TradeLogger:
    """Specialized logger for trading activities"""
    
    def __init__(self):
        self.logger = structlog.get_logger("trading")
        
        # Setup separate trade log file
        trade_handler = logging.handlers.RotatingFileHandler(
            'logs/trades.log',
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        trade_handler.setFormatter(JSONFormatter())
        
        trade_logger = logging.getLogger("trading")
        trade_logger.addHandler(trade_handler)
        trade_logger.setLevel(logging.INFO)
    
    def log_opportunity(self, opportunity):
        """Log arbitrage opportunity detection"""
        self.logger.info("opportunity_detected",
                        opportunity_id=opportunity.opportunity_id,
                        strategy=opportunity.strategy,
                        symbol=opportunity.symbol,
                        amount=float(opportunity.amount),
                        expected_profit=float(opportunity.expected_profit_percent),
                        timestamp=opportunity.timestamp)
    
    def log_execution_start(self, opportunity, execution_id: str):
        """Log start of trade execution"""
        self.logger.info("execution_started",
                        opportunity_id=opportunity.opportunity_id,
                        execution_id=execution_id,
                        symbol=opportunity.symbol,
                        amount=float(opportunity.amount))
    
    def log_execution_result(self, execution_result):
        """Log trade execution result"""
        self.logger.info("execution_completed",
                        opportunity_id=execution_result.opportunity_id,
                        execution_id=execution_result.execution_id,
                        success=execution_result.success,
                        profit=float(execution_result.realized_profit),
                        fees=float(execution_result.total_fees),
                        duration_ms=execution_result.execution_time_ms,
                        orders_count=len(execution_result.orders))
    
    def log_order(self, order, action: str):
        """Log individual order activity"""
        self.logger.info("order_activity",
                        action=action,  # 'placed', 'filled', 'cancelled'
                        order_id=order.id,
                        symbol=order.symbol,
                        side=order.side.value,
                        amount=float(order.amount),
                        price=float(order.price),
                        status=order.status.value)
    
    def log_risk_rejection(self, opportunity, reason: str):
        """Log opportunity rejection by risk management"""
        self.logger.warning("opportunity_rejected",
                          opportunity_id=opportunity.opportunity_id,
                          symbol=opportunity.symbol,
                          reason=reason,
                          amount=float(opportunity.amount),
                          expected_profit=float(opportunity.expected_profit_percent))


# Global instances
perf_logger = PerformanceLogger()
trade_logger = TradeLogger()


# Convenience decorators
def log_performance(operation_name: str):
    """Decorator for logging function performance"""
    return perf_logger(operation_name)


def get_logger(name: str):
    """Get a structured logger instance"""
    return structlog.get_logger(name)
