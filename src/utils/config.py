"""
Configuration Manager for SmartArb Engine
Handles loading and managing configuration from various sources
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import structlog
from dotenv import load_dotenv

logger = structlog.get_logger(__name__)


class ConfigManager:
    """
    Configuration management system
    
    Features:
    - YAML configuration files
    - Environment variable substitution
    - Configuration validation
    - Hot reloading (future feature)
    - Multiple environment support
    """
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.exchanges_config: Dict[str, Any] = {}
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Load configurations
        self._load_config()
        self._load_exchanges_config()
        self._validate_config()
        
        logger.info("config_manager_initialized", 
                   config_path=str(self.config_path))
    
    def _load_config(self):
        """Load main configuration file"""
        try:
            with open(self.config_path, 'r') as file:
                config_content = file.read()
                
                # Substitute environment variables
                config_content = self._substitute_env_vars(config_content)
                
                # Parse YAML
                self.config = yaml.safe_load(config_content)
                
            logger.info("main_config_loaded", path=str(self.config_path))
            
        except FileNotFoundError:
            logger.error("config_file_not_found", path=str(self.config_path))
            self.config = self._get_default_config()
            
        except yaml.YAMLError as e:
            logger.error("config_yaml_error", error=str(e))
            raise
            
        except Exception as e:
            logger.error("config_load_error", error=str(e))
            raise
    
    def _load_exchanges_config(self):
        """Load exchanges configuration"""
        exchanges_path = self.config_path.parent / "exchanges.yaml"
        
        try:
            with open(exchanges_path, 'r') as file:
                config_content = file.read()
                
                # Substitute environment variables
                config_content = self._substitute_env_vars(config_content)
                
                # Parse YAML
                exchanges_data = yaml.safe_load(config_content)
                self.exchanges_config = exchanges_data.get('exchanges', {})
                
                # Merge exchange settings into main config
                self.config['exchanges'] = self.exchanges_config
                
                # Add global exchange settings
                if 'global_settings' in exchanges_data:
                    self.config['exchange_global_settings'] = exchanges_data['global_settings']
                
                # Add arbitrage settings
                if 'arbitrage_settings' in exchanges_data:
                    self.config['arbitrage_settings'] = exchanges_data['arbitrage_settings']
                
            logger.info("exchanges_config_loaded", path=str(exchanges_path))
            
        except FileNotFoundError:
            logger.warning("exchanges_config_not_found", path=str(exchanges_path))
            self.exchanges_config = {}
            
        except Exception as e:
            logger.error("exchanges_config_load_error", error=str(e))
            raise
    
    def _substitute_env_vars(self, content: str) -> str:
        """Substitute environment variables in configuration content"""
        import re
        
        def replace_env_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else ""
            
            # Get environment variable
            env_value = os.getenv(var_name, default_value)
            
            if not env_value and not default_value:
                logger.warning("env_var_not_found", variable=var_name)
            
            return env_value
        
        # Pattern: ${VAR_NAME} or ${VAR_NAME:default_value}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        return re.sub(pattern, replace_env_var, content)
    
    def _validate_config(self):
        """Validate configuration values"""
        errors = []
        
        # Validate required sections
        required_sections = ['engine', 'database', 'risk_management', 'trading']
        for section in required_sections:
            if section not in self.config:
                errors.append(f"Missing required section: {section}")
        
        # Validate engine settings
        engine_config = self.config.get('engine', {})
        if not isinstance(engine_config.get('max_concurrent_opportunities'), int):
            errors.append("engine.max_concurrent_opportunities must be an integer")
        
        # Validate risk management settings
        risk_config = self.config.get('risk_management', {})
        required_risk_params = ['max_position_size', 'max_daily_loss', 'min_profit_threshold']
        for param in required_risk_params:
            if param not in risk_config:
                errors.append(f"Missing required risk parameter: {param}")
        
        # Validate database settings
        db_config = self.config.get('database', {})
        if 'postgresql' not in db_config and 'redis' not in db_config:
            errors.append("At least one database (postgresql or redis) must be configured")
        
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
            logger.warning("missing_api_credentials", 
                         missing_vars=critical_env_vars)
        
        # Log validation results
        if errors:
            for error in errors:
                logger.error("config_validation_error", error=error)
            raise ValueError(f"Configuration validation failed: {errors}")
        else:
            logger.info("config_validation_passed")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if config file is missing"""
        return {
            'engine': {
                'name': 'SmartArb Engine',
                'version': '1.0.0',
                'mode': 'development',
                'log_level': 'INFO',
                'max_concurrent_opportunities': 3,
                'update_interval': 5
            },
            'database': {
                'redis': {
                    'host': 'localhost',
                    'port': 6379,
                    'db': 0
                }
            },
            'risk_management': {
                'max_position_size': 1000,
                'max_daily_loss': 200,
                'min_profit_threshold': 0.20
            },
            'trading': {
                'enabled_pairs': ['BTC/USDT', 'ETH/USDT'],
                'order_type': 'limit',
                'order_timeout': 30
            },
            'strategies': {
                'spatial_arbitrage': {
                    'enabled': True,
                    'scan_interval': 5
                }
            },
            'monitoring': {
                'telegram_alerts': False
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'database.redis.host')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., 'database.redis.host')
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set value
        config[keys[-1]] = value
    
    def get_exchange_config(self, exchange_name: str) -> Dict[str, Any]:
        """Get configuration for specific exchange"""
        return self.exchanges_config.get(exchange_name, {})
    
    def get_enabled_exchanges(self) -> List[str]:
        """Get list of enabled exchange names"""
        return [
            name for name, config in self.exchanges_config.items()
            if config.get('enabled', False)
        ]
    
    def get_trading_pairs(self) -> List[str]:
        """Get configured trading pairs"""
        return self.get('trading.enabled_pairs', [])
    
    def reload(self):
        """Reload configuration from files"""
        logger.info("reloading_configuration")
        self._load_config()
        self._load_exchanges_config()
        self._validate_config()
        logger.info("configuration_reloaded")
    
    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary"""
        return self.config.copy()
    
    def get_environment(self) -> str:
        """Get current environment (development/production)"""
        return self.get('engine.mode', 'development')
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.get_environment() == 'development'
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.get_environment() == 'production'
    
    def get_log_level(self) -> str:
        """Get configured log level"""
        return self.get('engine.log_level', 'INFO')
    
    def is_paper_trading(self) -> bool:
        """Check if paper trading is enabled"""
        return self.get('development.paper_trading', False)
