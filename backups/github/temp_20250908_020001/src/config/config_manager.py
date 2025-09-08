#!/usr/bin/env python3
"""
Configuration Manager for SmartArb Engine
Handles loading and validation of configuration files
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class ExchangeConfig:
    """Configuration for a single exchange"""
    enabled: bool = False
    api_key: str = ""
    api_secret: str = ""
    sandbox: bool = False
    timeout: int = 30
    rate_limit: int = 10

@dataclass
class StrategyConfig:
    """Configuration for trading strategies"""
    enabled: bool = True
    min_spread_percent: float = 0.20
    max_position_size: float = 1000.0
    scan_frequency: int = 5
    confidence_threshold: float = 0.7

@dataclass
class AppConfig:
    """Main application configuration"""
    trading_mode: str = "PAPER"
    debug_mode: bool = True
    log_level: str = "INFO"
    exchanges: Dict[str, ExchangeConfig] = field(default_factory=dict)
    strategies: Dict[str, StrategyConfig] = field(default_factory=dict)

class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.project_root = Path(__file__).parent.parent.parent
        self.config_path = config_path or self.project_root / "config"
        self.logger = logging.getLogger(__name__)
        
    async def load_config(self) -> AppConfig:
        """Load configuration from files and environment"""
        self.logger.info("📖 Loading SmartArb Engine configuration...")
        
        # Load from YAML file
        config_data = await self._load_yaml_config()
        
        # Override with environment variables
        config_data = self._apply_env_overrides(config_data)
        
        # Create configuration object
        config = self._create_config_object(config_data)
        
        # Validate configuration
        await self._validate_config(config)
        
        self.logger.info("✅ Configuration loaded successfully")
        return config
    
    async def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        settings_file = self.config_path / "settings.yaml"
        
        if not settings_file.exists():
            self.logger.warning(f"⚠️ No settings.yaml found, using defaults")
            return self._get_default_config()
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
                self.logger.info(f"📄 Loaded config from {settings_file}")
                return config_data
        except Exception as e:
            self.logger.error(f"❌ Failed to load {settings_file}: {e}")
            return self._get_default_config()
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides"""
        # Trading mode
        if trading_mode := os.getenv('TRADING_MODE'):
            config_data['trading_mode'] = trading_mode
            
        # Debug mode
        if debug_mode := os.getenv('DEBUG_MODE'):
            config_data['debug_mode'] = debug_mode.lower() == 'true'
            
        # Log level
        if log_level := os.getenv('LOG_LEVEL'):
            config_data['log_level'] = log_level
        
        # Exchange API keys
        exchanges = config_data.get('exchanges', {})
        
        # Kraken
        if 'kraken' in exchanges:
            if api_key := os.getenv('KRAKEN_API_KEY'):
                exchanges['kraken']['api_key'] = api_key
            if api_secret := os.getenv('KRAKEN_API_SECRET'):
                exchanges['kraken']['api_secret'] = api_secret
                
        # Bybit
        if 'bybit' in exchanges:
            if api_key := os.getenv('BYBIT_API_KEY'):
                exchanges['bybit']['api_key'] = api_key
            if api_secret := os.getenv('BYBIT_API_SECRET'):
                exchanges['bybit']['api_secret'] = api_secret
                
        # MEXC
        if 'mexc' in exchanges:
            if api_key := os.getenv('MEXC_API_KEY'):
                exchanges['mexc']['api_key'] = api_key
            if api_secret := os.getenv('MEXC_API_SECRET'):
                exchanges['mexc']['api_secret'] = api_secret
        
        self.logger.info("🔧 Applied environment variable overrides")
        return config_data
    
    def _create_config_object(self, config_data: Dict[str, Any]) -> AppConfig:
        """Create configuration object from data"""
        # Create exchange configs
        exchanges = {}
        for name, exchange_data in config_data.get('exchanges', {}).items():
            exchanges[name] = ExchangeConfig(
                enabled=exchange_data.get('enabled', False),
                api_key=exchange_data.get('api_key', ''),
                api_secret=exchange_data.get('api_secret', ''),
                sandbox=exchange_data.get('sandbox', False),
                timeout=exchange_data.get('timeout', 30),
                rate_limit=exchange_data.get('rate_limit', 10)
            )
        
        # Create strategy configs
        strategies = {}
        for name, strategy_data in config_data.get('strategies', {}).items():
            strategies[name] = StrategyConfig(
                enabled=strategy_data.get('enabled', True),
                min_spread_percent=strategy_data.get('min_spread_percent', 0.20),
                max_position_size=strategy_data.get('max_position_size', 1000.0),
                scan_frequency=strategy_data.get('scan_frequency', 5),
                confidence_threshold=strategy_data.get('confidence_threshold', 0.7)
            )
        
        return AppConfig(
            trading_mode=config_data.get('trading_mode', 'PAPER'),
            debug_mode=config_data.get('debug_mode', True),
            log_level=config_data.get('log_level', 'INFO'),
            exchanges=exchanges,
            strategies=strategies
        )
    
    async def _validate_config(self, config: AppConfig) -> None:
        """Validate configuration settings"""
        self.logger.info("🔍 Validating configuration...")
        
        # Check enabled exchanges
        enabled_exchanges = [name for name, ex in config.exchanges.items() if ex.enabled]
        if not enabled_exchanges:
            self.logger.warning("⚠️ No exchanges are enabled!")
        else:
            self.logger.info(f"✅ Enabled exchanges: {', '.join(enabled_exchanges)}")
        
        # Check API keys for enabled exchanges
        for name, exchange in config.exchanges.items():
            if exchange.enabled:
                if not exchange.api_key or not exchange.api_secret:
                    self.logger.warning(f"⚠️ {name.capitalize()}: Missing API keys")
                else:
                    self.logger.info(f"🔑 {name.capitalize()}: API keys configured")
        
        # Check enabled strategies
        enabled_strategies = [name for name, strat in config.strategies.items() if strat.enabled]
        if not enabled_strategies:
            self.logger.warning("⚠️ No strategies are enabled!")
        else:
            self.logger.info(f"🎯 Enabled strategies: {', '.join(enabled_strategies)}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'trading_mode': 'PAPER',
            'debug_mode': True,
            'log_level': 'INFO',
            'exchanges': {
                'kraken': {
                    'enabled': True,
                    'api_key': os.getenv('KRAKEN_API_KEY', ''),
                    'api_secret': os.getenv('KRAKEN_API_SECRET', ''),
                    'sandbox': False,
                    'timeout': 30,
                    'rate_limit': 15
                },
                'bybit': {
                    'enabled': True,
                    'api_key': os.getenv('BYBIT_API_KEY', ''),
                    'api_secret': os.getenv('BYBIT_API_SECRET', ''),
                    'sandbox': False,
                    'timeout': 10,
                    'rate_limit': 120
                },
                'mexc': {
                    'enabled': True,
                    'api_key': os.getenv('MEXC_API_KEY', ''),
                    'api_secret': os.getenv('MEXC_API_SECRET', ''),
                    'sandbox': False,
                    'timeout': 15,
                    'rate_limit': 20
                }
            },
            'strategies': {
                'spatial_arbitrage': {
                    'enabled': True,
                    'min_spread_percent': 0.20,
                    'max_position_size': 1000.0,
                    'scan_frequency': 5,
                    'confidence_threshold': 0.7
                }
            }
        }
