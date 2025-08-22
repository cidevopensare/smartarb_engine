“””
Advanced Logging System for SmartArb Engine
Provides structured logging with file rotation, performance tracking, and AI integration
“””

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
from structlog.stdlib import LoggerFactory
import colorama
from colorama import Fore, Back, Style

def setup_logging(config: Dict[str, Any]) -> None:
“””
Setup comprehensive logging system for SmartArb Engine

```
Features:
- Structured logging with structlog
- File rotation with size limits
- Colored console output
- Performance tracking
- AI-friendly log format
- Raspberry Pi optimized
"""

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)

# Get logging configuration
logging_config = config.get('logging', {})
log_level = getattr(logging, logging_config.get('level', 'INFO').upper())
log_format = logging_config.get('format', 'structured')

# Create logs directory
log_dir = Path(logging_config.get('file_logging', {}).get('log_dir', 'logs'))
log_dir.mkdir(exist_ok=True)

# Configure standard logging
logging.basicConfig(
    level=log_level,
    format='%(message)s'
)

# Setup structlog processors
processors = [
    structlog.stdlib.filter_by_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    add_timestamp,
    add_system_info,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]

# Add performance tracking
processors.append(add_performance_metrics)

# Add AI-friendly formatting for analysis
processors.append(add_ai_metadata)

# Console output processor
if logging_config.get('console_logging', {}).get('enabled', True):
    if logging_config.get('console_logging', {}).get('colored', True):
        processors.append(colored_console_renderer)
    else:
        processors.append(structlog.dev.ConsoleRenderer())

# Configure structlog
structlog.configure(
    processors=processors,
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Setup file logging
if logging_config.get('file_logging', {}).get('enabled', True):
    setup_file_logging(logging_config, log_dir)

# Setup specific logger levels
logger_levels = logging_config.get('loggers', {})
for logger_name, level in logger_levels.items():
    logging.getLogger(logger_name).setLevel(getattr(logging, level.upper()))

# Get root structlog logger and log initialization
logger = structlog.get_logger(__name__)
logger.info("logging_system_initialized",
           level=log_level,
           format=log_format,
           log_dir=str(log_dir),
           processors=len(processors))
```

def setup_file_logging(logging_config: Dict[str, Any], log_dir: Path) -> None:
“”“Setup file logging with rotation”””
file_config = logging_config.get(‘file_logging’, {})

```
# Main application log
main_log_file = log_dir / 'smartarb.log'
max_file_size = file_config.get('max_file_size_mb', 50) * 1024 * 1024  # Convert to bytes
backup_count = file_config.get('backup_count', 5)

# Create rotating file handler
file_handler = logging.handlers.RotatingFileHandler(
    main_log_file,
    maxBytes=max_file_size,
    backupCount=backup_count,
    encoding='utf-8'
)

# File formatter (JSON for structured logging)
file_formatter = StructuredFileFormatter()
file_handler.setFormatter(file_formatter)

# Add to root logger
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)

# Separate log files for different components
component_logs = {
    'trades': 'trades.log',
    'errors': 'errors.log',
    'ai': 'ai_analysis.log',
    'performance': 'performance.log'
}

for component, filename in component_logs.items():
    component_log_file = log_dir / filename
    component_handler = logging.handlers.RotatingFileHandler(
        component_log_file,
        maxBytes=max_file_size // 2,  # Smaller files for component logs
        backupCount=3,
        encoding='utf-8'
    )
    component_handler.setFormatter(file_formatter)
    
    # Create component-specific logger
    component_logger = logging.getLogger(f'smartarb.{component}')
    component_logger.addHandler(component_handler)
    component_logger.setLevel(logging.INFO)
```

class StructuredFileFormatter(logging.Formatter):
“”“Custom formatter for structured file logging”””

```
def format(self, record: logging.LogRecord) -> str:
    """Format log record as structured JSON"""
    import json
    from datetime import datetime
    
    # Extract structlog event dict if available
    if hasattr(record, 'msg') and isinstance(record.msg, dict):
        event_dict = record.msg.copy()
    else:
        event_dict = {'message': str(record.msg)}
    
    # Add standard fields
    log_entry = {
        'timestamp': datetime.fromtimestamp(record.created).isoformat(),
        'level': record.levelname,
        'logger': record.name,
        'module': record.module,
        'function': record.funcName,
        'line': record.lineno,
        **event_dict
    }
    
    # Add exception info if present
    if record.exc_info:
        log_entry['exception'] = self.formatException(record.exc_info)
    
    return json.dumps(log_entry, ensure_ascii=False, default=str)
```

def add_timestamp(logger, method_name, event_dict):
“”“Add timestamp to log events”””
from datetime import datetime
event_dict[‘timestamp’] = datetime.utcnow().isoformat() + ‘Z’
return event_dict

def add_system_info(logger, method_name, event_dict):
“”“Add system information to log events”””
import psutil
import platform

```
# Add basic system info (cached to avoid performance impact)
if not hasattr(add_system_info, '_system_info'):
    add_system_info._system_info = {
        'hostname': platform.node(),
        'platform': platform.system(),
        'python_version': platform.python_version(),
        'pid': os.getpid()
    }

event_dict.update(add_system_info._system_info)

# Add current resource usage (only for important events)
if event_dict.get('level') in ['error', 'critical'] or 'performance' in str(event_dict):
    try:
        process = psutil.Process()
        event_dict.update({
            'memory_percent': process.memory_percent(),
            'cpu_percent': process.cpu_percent(),
            'num_threads': process.num_threads()
        })
    except Exception:
        pass  # Don't let system info collection fail logging

return event_dict
```

def add_performance_metrics(logger, method_name, event_dict):
“”“Add performance metrics to log events”””
import time

```
# Add execution time for trade-related events
event_type = event_dict.get('event', '')

if 'execution' in event_type or 'trade' in event_type:
    # Try to calculate execution time if start_time is available
    start_time = event_dict.get('start_time')
    if start_time:
        event_dict['execution_time_ms'] = (time.time() - start_time) * 1000

# Add performance context
if any(keyword in str(event_dict) for keyword in ['opportunity', 'execution', 'trade']):
    event_dict['performance_context'] = True

return event_dict
```

def add_ai_metadata(logger, method_name, event_dict):
“”“Add metadata useful for AI analysis”””

```
# Tag events that are relevant for AI analysis
ai_relevant_keywords = [
    'opportunity', 'execution', 'profit', 'loss', 'error', 'failed',
    'success', 'performance', 'risk', 'arbitrage', 'trade'
]

event_str = str(event_dict).lower()
if any(keyword in event_str for keyword in ai_relevant_keywords):
    event_dict['ai_relevant'] = True
    
    # Add context for AI analysis
    if 'opportunity' in event_str:
        event_dict['ai_category'] = 'opportunity_detection'
    elif 'execution' in event_str or 'trade' in event_str:
        event_dict['ai_category'] = 'trade_execution'
    elif 'error' in event_str or 'failed' in event_str:
        event_dict['ai_category'] = 'error_analysis'
    elif 'performance' in event_str or 'profit' in event_str:
        event_dict['ai_category'] = 'performance_analysis'
    elif 'risk' in event_str:
        event_dict['ai_category'] = 'risk_management'

# Add severity for AI prioritization
level = event_dict.get('level', '').lower()
if level in ['error', 'critical']:
    event_dict['ai_priority'] = 'high'
elif level == 'warning':
    event_dict['ai_priority'] = 'medium'
else:
    event_dict['ai_priority'] = 'low'

return event_dict
```

def colored_console_renderer(logger, method_name, event_dict):
“”“Custom colored console renderer for better readability”””

```
# Extract key information
timestamp = event_dict.get('timestamp', '')
level = event_dict.get('level', '').upper()
logger_name = event_dict.get('logger', '')

# Choose colors based on log level
level_colors = {
    'DEBUG': Fore.CYAN,
    'INFO': Fore.GREEN,
    'WARNING': Fore.YELLOW,
    'ERROR': Fore.RED,
    'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT
}

level_color = level_colors.get(level, Fore.WHITE)

# Format timestamp (shorter for console)
if timestamp:
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        time_str = dt.strftime('%H:%M:%S')
    except:
        time_str = timestamp[:8]  # Fallback
else:
    time_str = ''

# Create colored output
output_parts = []

# Timestamp
if time_str:
    output_parts.append(f"{Fore.BLUE}{time_str}{Style.RESET_ALL}")

# Level
output_parts.append(f"{level_color}{level:8}{Style.RESET_ALL}")

# Logger name (shortened)
if logger_name:
    short_logger = logger_name.split('.')[-1][:12]
    output_parts.append(f"{Fore.MAGENTA}{short_logger:12}{Style.RESET_ALL}")

# Main message
main_msg = event_dict.get('event', event_dict.get('message', ''))
if main_msg:
    output_parts.append(f"{Fore.WHITE}{main_msg}{Style.RESET_ALL}")

# Add important context
context_parts = []

# Trading-specific context
for key in ['opportunity_id', 'symbol', 'exchange', 'profit', 'amount']:
    if key in event_dict:
        value = event_dict[key]
        if isinstance(value, float):
            value = f"{value:.4f}"
        context_parts.append(f"{key}={value}")

# Error context
if level in ['ERROR', 'CRITICAL'] and 'error' in event_dict:
    error_msg = str(event_dict['error'])[:100]  # Truncate long errors
    context_parts.append(f"{Fore.RED}error={error_msg}{Style.RESET_ALL}")

# Add context to output
if context_parts:
    context_str = ' '.join(context_parts)
    output_parts.append(f"{Fore.YELLOW}[{context_str}]{Style.RESET_ALL}")

return ' '.join(output_parts)
```

class PerformanceLogger:
“”“Specialized logger for performance tracking”””

```
def __init__(self):
    self.logger = structlog.get_logger('smartarb.performance')
    self._timers = {}

def start_timer(self, operation_id: str) -> None:
    """Start timing an operation"""
    import time
    self._timers[operation_id] = time.time()

def end_timer(self, operation_id: str, **context) -> None:
    """End timing and log performance"""
    import time
    start_time = self._timers.pop(operation_id, None)
    if start_time:
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        self.logger.info("performance_metric",
                       operation_id=operation_id,
                       duration_ms=duration,
                       **context)

def log_metric(self, metric_name: str, value: float, **context) -> None:
    """Log a performance metric"""
    self.logger.info("performance_metric",
                    metric_name=metric_name,
                    value=value,
                    **context)
```

class TradeLogger:
“”“Specialized logger for trade events”””

```
def __init__(self):
    self.logger = structlog.get_logger('smartarb.trades')

def log_opportunity_detected(self, opportunity_id: str, **details) -> None:
    """Log opportunity detection"""
    self.logger.info("opportunity_detected",
                    opportunity_id=opportunity_id,
                    ai_category="opportunity_detection",
                    **details)

def log_trade_execution_start(self, opportunity_id: str, **details) -> None:
    """Log start of trade execution"""
    self.logger.info("trade_execution_started",
                    opportunity_id=opportunity_id,
                    ai_category="trade_execution",
                    **details)

def log_trade_execution_complete(self, opportunity_id: str, profit: float, **details) -> None:
    """Log completion of trade execution"""
    self.logger.info("trade_execution_completed",
                    opportunity_id=opportunity_id,
                    profit=profit,
                    ai_category="trade_execution",
                    ai_priority="high" if profit > 100 else "medium",
                    **details)

def log_trade_failed(self, opportunity_id: str, error: str, **details) -> None:
    """Log failed trade execution"""
    self.logger.error("trade_execution_failed",
                     opportunity_id=opportunity_id,
                     error=error,
                     ai_category="error_analysis",
                     ai_priority="high",
                     **details)
```

class AILogger:
“”“Specialized logger for AI analysis events”””

```
def __init__(self):
    self.logger = structlog.get_logger('smartarb.ai')

def log_analysis_start(self, analysis_type: str, **context) -> None:
    """Log start of AI analysis"""
    self.logger.info("ai_analysis_started",
                    analysis_type=analysis_type,
                    ai_relevant=True,
                    **context)

def log_analysis_complete(self, analysis_type: str, recommendations_count: int, **context) -> None:
    """Log completion of AI analysis"""
    self.logger.info("ai_analysis_completed",
                    analysis_type=analysis_type,
                    recommendations_count=recommendations_count,
                    ai_relevant=True,
                    **context)

def log_recommendation(self, recommendation_type: str, confidence: float, **details) -> None:
    """Log AI recommendation"""
    priority = "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low"
    self.logger.info("ai_recommendation",
                    recommendation_type=recommendation_type,
                    confidence=confidence,
                    ai_relevant=True,
                    ai_priority=priority,
                    **details)

def log_code_update(self, update_type: str, files_modified: int, **details) -> None:
    """Log AI code update"""
    self.logger.info("ai_code_update",
                    update_type=update_type,
                    files_modified=files_modified,
                    ai_relevant=True,
                    ai_priority="high",
                    **details)
```

def get_specialized_loggers():
“”“Get all specialized loggers for easy import”””
return {
‘performance’: PerformanceLogger(),
‘trade’: TradeLogger(),
‘ai’: AILogger()
}

# Context manager for performance logging

class log_performance:
“”“Context manager for automatic performance logging”””

```
def __init__(self, operation_id: str, logger: Optional[PerformanceLogger] = None, **context):
    self.operation_id = operation_id
    self.logger = logger or PerformanceLogger()
    self.context = context

def __enter__(self):
    self.logger.start_timer(self.operation_id)
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    if exc_type:
        self.context['exception'] = str(exc_val)
    self.logger.end_timer(self.operation_id, **self.context)
```

# Decorator for automatic function performance logging

def log_function_performance(operation_id: Optional[str] = None):
“”“Decorator to automatically log function performance”””
def decorator(func):
def wrapper(*args, **kwargs):
op_id = operation_id or f”{func.**module**}.{func.**name**}”
with log_performance(op_id, function=func.**name**):
return func(*args, **kwargs)
return wrapper
return decorator