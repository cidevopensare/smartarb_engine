“””
Configuration Manager for SmartArb Engine
Complete implementation for managing configuration files and environment variables
“””

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger(**name**)

class ConfigManager:
“””
Configuration Management System

```
Features:
- YAML configuration file loading
- Environment variable substitution
- Multiple configuration file support
- Configuration validation
- Dynamic configuration updates
- Default value management
"""

def __init__(self, config_path: str = "config/settings.yaml"):
    """Initialize configuration manager"""
    self.config_path = Path(config_path)
    self.config_dir = self.config_path.parent
    
    # Main configuration
    self.config: Dict[str, Any] = {}
    
    # Exchange configurations
    self.exchanges_config: Dict[str, Any] = {}
    
    # Strategies configurations
    self.strategies_config: Dict[str, Any] = {}
    
    # Environment variables cache
    self.env_cache: Dict[str, str] = {}
    
    # Load all configurations
    self._load_configurations()
    
    logger.info("config_manager_initialized",
               config_path=str(self.config_path),
               config_dir=str(self.config_dir))

def _load_configurations(self) -> None:
    """Load all configuration files"""
    try:
        # Load main configuration
        self._load_main_config()
        
        # Load exchange configurations
        self._load_exchanges_config()
        
        # Load strategies configurations
        self._load_strategies_config()
        
        # Validate configurations
        self._validate_config()
        
        logger.info("configurations_loaded_successfully",
                   main_config_size=len(self.config),
                   exchanges_count=len(self.exchanges_config),
                   strategies_count=len(self.strategies_config))
        
    except Exception as e:
        logger.error("configuration_loading_failed", error=str(e))
        # Load default configuration as fallback
        self._load_default_config()

def _load_main_config(self) -> None:
    """Load main configuration file"""
    try:
        if not self.config_path.exists():
            logger.warning("main_config_file_not_found", path=str(self.config_path))
            self.config = self._get_default_config()
            return
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substitute environment variables
        content = self._substitute_env_vars(content)
        
        # Parse YAML
        self.config = yaml.safe_load(content) or {}
        
        logger.info("main_config_loaded", path=str(self.config_path))
        
    except Exception as e:
        logger.error("main_config_load_error", error=str(e))
        self.config = self._get_default_config()

def _load_exchanges_config(self) -> None:
    """Load exchange configurations"""
    exchanges_path = self.config_dir / "exchanges.yaml"
    
    try:
        if not exchanges_path.exists():
            logger.warning("exchanges_config_not_found", path=str(exchanges_path))
            self.exchanges_config = self._get_default_exchanges_config()
            return
        
        with open(exchanges_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substitute environment variables
        content = self._substitute_env_vars(content)
        
        # Parse YAML
        exchanges_data = yaml.safe_load(content) or {}
        
        # Extract exchanges configuration
        if 'exchanges' in exchanges_data:
            self.exchanges_config = exchanges_data['exchanges']
            
            # Add global settings to main config if present
            if 'global_settings' in exchanges_data:
                self.config['exchange_global_settings'] = exchanges_data['global_settings']
            
            # Add arbitrage settings
            if 'arbitrage_settings' in exchanges_data:
                self.config['arbitrage_settings'] = exchanges_data['arbitrage_settings']
            
        logger.info("exchanges_config_loaded", path=str(exchanges_path))
        
    except FileNotFoundError:
        logger.warning("exchanges_config_not_found", path=str(exchanges_path))
        self.exchanges_config = self._get_default_exchanges_config()
        
    except Exception as e:
        logger.error("exchanges_config_load_error", error=str(e))
        self.exchanges_config = self._get_default_exchanges_config()

def _load_strategies_config(self) -> None:
    """Load strategies configurations"""
    strategies_path = self.config_dir / "strategies.yaml"
    
    try:
        if not strategies_path.exists():
            logger.warning("strategies_config_not_found", path=str(strategies_path))
            self.strategies_config = self._get_default_strategies_config()
            return
        
        with open(strategies_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Substitute environment variables
        content = self._substitute_env_vars(content)
        
        # Parse YAML
        strategies_data = yaml.safe_load(content) or {}
        
        # Extract strategies configuration
        if 'strategies' in strategies_data:
            self.strategies_config = strategies_data['strategies']
            
            # Merge with main config strategies if present
            if 'strategies' in self.config:
                self.config['strategies'].update(self.strategies_config)
            else:
                self.config['strategies'] = self.strategies_config
        
        logger.info("strategies_config_loaded", path=str(strategies_path))
        
    except FileNotFoundError:
        logger.warning("strategies_config_not_found", path=str(strategies_path))
        self.strategies_config = self._get_default_strategies_config()
        
    except Exception as e:
        logger.error("strategies_config_load_error", error=str(e))
        self.strategies_config = self._get_default_strategies_config()

def _substitute_env_vars(self, content: str) -> str:
    """Substitute environment variables in configuration content"""
    
    def replace_env_var(match):
        var_name = match.group(1)
        default_value = match.group(2) if match.group(2) else ""
        
        # Get environment variable
        env_value = os.getenv(var_name, default_value)
        
        if not env_value and not default_value:
            logger.warning("env_var_not_found", variable=var_name)
        
        # Cache for future reference
        self.env_cache[var_name] = env_value
        
        return env_value
    
    # Pattern: ${VAR_NAME} or ${VAR_NAME:default_value}
    pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
    
    return re.sub(pattern, replace_env_var, content)

def _validate_config(self) -> None:
    """Validate configuration values"""
    errors = []
    warnings = []
    
    # Validate required sections
    required_sections = ['engine', 'trading', 'risk_management']
    for section in required_sections:
        if section not in self.config:
            errors.append(f"Missing required section: {section}")
    
    # Validate engine settings
    engine_config = self.config.get('engine', {})
    if not isinstance(engine_config.get('max_concurrent_opportunities'), int):
        errors.append("engine.max_concurrent_opportunities must be an integer")
    
    if engine_config.get('max_concurrent_opportunities', 0) <= 0:
        errors.append("engine.max_concurrent_opportunities must be greater than 0")
    
    # Validate trading settings
    trading_config = self.config.get('trading', {})
    required_trading_params = ['paper_trading', 'default_order_type']
    for param in required_trading_params:
        if param not in trading_config:
            warnings.append(f"Missing trading parameter: {param} (using default)")
    
    # Validate risk management settings
    risk_config = self.config.get('risk_management', {})
    required_risk_params = ['max_position_size', 'max_daily_loss', 'min_profit_threshold']
    for param in required_risk_params:
        if param not in risk_config:
            errors.append(f"Missing required risk parameter: {param}")
    
    # Validate numeric risk parameters
    numeric_risk_params = {
        'max_position_size': (float, 0),
        'max_daily_loss': (float, None),  # Can be negative
        'min_profit_threshold': (float, 0)
    }
    
    for param, (param_type, min_val) in numeric_risk_params.items():
        if param in risk_config:
            try:
                value = param_type(risk_config[param])
                if min_val is not None and value < min_val:
                    errors.append(f"Risk parameter {param} must be >= {min_val}")
            except (ValueError, TypeError):
                errors.append(f"Risk parameter {param} must be a valid {param_type.__name__}")
    
    # Validate database settings
    db_config = self.config.get('database', {})
    if not db_config.get('postgresql', {}) and not db_config.get('redis', {}):
        warnings.append("No database configuration found (PostgreSQL or Redis recommended)")
    
    # Validate exchange configurations
    if not self.exchanges_config:
        errors.append("No exchanges configured")
    else:
        enabled_exchanges = [name for name, config in self.exchanges_config.items() 
                           if config.get('enabled', False)]
        if len(enabled_exchanges) < 2:
            errors.append("At least 2 exchanges must be enabled for arbitrage")
    
    # Check for critical environment variables
    critical_env_vars = []
    for exchange_name, exchange_config in self.exchanges_config.items():
        if exchange_config.get('enabled', False):
            api_key = exchange_config.get('api_key', '')
            api_secret = exchange_config.get('api_secret', '')
            
            if not api_key or api_key.startswith('${'):
                critical_env_vars.append(f"{exchange_name.upper()}_API_KEY")
            if not api_secret or api_secret.startswith('${'):
                critical_env_vars.append(f"{exchange_name.upper()}_API_SECRET")
    
    if critical_env_vars:
        warnings.append(f"Missing API credentials environment variables: {', '.join(critical_env_vars)}")
    
    # Validate AI configuration
    ai_config = self.config.get('ai', {})
    if ai_config.get('enabled', False):
        claude_config = ai_config.get('claude', {})
        if not claude_config.get('api_key') or claude_config.get('api_key', '').startswith('${'):
            warnings.append("AI is enabled but CLAUDE_API_KEY environment variable is missing")
    
    # Validate notification settings
    notifications_config = self.config.get('notifications', {})
    if notifications_config.get('telegram', {}).get('enabled', False):
        telegram_config = notifications_config['telegram']
        if not telegram_config.get('bot_token') or not telegram_config.get('chat_id'):
            warnings.append("Telegram notifications enabled but bot_token or chat_id missing")
    
    # Log validation results
    if errors:
        for error in errors:
            logger.error("config_validation_error", error=error)
        raise ValueError(f"Configuration validation failed: {errors}")
    
    if warnings:
        for warning in warnings:
            logger.warning("config_validation_warning", warning=warning)
    
    logger.info("config_validation_passed", warnings_count=len(warnings))

def _get_default_config(self) -> Dict[str, Any]:
    """Get default configuration if main config file is missing"""
    return {
        'engine': {
            'max_concurrent_opportunities': 3,
            'scan_interval': 5,
            'health_check_interval': 30,
            'max_threads': 4,
            'memory_limit_mb': 3072,
            'auto_start_strategies': True,
            'auto_connect_exchanges': True,
            'validate_config_on_start': True
        },
        'trading': {
            'paper_trading': True,
            'default_order_type': 'limit',
            'order_timeout': 30,
            'max_position_size_usd': 1000,
            'min_position_size_usd': 10,
            'min_profit_threshold': 0.20,
            'target_profit_margin': 0.50,
            'max_slippage_percent': 0.10
        },
        'risk_management': {
            'max_daily_trades': 50,
            'max_daily_volume_usd': 10000,
            'max_daily_loss': -200,
            'max_position_size': 1000,
            'max_total_exposure': 5000,
            'max_open_positions': 5,
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
                'trading_pairs': [
                    'BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT', 'LINK/USDT', 'MATIC/USDT'
                ]
            }
        },
        'logging': {
            'level': 'INFO',
            'format': 'structured',
            'file_logging': {
                'enabled': True,
                'log_dir': 'logs',
                'max_file_size_mb': 50,
                'backup_count': 5
            },
            'console_logging': {
                'enabled': True,
                'colored': True
            }
        },
        'ai': {
            'enabled': False,
            'analysis': {
                'enabled': False,
                'frequency': 'daily',
                'auto_apply_safe_changes': False
            }
        }
    }

def _get_default_exchanges_config(self) -> Dict[str, Any]:
    """Get default exchange configuration"""
    return {
        'kraken': {
            'enabled': False,
            'name': 'Kraken',
            'api_key': '${KRAKEN_API_KEY:}',
            'api_secret': '${KRAKEN_API_SECRET:}',
            'sandbox': False,
            'base_url': 'https://api.kraken.com',
            'rate_limit': 15,
            'timeout': 30,
            'maker_fee': 0.0016,
            'taker_fee': 0.0026
        },
        'bybit': {
            'enabled': False,
            'name': 'Bybit',
            'api_key': '${BYBIT_API_KEY:}',
            'api_secret': '${BYBIT_API_SECRET:}',
            'sandbox': False,
            'base_url': 'https://api.bybit.com',
            'rate_limit': 120,
            'timeout': 10,
            'maker_fee': 0.001,
            'taker_fee': 0.001
        },
        'mexc': {
            'enabled': False,
            'name': 'MEXC',
            'api_key': '${MEXC_API_KEY:}',
            'api_secret': '${MEXC_API_SECRET:}',
            'sandbox': False,
            'base_url': 'https://api.mexc.com',
            'rate_limit': 20,
            'timeout': 15,
            'maker_fee': 0.002,
            'taker_fee': 0.002
        }
    }

def _get_default_strategies_config(self) -> Dict[str, Any]:
    """Get default strategies configuration"""
    return {
        'spatial_arbitrage': {
            'enabled': True,
            'priority': 1,
            'min_spread_percent': 0.20,
            'max_position_size': 1000,
            'confidence_threshold': 0.7,
            'max_slippage_percent': 0.10,
            'trading_pairs': [
                'BTC/USDT', 'ETH/USDT', 'ADA/USDT', 'DOT/USDT', 'LINK/USDT', 'MATIC/USDT'
            ],
            'preferred_pairs': [
                ['kraken', 'bybit'],
                ['bybit', 'mexc'],
                ['kraken', 'mexc']
            ],
            'scan_frequency': 5
        },
        'triangular_arbitrage': {
            'enabled': False,
            'priority': 2,
            'min_profit_percent': 0.30,
            'max_position_size': 500,
            'confidence_threshold': 0.8
        }
    }

def _load_default_config(self) -> None:
    """Load default configuration as fallback"""
    logger.warning("loading_default_configuration")
    
    self.config = self._get_default_config()
    self.exchanges_config = self._get_default_exchanges_config()
    self.strategies_config = self._get_default_strategies_config()
    
    # Merge strategies into main config
    self.config['strategies'] = self.strategies_config

# Public interface methods
def get_config(self) -> Dict[str, Any]:
    """Get the complete configuration"""
    return self.config.copy()

def get_exchange_configs(self) -> Dict[str, Any]:
    """Get exchange configurations"""
    return self.exchanges_config.copy()

def get_strategy_configs(self) -> Dict[str, Any]:
    """Get strategy configurations"""
    return self.strategies_config.copy()

def get_section(self, section_name: str, default: Any = None) -> Any:
    """Get a specific configuration section"""
    return self.config.get(section_name, default)

def get_value(self, path: str, default: Any = None) -> Any:
    """Get a configuration value using dot notation path"""
    try:
        keys = path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
        
    except Exception as e:
        logger.warning("config_path_access_failed", path=path, error=str(e))
        return default

def set_value(self, path: str, value: Any) -> bool:
    """Set a configuration value using dot notation path"""
    try:
        keys = path.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
        
        logger.info("config_value_updated", path=path, value=value)
        return True
        
    except Exception as e:
        logger.error("config_value_update_failed", path=path, error=str(e))
        return False

def update_exchange_config(self, exchange_name: str, updates: Dict[str, Any]) -> bool:
    """Update exchange configuration"""
    try:
        if exchange_name not in self.exchanges_config:
            logger.error("exchange_not_found", exchange=exchange_name)
            return False
        
        self.exchanges_config[exchange_name].update(updates)
        
        logger.info("exchange_config_updated",
                   exchange=exchange_name,
                   updates=list(updates.keys()))
        return True
        
    except Exception as e:
        logger.error("exchange_config_update_failed",
                    exchange=exchange_name,
                    error=str(e))
        return False

def update_strategy_config(self, strategy_name: str, updates: Dict[str, Any]) -> bool:
    """Update strategy configuration"""
    try:
        # Update in strategies config
        if strategy_name not in self.strategies_config:
            logger.error("strategy_not_found", strategy=strategy_name)
            return False
        
        self.strategies_config[strategy_name].update(updates)
        
        # Also update in main config if present
        if 'strategies' in self.config and strategy_name in self.config['strategies']:
            self.config['strategies'][strategy_name].update(updates)
        
        logger.info("strategy_config_updated",
                   strategy=strategy_name,
                   updates=list(updates.keys()))
        return True
        
    except Exception as e:
        logger.error("strategy_config_update_failed",
                    strategy=strategy_name,
                    error=str(e))
        return False

def reload_configuration(self) -> bool:
    """Reload configuration from files"""
    try:
        logger.info("reloading_configuration")
        
        # Backup current config
        backup_config = self.config.copy()
        backup_exchanges = self.exchanges_config.copy()
        backup_strategies = self.strategies_config.copy()
        
        try:
            # Clear current configs
            self.config.clear()
            self.exchanges_config.clear()
            self.strategies_config.clear()
            self.env_cache.clear()
            
            # Reload all configurations
            self._load_configurations()
            
            logger.info("configuration_reloaded_successfully")
            return True
            
        except Exception as e:
            # Restore backup on failure
            self.config = backup_config
            self.exchanges_config = backup_exchanges
            self.strategies_config = backup_strategies
            
            logger.error("configuration_reload_failed_restored_backup", error=str(e))
            return False
            
    except Exception as e:
        logger.error("configuration_reload_failed", error=str(e))
        return False

def save_configuration(self, backup: bool = True) -> bool:
    """Save current configuration to files"""
    try:
        if backup:
            self._create_config_backup()
        
        # Save main configuration
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.config, f, default_flow_style=False, indent=2)
        
        # Save exchanges configuration
        exchanges_path = self.config_dir / "exchanges.yaml"
        exchanges_data = {
            'exchanges': self.exchanges_config
        }
        
        if 'exchange_global_settings' in self.config:
            exchanges_data['global_settings'] = self.config['exchange_global_settings']
        
        if 'arbitrage_settings' in self.config:
            exchanges_data['arbitrage_settings'] = self.config['arbitrage_settings']
        
        with open(exchanges_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(exchanges_data, f, default_flow_style=False, indent=2)
        
        # Save strategies configuration
        strategies_path = self.config_dir / "strategies.yaml"
        strategies_data = {
            'strategies': self.strategies_config
        }
        
        with open(strategies_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(strategies_data, f, default_flow_style=False, indent=2)
        
        logger.info("configuration_saved_successfully")
        return True
        
    except Exception as e:
        logger.error("configuration_save_failed", error=str(e))
        return False

def _create_config_backup(self) -> None:
    """Create backup of current configuration files"""
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.config_dir / "backups" / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup files if they exist
        config_files = [
            self.config_path,
            self.config_dir / "exchanges.yaml",
            self.config_dir / "strategies.yaml"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                backup_file = backup_dir / config_file.name
                backup_file.write_text(config_file.read_text(encoding='utf-8'), encoding='utf-8')
        
        logger.info("configuration_backup_created", backup_dir=str(backup_dir))
        
    except Exception as e:
        logger.warning("configuration_backup_failed", error=str(e))

def get_env_variables(self) -> Dict[str, str]:
    """Get cached environment variables"""
    return self.env_cache.copy()

def validate_api_credentials(self) -> Dict[str, bool]:
    """Validate that required API credentials are present"""
    credentials_status = {}
    
    for exchange_name, exchange_config in self.exchanges_config.items():
        if not exchange_config.get('enabled', False):
            credentials_status[exchange_name] = True  # Not enabled, so OK
            continue
        
        api_key = exchange_config.get('api_key', '')
        api_secret = exchange_config.get('api_secret', '')
        
        # Check if credentials are properly set (not template values)
        has_valid_credentials = (
            api_key and not api_key.startswith('${') and
            api_secret and not api_secret.startswith('${')
        )
        
        credentials_status[exchange_name] = has_valid_credentials
    
    return credentials_status

def get_config_summary(self) -> Dict[str, Any]:
    """Get configuration summary for status reporting"""
    return {
        'config_file': str(self.config_path),
        'config_exists': self.config_path.exists(),
        'exchanges_configured': len(self.exchanges_config),
        'exchanges_enabled': len([
            ex for ex in self.exchanges_config.values() 
            if ex.get('enabled', False)
        ]),
        'strategies_configured': len(self.strategies_config),
        'strategies_enabled': len([
            st for st in self.strategies_config.values() 
            if st.get('enabled', False)
        ]),
        'paper_trading': self.get_value('trading.paper_trading', True),
        'ai_enabled': self.get_value('ai.enabled', False),
        'environment_variables_used': len(self.env_cache),
        'credentials_status': self.validate_api_credentials()
    }
```