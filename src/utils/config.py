#!/usr/bin/env python3
“””
Configuration Management for SmartArb Engine
Centralized configuration loading, validation, and management
“””

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import structlog
from decimal import Decimal
import re
from dataclasses import dataclass
from datetime import datetime

logger = structlog.get_logger(**name**)

@dataclass
class ConfigValidationResult:
“”“Configuration validation result”””
valid: bool
errors: List[str]
warnings: List[str]

```
def __post_init__(self):
    if not hasattr(self, 'errors'):
        self.errors = []
    if not hasattr(self, 'warnings'):
        self.warnings = []
```

class ConfigManager:
“”“Central configuration management system”””

```
def __init__(self, config_path: str = "config/settings.yaml"):
    self.config_path = Path(config_path)
    self.config_dir = self.config_path.parent
    
    # Configuration data
    self.config = {}
    self.exchanges_config = {}
    self.strategies_config = {}
    
    # Environment variables
    self.env_vars = {}
    self._load_env_vars()
    
    # Load all configurations
    self._load_configurations()
    
    self.logger = structlog.get_logger("config_manager")

def _load_env_vars(self):
    """Load environment variables from .env file"""
    
    env_file = Path('.env')
    
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        self.env_vars[key] = value
                        # Also set in os.environ for other components
                        os.environ[key] = value
            
            self.logger.info("env_file_loaded", vars_count=len(self.env_vars))
            
        except Exception as e:
            self.logger.warning("env_file_load_failed", error=str(e))
    else:
        self.logger.info("env_file_not_found", path=str(env_file))

def _load_configurations(self):
    """Load all configuration files"""
    
    try:
        # Load main configuration
        self._load_main_config()
        
        # Load exchanges configuration
        self._load_exchanges_config()
        
        # Load strategies configuration (if separate file exists)
        self._load_strategies_config()
        
        # Merge strategies into main config if loaded separately
        if self.strategies_config:
            if 'strategies' not in self.config:
                self.config['strategies'] = {}
            self.config['strategies'].update(self.strategies_config)
        
        self.logger.info("configurations_loaded_successfully",
                       main_config_size=len(self.config),
                       exchanges_count=len(self.exchanges_config),
                       strategies_count=len(self.strategies_config))
    
    except Exception as e:
        self.logger.error("configuration_loading_failed", error=str(e))
        # Load default configuration as fallback
        self._load_default_config()

def _load_main_config(self) -> None:
    """Load main configuration file"""
    try:
        if not self.config_path.exists():
            self.logger.warning("main_config_file_not_found", path=str(self.config_path))
            self.config = self._get_default_config()
            return
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substitute environment variables
        content = self._substitute_env_vars(content)
        
        # Parse YAML
        self.config = yaml.safe_load(content) or {}
        
        self.logger.info("main_config_loaded", path=str(self.config_path))
        
    except Exception as e:
        self.logger.error("main_config_load_error", error=str(e))
        self.config = self._get_default_config()

def _load_exchanges_config(self) -> None:
    """Load exchange configurations"""
    exchanges_path = self.config_dir / "exchanges.yaml"
    
    try:
        if not exchanges_path.exists():
            self.logger.warning("exchanges_config_not_found", path=str(exchanges_path))
            self.exchanges_config = self._get_default_exchanges_config()
            return
        
        with open(exchanges_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substitute environment variables
        content = self._substitute_env_vars(content)
        
        # Parse YAML
        exchanges_data = yaml.safe_load(content) or {}
        self.exchanges_config = exchanges_data.get('exchanges', {})
        
        # Merge into main config
        if 'exchanges' not in self.config:
            self.config['exchanges'] = {}
        self.config['exchanges'].update(self.exchanges_config)
        
        self.logger.info("exchanges_config_loaded", exchanges=list(self.exchanges_config.keys()))
        
    except Exception as e:
        self.logger.error("exchanges_config_load_error", error=str(e))
        self.exchanges_config = self._get_default_exchanges_config()

def _load_strategies_config(self) -> None:
    """Load strategies configuration if separate file exists"""
    strategies_path = self.config_dir / "strategies.yaml"
    
    if not strategies_path.exists():
        # Strategies are probably in main config
        self.strategies_config = self.config.get('strategies', {})
        return
    
    try:
        with open(strategies_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substitute environment variables
        content = self._substitute_env_vars(content)
        
        # Parse YAML
        strategies_data = yaml.safe_load(content) or {}
        self.strategies_config = strategies_data.get('strategies', {})
        
        self.logger.info("strategies_config_loaded", strategies=list(self.strategies_config.keys()))
        
    except Exception as e:
        self.logger.error("strategies_config_load_error", error=str(e))
        self.strategies_config = {}

def _substitute_env_vars(self, content: str) -> str:
    """Substitute environment variables in configuration content"""
    
    # Pattern to match ${VAR_NAME} or ${VAR_NAME:default_value}
    pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
    
    def replace_var(match):
        var_name = match.group(1)
        default_value = match.group(2) if match.group(2) is not None else ''
        
        # First check our env_vars, then os.environ
        if var_name in self.env_vars:
            return self.env_vars[var_name]
        elif var_name in os.environ:
            return os.environ[var_name]
        else:
            return default_value
    
    return re.sub(pattern, replace_var, content)

def _get_default_config(self) -> Dict[str, Any]:
    """Get default configuration"""
    
    return {
        'engine': {
            'name': 'SmartArb Engine',
            'version': '1.0.0',
            'debug_mode': False,
            'environment': 'production'
        },
        'logging': {
            'log_level': 'INFO',
            'log_directory': 'logs',
            'max_file_size_mb': 50,
            'backup_count': 10,
            'console_output': True
        },
        'database': {
            'postgresql': {
                'enabled': False,
                'host': 'localhost',
                'port': 5432,
                'database': 'smartarb',
                'username': 'smartarb_user',
                'password': '',
                'min_connections': 2,
                'max_connections': 8,
                'connection_timeout': 30
            },
            'redis': {
                'enabled': False,
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'password': '',
                'connection_timeout': 5
            }
        },
        'risk_management': {
            'max_daily_loss': 50,
            'max_position_size': 1000,
            'max_risk_score': 0.8,
            'min_confidence_level': 0.7,
            'enable_stop_loss': True,
            'stop_loss_percent': -2.0,
            'emergency_stop_enabled': True,
            'circuit_breaker': {
                'enabled': True,
                'loss_threshold': -100,
                'lookback_minutes': 60,
                'cooldown_minutes': 30
            }
        },
        'strategies': {
            'spatial_arbitrage': {
                'enabled': True,
                'priority': 1,
                'min_spread_percent': 0.20,
                'max_position_size': 1000,
                'confidence_threshold': 0.7,
                'scan_frequency': 5,
                'trading_pairs': [
                    'BTC/USDT',
                    'ETH/USDT',
                    'ADA/USDT',
                    'DOT/USDT',
                    'LINK/USDT',
                    'MATIC/USDT'
                ]
            }
        },
        'ai': {
            'enabled': True,
            'claude_api_key': '',
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 4000,
            'temperature': 0.3,
            'rate_limit_per_minute': 50,
            'auto_optimization': False,
            'analysis_schedule': {
                'performance_review': '0 8 * * *',  # Daily at 8 AM
                'strategy_optimization': '0 12 * * 1',  # Weekly on Monday at noon
                'risk_assessment': '0 */4 * * *'  # Every 4 hours
            }
        },
        'notifications': {
            'telegram': {
                'enabled': False,
                'bot_token': '',
                'chat_id': ''
            },
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'to_address': ''
            },
            'webhook': {
                'enabled': False,
                'url': ''
            }
        },
        'api': {
            'rest_api': {
                'enabled': True,
                'host': '0.0.0.0',
                'port': 8000,
                'debug': False
            },
            'websocket': {
                'enabled': True,
                'port': 8001
            }
        }
    }

def _get_default_exchanges_config(self) -> Dict[str, Any]:
    """Get default exchanges configuration"""
    
    return {
        'kraken': {
            'enabled': False,
            'api_key': '',
            'api_secret': '',
            'sandbox': False,
            'timeout': 30,
            'rate_limit': 15
        },
        'bybit': {
            'enabled': False,
            'api_key': '',
            'api_secret': '',
            'sandbox': False,
            'timeout': 10,
            'rate_limit': 120
        },
        'mexc': {
            'enabled': False,
            'api_key': '',
            'api_secret': '',
            'sandbox': False,
            'timeout': 15,
            'rate_limit': 20
        }
    }

def _load_default_config(self):
    """Load default configuration as fallback"""
    
    self.config = self._get_default_config()
    self.exchanges_config = self._get_default_exchanges_config()
    
    # Merge exchanges into main config
    self.config['exchanges'] = self.exchanges_config
    
    self.logger.warning("using_default_configuration")

def get_config(self) -> Dict[str, Any]:
    """Get complete configuration"""
    return self.config.copy()

def get_exchange_config(self, exchange_name: str) -> Dict[str, Any]:
    """Get configuration for specific exchange"""
    
    exchanges = self.config.get('exchanges', {})
    exchange_config = exchanges.get(exchange_name, {})
    
    if not exchange_config:
        self.logger.warning("exchange_config_not_found", exchange=exchange_name)
    
    return exchange_config.copy()

def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
    """Get configuration for specific strategy"""
    
    strategies = self.config.get('strategies', {})
    strategy_config = strategies.get(strategy_name, {})
    
    if not strategy_config:
        self.logger.warning("strategy_config_not_found", strategy=strategy_name)
    
    return strategy_config.copy()

def get_section_config(self, section_name: str) -> Dict[str, Any]:
    """Get configuration for specific section"""
    
    section_config = self.config.get(section_name, {})
    
    if not section_config:
        self.logger.warning("section_config_not_found", section=section_name)
    
    return section_config.copy()

def validate_config(self) -> ConfigValidationResult:
    """Validate complete configuration"""
    
    errors = []
    warnings = []
    
    # Validate main configuration structure
    validation_result = self._validate_main_config()
    errors.extend(validation_result.errors)
    warnings.extend(validation_result.warnings)
    
    # Validate exchange configurations
    validation_result = self._validate_exchanges_config()
    errors.extend(validation_result.errors)
    warnings.extend(validation_result.warnings)
    
    # Validate strategy configurations
    validation_result = self._validate_strategies_config()
    errors.extend(validation_result.errors)
    warnings.extend(validation_result.warnings)
    
    # Validate AI configuration
    validation_result = self._validate_ai_config()
    errors.extend(validation_result.errors)
    warnings.extend(validation_result.warnings)
    
    # Validate risk management configuration
    validation_result = self._validate_risk_config()
    errors.extend(validation_result.errors)
    warnings.extend(validation_result.warnings)
    
    is_valid = len(errors) == 0
    
    return ConfigValidationResult(
        valid=is_valid,
        errors=errors,
        warnings=warnings
    )

def _validate_main_config(self) -> ConfigValidationResult:
    """Validate main configuration"""
    
    errors = []
    warnings = []
    
    # Check required sections
    required_sections = ['engine', 'logging', 'risk_management']
    
    for section in required_sections:
        if section not in self.config:
            errors.append(f"Missing required section: {section}")
    
    # Validate logging configuration
    logging_config = self.config.get('logging', {})
    
    log_level = logging_config.get('log_level', 'INFO')
    if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        warnings.append(f"Invalid log level: {log_level}")
    
    log_dir = logging_config.get('log_directory', 'logs')
    log_path = Path(log_dir)
    if not log_path.exists():
        try:
            log_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            warnings.append(f"Cannot create log directory {log_dir}: {str(e)}")
    
    return ConfigValidationResult(True, errors, warnings)

def _validate_exchanges_config(self) -> ConfigValidationResult:
    """Validate exchange configurations"""
    
    errors = []
    warnings = []
    
    exchanges = self.config.get('exchanges', {})
    
    if not exchanges:
        warnings.append("No exchanges configured")
        return ConfigValidationResult(True, errors, warnings)
    
    enabled_exchanges = 0
    
    for exchange_name, exchange_config in exchanges.items():
        if not isinstance(exchange_config, dict):
            errors.append(f"Invalid configuration for exchange {exchange_name}")
            continue
        
        if exchange_config.get('enabled', False):
            enabled_exchanges += 1
            
            # Check required fields for enabled exchanges
            required_fields = ['api_key', 'api_secret']
            
            for field in required_fields:
                value = exchange_config.get(field, '')
                if not value:
                    errors.append(f"Missing {field} for enabled exchange {exchange_name}")
                elif 'your_' in value.lower() or 'example' in value.lower():
                    errors.append(f"Placeholder value detected for {field} in {exchange_name}")
            
            # Validate timeout
            timeout = exchange_config.get('timeout', 30)
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                warnings.append(f"Invalid timeout for {exchange_name}: {timeout}")
            
            # Validate rate limit
            rate_limit = exchange_config.get('rate_limit', 10)
            if not isinstance(rate_limit, (int, float)) or rate_limit <= 0:
                warnings.append(f"Invalid rate limit for {exchange_name}: {rate_limit}")
    
    if enabled_exchanges == 0:
        warnings.append("No exchanges enabled")
    elif enabled_exchanges < 2:
        warnings.append("Arbitrage requires at least 2 exchanges")
    
    return ConfigValidationResult(True, errors, warnings)

def _validate_strategies_config(self) -> ConfigValidationResult:
    """Validate strategy configurations"""
    
    errors = []
    warnings = []
    
    strategies = self.config.get('strategies', {})
    
    if not strategies:
        errors.append("No strategies configured")
        return ConfigValidationResult(False, errors, warnings)
    
    enabled_strategies = 0
    
    for strategy_name, strategy_config in strategies.items():
        if not isinstance(strategy_config, dict):
            errors.append(f"Invalid configuration for strategy {strategy_name}")
            continue
        
        if strategy_config.get('enabled', False):
            enabled_strategies += 1
            
            # Validate strategy-specific parameters
            if strategy_name == 'spatial_arbitrage':
                min_spread = strategy_config.get('min_spread_percent', 0.2)
                if not isinstance(min_spread, (int, float)) or min_spread <= 0:
                    warnings.append(f"Invalid min_spread_percent for {strategy_name}: {min_spread}")
                
                max_position = strategy_config.get('max_position_size', 1000)
                if not isinstance(max_position, (int, float)) or max_position <= 0:
                    warnings.append(f"Invalid max_position_size for {strategy_name}: {max_position}")
                
                confidence = strategy_config.get('confidence_threshold', 0.7)
                if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                    warnings.append(f"Invalid confidence_threshold for {strategy_name}: {confidence}")
    
    if enabled_strategies == 0:
        warnings.append("No strategies enabled")
    
    return ConfigValidationResult(True, errors, warnings)

def _validate_ai_config(self) -> ConfigValidationResult:
    """Validate AI configuration"""
    
    errors = []
    warnings = []
    
    ai_config = self.config.get('ai', {})
    
    if ai_config.get('enabled', False):
        api_key = ai_config.get('claude_api_key', '')
        if not api_key:
            errors.append("Claude API key required when AI is enabled")
        elif 'your_' in api_key.lower() or 'example' in api_key.lower():
            errors.append("Claude API key appears to be a placeholder")
        
        model = ai_config.get('model', '')
        if model and not model.startswith('claude'):
            warnings.append(f"Unexpected AI model: {model}")
        
        rate_limit = ai_config.get('rate_limit_per_minute', 50)
        if not isinstance(rate_limit, int) or rate_limit <= 0:
            warnings.append(f"Invalid AI rate limit: {rate_limit}")
    
    return ConfigValidationResult(True, errors, warnings)

def _validate_risk_config(self) -> ConfigValidationResult:
    """Validate risk management configuration"""
    
    errors = []
    warnings = []
    
    risk_config = self.config.get('risk_management', {})
    
    max_daily_loss = risk_config.get('max_daily_loss', 50)
    if not isinstance(max_daily_loss, (int, float)) or max_daily_loss <= 0:
        warnings.append(f"Invalid max_daily_loss: {max_daily_loss}")
    
    max_position = risk_config.get('max_position_size', 1000)
    if not isinstance(max_position, (int, float)) or max_position <= 0:
        warnings.append(f"Invalid max_position_size: {max_position}")
    
    max_risk_score = risk_config.get('max_risk_score', 0.8)
    if not isinstance(max_risk_score, (int, float)) or not 0 <= max_risk_score <= 1:
        warnings.append(f"Invalid max_risk_score: {max_risk_score}")
    
    stop_loss = risk_config.get('stop_loss_percent', -2.0)
    if not isinstance(stop_loss, (int, float)) or stop_loss >= 0:
        warnings.append(f"Invalid stop_loss_percent (should be negative): {stop_loss}")
    
    # Validate circuit breaker
    circuit_breaker = risk_config.get('circuit_breaker', {})
    if circuit_breaker.get('enabled', False):
        loss_threshold = circuit_breaker.get('loss_threshold', -100)
        if not isinstance(loss_threshold, (int, float)) or loss_threshold >= 0:
            warnings.append(f"Invalid circuit breaker loss_threshold: {loss_threshold}")
    
    return ConfigValidationResult(True, errors, warnings)

def update_config(self, section: str, key: str, value: Any) -> bool:
    """Update configuration value"""
    
    try:
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        
        self.logger.info("config_updated", section=section, key=key)
        return True
        
    except Exception as e:
        self.logger.error("config_update_failed", section=section, key=key, error=str(e))
        return False

def save_config(self) -> bool:
    """Save current configuration to file"""
    
    try:
        # Create backup of current config
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix('.yaml.backup')
            self.config_path.rename(backup_path)
        
        # Save new configuration
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)
        
        self.logger.info("config_saved", path=str(self.config_path))
        return True
        
    except Exception as e:
        self.logger.error("config_save_failed", error=str(e))
        return False

def reload_config(self) -> bool:
    """Reload configuration from files"""
    
    try:
        self._load_configurations()
        self.logger.info("config_reloaded")
        return True
        
    except Exception as e:
        self.logger.error("config_reload_failed", error=str(e))
        return False

def get_env_var(self, key: str, default: str = None) -> Optional[str]:
    """Get environment variable"""
    
    return self.env_vars.get(key, os.environ.get(key, default))

def set_env_var(self, key: str, value: str) -> None:
    """Set environment variable"""
    
    self.env_vars[key] = value
    os.environ[key] = value

def get_config_summary(self) -> Dict[str, Any]:
    """Get configuration summary for debugging"""
    
    enabled_exchanges = [
        name for name, config in self.config.get('exchanges', {}).items()
        if config.get('enabled', False)
    ]
    
    enabled_strategies = [
        name for name, config in self.config.get('strategies', {}).items()
        if config.get('enabled', False)
    ]
    
    return {
        'config_path': str(self.config_path),
        'config_loaded': bool(self.config),
        'enabled_exchanges': enabled_exchanges,
        'enabled_strategies': enabled_strategies,
        'ai_enabled': self.config.get('ai', {}).get('enabled', False),
        'debug_mode': self.config.get('engine', {}).get('debug_mode', False),
        'environment': self.config.get('engine', {}).get('environment', 'unknown'),
        'last_loaded': datetime.now().isoformat()
    }
```

# CLI interface for configuration validation

def main():
“”“Command line interface for config validation”””

```
import argparse
import sys

parser = argparse.ArgumentParser(description='SmartArb Configuration Manager')
parser.add_argument('--validate', action='store_true', 
                   help='Validate configuration')
parser.add_argument('--config', '-c', default='config/settings.yaml',
                   help='Configuration file path')
parser.add_argument('--summary', action='store_true',
                   help='Show configuration summary')

args = parser.parse_args()

try:
    config_manager = ConfigManager(args.config)
    
    if args.summary:
        summary = config_manager.get_config_summary()
        print(json.dumps(summary, indent=2))
        return 0
    
    if args.validate:
        validation_result = config_manager.validate_config()
        
        if validation_result.valid:
            print("✅ Configuration is valid")
            
            if validation_result.warnings:
                print("\n⚠️  Warnings:")
                for warning in validation_result.warnings:
                    print(f"  - {warning}")
            
            return 0
        else:
            print("❌ Configuration validation failed")
            
            if validation_result.errors:
                print("\n🚫 Errors:")
                for error in validation_result.errors:
                    print(f"  - {error}")
            
            if validation_result.warnings:
                print("\n⚠️  Warnings:")
                for warning in validation_result.warnings:
                    print(f"  - {warning}")
            
            return 1
    
    # Default: show summary
    summary = config_manager.get_config_summary()
    print(json.dumps(summary, indent=2))
    return 0
    
except Exception as e:
    print(f"❌ Configuration manager failed: {str(e)}")
    return 1
```

if **name** == “**main**”:
exit(main())