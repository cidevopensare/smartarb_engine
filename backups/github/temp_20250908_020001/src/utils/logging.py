#!/usr/bin/env python3
“””
SmartArb Engine Logging System
Professional logging configuration with structured logging, multiple handlers,
and performance optimization for Raspberry Pi
“””

import sys
import os
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
from datetime import datetime
import json
import gzip
import shutil

# Configure structlog

structlog.configure(
processors=[
structlog.stdlib.filter_by_level,
structlog.stdlib.add_logger_name,
structlog.stdlib.add_log_level,
structlog.stdlib.PositionalArgumentsFormatter(),
structlog.processors.TimeStamper(fmt=“iso”),
structlog.processors.StackInfoRenderer(),
structlog.processors.format_exc_info,
structlog.processors.UnicodeDecoder(),
structlog.processors.JSONRenderer()
],
context_class=dict,
logger_factory=structlog.stdlib.LoggerFactory(),
wrapper_class=structlog.stdlib.BoundLogger,
cache_logger_on_first_use=True,
)

class SmartArbFormatter(logging.Formatter):
“”“Custom formatter for SmartArb Engine logs”””

```
def __init__(self):
    super().__init__()
    self.formatters = {
        logging.DEBUG: logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ),
        logging.INFO: logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ),
        logging.WARNING: logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ),
        logging.ERROR: logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s - %(pathname)s:%(lineno)d',
            datefmt='%Y-%m-%d %H:%M:%S'
        ),
        logging.CRITICAL: logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s - %(pathname)s:%(lineno)d',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    }

def format(self, record):
    formatter = self.formatters.get(record.levelno, self.formatters[logging.INFO])
    return formatter.format(record)
```

class PerformanceOptimizedRotatingFileHandler(logging.handlers.RotatingFileHandler):
“”“Optimized rotating file handler for Raspberry Pi”””

```
def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False):
    super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
    self.compression = True

def doRollover(self):
    """Enhanced rollover with compression for space efficiency"""
    if self.stream:
        self.stream.close()
        self.stream = None
    
    if self.backupCount > 0:
        for i in range(self.backupCount - 1, 0, -1):
            sfn = self.rotation_filename("%s.%d.gz" % (self.baseFilename, i))
            dfn = self.rotation_filename("%s.%d.gz" % (self.baseFilename, i + 1))
            if os.path.exists(sfn):
                if os.path.exists(dfn):
                    os.remove(dfn)
                os.rename(sfn, dfn)
        
        # Compress the current log file
        dfn = self.rotation_filename(self.baseFilename + ".1.gz")
        if os.path.exists(dfn):
            os.remove(dfn)
        
        # Compress the log file
        with open(self.baseFilename, 'rb') as f_in:
            with gzip.open(dfn, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    if not self.delay:
        self.stream = self._open()
```

class SmartArbLoggingManager:
“”“Centralized logging management”””

```
def __init__(self, config: Dict[str, Any]):
    self.config = config
    self.logging_config = config.get('logging', {})
    self.log_dir = Path(self.logging_config.get('log_directory', 'logs'))
    self.log_level = self.logging_config.get('log_level', 'INFO')
    self.max_file_size = self.logging_config.get('max_file_size_mb', 50) * 1024 * 1024
    self.backup_count = self.logging_config.get('backup_count', 10)
    
    # Create log directory
    self.log_dir.mkdir(exist_ok=True)
    
    # Specialized loggers
    self.loggers = {}
    self._setup_loggers()

def _setup_loggers(self):
    """Setup specialized loggers for different components"""
    
    # Main application logger
    self._setup_logger(
        'smartarb.main',
        self.log_dir / 'main.log',
        logging.INFO
    )
    
    # Exchange loggers
    for exchange in ['kraken', 'bybit', 'mexc']:
        self._setup_logger(
            f'smartarb.exchange.{exchange}',
            self.log_dir / f'exchange_{exchange}.log',
            logging.INFO
        )
    
    # Trading activity logger
    self._setup_logger(
        'smartarb.trading',
        self.log_dir / 'trading.log',
        logging.INFO
    )
    
    # Risk management logger
    self._setup_logger(
        'smartarb.risk',
        self.log_dir / 'risk.log',
        logging.WARNING
    )
    
    # AI system logger
    self._setup_logger(
        'smartarb.ai',
        self.log_dir / 'ai.log',
        logging.INFO
    )
    
    # Performance logger
    self._setup_logger(
        'smartarb.performance',
        self.log_dir / 'performance.log',
        logging.INFO
    )
    
    # Error logger
    self._setup_logger(
        'smartarb.error',
        self.log_dir / 'error.log',
        logging.ERROR
    )

def _setup_logger(self, name: str, file_path: Path, level: int):
    """Setup individual logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    
    # File handler with rotation
    file_handler = PerformanceOptimizedRotatingFileHandler(
        filename=file_path,
        maxBytes=self.max_file_size,
        backupCount=self.backup_count
    )
    file_handler.setFormatter(SmartArbFormatter())
    logger.addHandler(file_handler)
    
    # Console handler for important logs
    if level >= logging.WARNING or name == 'smartarb.main':
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(SmartArbFormatter())
        logger.addHandler(console_handler)
    
    self.loggers[name] = logger

def get_logger(self, name: str) -> logging.Logger:
    """Get specialized logger"""
    return self.loggers.get(name, logging.getLogger(name))
```

def setup_logging(config: Dict[str, Any]) -> SmartArbLoggingManager:
“”“Initialize logging system”””
logging_manager = SmartArbLoggingManager(config)

```
# Set root logger level
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, config.get('logging', {}).get('log_level', 'INFO')))

# Reduce noise from external libraries
logging.getLogger('ccxt').setLevel(logging.WARNING)
logging.getLogger('websockets').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

return logging_manager
```

def get_specialized_loggers(logging_manager: SmartArbLoggingManager) -> Dict[str, logging.Logger]:
“”“Get all specialized loggers”””
return logging_manager.loggers

class LoggingMixin:
“”“Mixin class to add logging capabilities to any class”””

```
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.logger = structlog.get_logger(self.__class__.__name__.lower())

def log_info(self, message: str, **kwargs):
    """Log info message"""
    self.logger.info(message, **kwargs)

def log_warning(self, message: str, **kwargs):
    """Log warning message"""
    self.logger.warning(message, **kwargs)

def log_error(self, message: str, **kwargs):
    """Log error message"""
    self.logger.error(message, **kwargs)

def log_debug(self, message: str, **kwargs):
    """Log debug message"""
    self.logger.debug(message, **kwargs)
```

def performance_logger(func):
“”“Decorator to log function performance”””
def wrapper(*args, **kwargs):
start_time = datetime.now()
logger = structlog.get_logger(func.**module**)

```
    try:
        result = func(*args, **kwargs)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            "function_executed",
            function=func.__name__,
            execution_time_seconds=execution_time,
            success=True
        )
        
        return result
        
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.error(
            "function_failed",
            function=func.__name__,
            execution_time_seconds=execution_time,
            error=str(e),
            success=False
        )
        
        raise

return wrapper
```