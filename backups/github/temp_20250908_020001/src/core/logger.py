#!/usr/bin/env python3
"""
Logging setup for SmartArb Engine
Professional logging configuration with file rotation and formatting
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

def setup_logging(config=None) -> logging.Logger:
    """Setup comprehensive logging for SmartArb Engine"""
    
    # Get configuration values
    log_level = getattr(config, 'log_level', 'INFO') if config else os.getenv('LOG_LEVEL', 'INFO')
    debug_mode = getattr(config, 'debug_mode', True) if config else os.getenv('DEBUG_MODE', 'true').lower() == 'true'
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Setup main logger
    logger = logging.getLogger('smartarb')
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter if not debug_mode else detailed_formatter)
    console_handler.setLevel(logging.INFO if not debug_mode else logging.DEBUG)
    logger.addHandler(console_handler)
    
    # Main log file handler with rotation
    main_log_file = log_dir / f"smartarb_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    # Error log file handler
    error_log_file = log_dir / f"smartarb_errors_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.WARNING)
    logger.addHandler(error_handler)
    
    # Trading activity log (for trades and opportunities)
    trading_log_file = log_dir / f"smartarb_trading_{datetime.now().strftime('%Y%m%d')}.log"
    trading_handler = logging.FileHandler(trading_log_file, encoding='utf-8')
    trading_formatter = logging.Formatter(
        fmt='%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    trading_handler.setFormatter(trading_formatter)
    
    # Create trading logger
    trading_logger = logging.getLogger('smartarb.trading')
    trading_logger.addHandler(trading_handler)
    trading_logger.setLevel(logging.INFO)
    
    # Prevent duplicate messages
    logger.propagate = False
    trading_logger.propagate = False
    
    # Log initial setup message
    logger.info("=" * 60)
    logger.info("🚀 SmartArb Engine Logging System Initialized")
    logger.info("=" * 60)
    logger.info(f"📊 Log Level: {log_level.upper()}")
    logger.info(f"🔍 Debug Mode: {debug_mode}")
    logger.info(f"📁 Log Directory: {log_dir.absolute()}")
    logger.info(f"📄 Main Log: {main_log_file.name}")
    logger.info(f"⚠️  Error Log: {error_log_file.name}")
    logger.info(f"📈 Trading Log: {trading_log_file.name}")
    logger.info("=" * 60)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(f'smartarb.{name}')

def log_trade_activity(message: str) -> None:
    """Log trading activity to dedicated trading log"""
    trading_logger = logging.getLogger('smartarb.trading')
    trading_logger.info(message)

class PerformanceLogger:
    """Logger for performance metrics"""
    
    def __init__(self):
        self.logger = get_logger('performance')
        self.start_times = {}
    
    def start_timer(self, operation: str) -> None:
        """Start timing an operation"""
        import time
        self.start_times[operation] = time.time()
        self.logger.debug(f"⏱️  Started timing: {operation}")
    
    def end_timer(self, operation: str) -> float:
        """End timing an operation and log the duration"""
        import time
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            self.logger.info(f"⏱️  {operation}: {duration:.3f}s")
            del self.start_times[operation]
            return duration
        return 0.0
    
    def log_metric(self, metric_name: str, value: float, unit: str = ""):
        """Log a performance metric"""
        self.logger.info(f"📊 {metric_name}: {value}{unit}")

# Global performance logger instance
performance_logger = PerformanceLogger()
