#!/usr/bin/env python3
“””
Test Configuration Management
Tests for SmartArb Engine configuration loading and validation
“””

import pytest
import tempfile
import yaml
from pathlib import Path
import os
import sys

# Add src to path

sys.path.insert(0, str(Path(**file**).parent.parent))

from src.utils.config import ConfigManager, ConfigValidationResult

class TestConfigManager:
“”“Test configuration management functionality”””

```
def test_config_manager_initialization(self):
    """Test basic configuration manager initialization"""
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        test_config = {
            'engine': {
                'name': 'Test Engine',
                'version': '1.0.0'
            },
            'logging': {
                'log_level': 'INFO'
            }
        }
        yaml.dump(test_config, f)
        config_path = f.name
    
    try:
        # Initialize config manager
        config_manager = ConfigManager(config_path)
        
        # Check if config loaded
        config = config_manager.get_config()
        assert config is not None
        assert config['engine']['name'] == 'Test Engine'
        assert config['logging']['log_level'] == 'INFO'
        
    finally:
        # Cleanup
        os.unlink(config_path)

def test_environment_variable_substitution(self):
    """Test environment variable substitution in config"""
    
    # Set test environment variable
    os.environ['TEST_API_KEY'] = 'test_key_123'
    
    # Create config with environment variable
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
```

engine:
name: “Test Engine”
exchanges:
test:
api_key: “${TEST_API_KEY}”
fallback: “${NONEXISTENT_VAR:default_value}”
“””)
config_path = f.name

```
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.get_config()
        
        # Check substitution worked
        assert config['exchanges']['test']['api_key'] == 'test_key_123'
        assert config['exchanges']['test']['fallback'] == 'default_value'
        
    finally:
        os.unlink(config_path)
        del os.environ['TEST_API_KEY']

def test_config_validation_valid(self):
    """Test configuration validation with valid config"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        valid_config = {
            'engine': {
                'name': 'Test Engine',
                'version': '1.0.0'
            },
            'logging': {
                'log_level': 'INFO',
                'log_directory': 'logs'
            },
            'risk_management': {
                'max_daily_loss': 50,
                'max_position_size': 1000
            },
            'exchanges': {
                'test_exchange': {
                    'enabled': True,
                    'api_key': 'valid_key',
                    'api_secret': 'valid_secret'
                }
            },
            'strategies': {
                'spatial_arbitrage': {
                    'enabled': True,
                    'min_spread_percent': 0.2
                }
            }
        }
        yaml.dump(valid_config, f)
        config_path = f.name
    
    try:
        config_manager = ConfigManager(config_path)
        validation_result = config_manager.validate_config()
        
        assert isinstance(validation_result, ConfigValidationResult)
        assert validation_result.valid is True
        
    finally:
        os.unlink(config_path)

def test_config_validation_invalid(self):
    """Test configuration validation with invalid config"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        invalid_config = {
            'engine': {
                'name': 'Test Engine'
                # Missing required fields
            },
            'logging': {
                'log_level': 'INVALID_LEVEL'  # Invalid log level
            },
            'exchanges': {
                'test_exchange': {
                    'enabled': True,
                    'api_key': 'your_api_key_here',  # Placeholder value
                    'api_secret': ''  # Missing secret
                }
            }
            # Missing required sections
        }
        yaml.dump(invalid_config, f)
        config_path = f.name
    
    try:
        config_manager = ConfigManager(config_path)
        validation_result = config_manager.validate_config()
        
        assert isinstance(validation_result, ConfigValidationResult)
        assert len(validation_result.errors) > 0
        assert len(validation_result.warnings) > 0
        
    finally:
        os.unlink(config_path)

def test_exchange_config_access(self):
    """Test exchange configuration access"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config = {
            'exchanges': {
                'kraken': {
                    'enabled': True,
                    'api_key': 'kraken_key',
                    'rate_limit': 15
                },
                'bybit': {
                    'enabled': False,
                    'api_key': 'bybit_key',
                    'rate_limit': 120
                }
            }
        }
        yaml.dump(config, f)
        config_path = f.name
    
    try:
        config_manager = ConfigManager(config_path)
        
        # Test getting specific exchange config
        kraken_config = config_manager.get_exchange_config('kraken')
        assert kraken_config['enabled'] is True
        assert kraken_config['api_key'] == 'kraken_key'
        assert kraken_config['rate_limit'] == 15
        
        bybit_config = config_manager.get_exchange_config('bybit')
        assert bybit_config['enabled'] is False
        
        # Test getting non-existent exchange
        nonexistent_config = config_manager.get_exchange_config('nonexistent')
        assert nonexistent_config == {}
        
    finally:
        os.unlink(config_path)

def test_strategy_config_access(self):
    """Test strategy configuration access"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config = {
            'strategies': {
                'spatial_arbitrage': {
                    'enabled': True,
                    'min_spread_percent': 0.2,
                    'max_position_size': 1000
                },
                'triangular_arbitrage': {
                    'enabled': False,
                    'min_profit_percent': 0.15
                }
            }
        }
        yaml.dump(config, f)
        config_path = f.name
    
    try:
        config_manager = ConfigManager(config_path)
        
        # Test getting specific strategy config
        spatial_config = config_manager.get_strategy_config('spatial_arbitrage')
        assert spatial_config['enabled'] is True
        assert spatial_config['min_spread_percent'] == 0.2
        
        triangular_config = config_manager.get_strategy_config('triangular_arbitrage')
        assert triangular_config['enabled'] is False
        
        # Test getting non-existent strategy
        nonexistent_config = config_manager.get_strategy_config('nonexistent')
        assert nonexistent_config == {}
        
    finally:
        os.unlink(config_path)

def test_config_update(self):
    """Test configuration updates"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config = {
            'engine': {
                'name': 'Test Engine',
                'debug_mode': False
            }
        }
        yaml.dump(config, f)
        config_path = f.name
    
    try:
        config_manager = ConfigManager(config_path)
        
        # Update configuration
        success = config_manager.update_config('engine', 'debug_mode', True)
        assert success is True
        
        # Check if update was applied
        updated_config = config_manager.get_config()
        assert updated_config['engine']['debug_mode'] is True
        
    finally:
        os.unlink(config_path)

def test_default_config_fallback(self):
    """Test fallback to default configuration"""
    
    # Try to load non-existent config file
    config_manager = ConfigManager('nonexistent_config.yaml')
    
    # Should fall back to default config
    config = config_manager.get_config()
    assert config is not None
    assert 'engine' in config
    assert 'logging' in config
    assert 'risk_management' in config

def test_env_file_loading(self):
    """Test .env file loading"""
    
    # Create temporary .env file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("""
```

# Test environment file

TEST_VAR1=value1
TEST_VAR2=“quoted value”
TEST_VAR3=‘single quoted’

# Comment line

TEST_VAR4=value4
“””)
env_path = f.name

```
    # Temporarily move to temp directory
    original_cwd = os.getcwd()
    temp_dir = os.path.dirname(env_path)
    
    try:
        os.chdir(temp_dir)
        os.rename(env_path, os.path.join(temp_dir, '.env'))
        
        # Create config that uses env vars
        config_path = os.path.join(temp_dir, 'test_config.yaml')
        with open(config_path, 'w') as f:
            f.write("""
```

test:
var1: “${TEST_VAR1}”
var2: “${TEST_VAR2}”
var3: “${TEST_VAR3}”
“””)

```
        config_manager = ConfigManager(config_path)
        config = config_manager.get_config()
        
        assert config['test']['var1'] == 'value1'
        assert config['test']['var2'] == 'quoted value'
        assert config['test']['var3'] == 'single quoted'
        
    finally:
        os.chdir(original_cwd)
        # Cleanup
        try:
            os.unlink(os.path.join(temp_dir, '.env'))
            os.unlink(config_path)
        except:
            pass
```

if **name** == “**main**”:
pytest.main([**file**])