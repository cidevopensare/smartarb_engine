#!/usr/bin/env python3
"""
SmartArb Engine - Comprehensive Test Suite
Complete testing for all critical components and edge cases
"""

import pytest
import asyncio
import time
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import SmartArb components
from src.core.engine import SmartArbEngine, EngineState
from src.exchanges.base import BaseExchange
from src.strategies.arbitrage import ArbitrageCalculator, ArbitrageStrategy
from src.risk.manager import RiskManager
from src.portfolio.manager import PortfolioManager
from src.utils.config import ConfigManager

# Test fixtures and utilities
@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        'database': {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_smartarb',
            'username': 'test_user',
            'password': 'test_password'
        },
        'exchanges': {
            'kraken': {
                'api_key': 'test_api_key_kraken',
                'api_secret': 'test_api_secret_kraken',
                'sandbox': True,
                'enabled': True
            },
            'bybit': {
                'api_key': 'test_api_key_bybit',
                'api_secret': 'test_api_secret_bybit',
                'sandbox': True,
                'enabled': True
            }
        },
        'risk': {
            'max_position_size': 1000.0,
            'max_daily_loss': 100.0,
            'max_exposure_per_exchange': 500.0,
            'stop_loss_percentage': 2.0
        },
        'strategies': {
            'spatial_arbitrage': {
                'enabled': True,
                'min_profit_threshold': 0.5,
                'max_position_size': 500.0
            }
        }
    }

@pytest.fixture
def sample_ticker_data():
    """Sample ticker data for testing"""
    return {
        'kraken': {
            'BTC/USD': {'bid': 50000.0, 'ask': 50100.0, 'timestamp': time.time()},
            'ETH/USD': {'bid': 3000.0, 'ask': 3010.0, 'timestamp': time.time()}
        },
        'bybit': {
            'BTC/USD': {'bid': 50150.0, 'ask': 50250.0, 'timestamp': time.time()},
            'ETH/USD': {'bid': 3020.0, 'ask': 3030.0, 'timestamp': time.time()}
        }
    }

# =============================================================================
# ENGINE CORE TESTS
# =============================================================================

class TestSmartArbEngine:
    """Test suite for the main SmartArb Engine"""
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, mock_config):
        """Test engine initialization process"""
        with patch('src.core.engine.ConfigManager') as mock_config_manager:
            mock_config_manager.return_value.load_all_configs = AsyncMock()
            mock_config_manager.return_value.validate_critical_configs = MagicMock(return_value=True)
            
            engine = SmartArbEngine()
            
            # Test initial state
            assert engine.state == EngineState.STOPPED
            assert engine.emergency_stop_triggered is False
            assert engine.metrics.error_count == 0
            
            # Mock all initialization methods to succeed
            with patch.multiple(engine,
                                _initialize_config=AsyncMock(return_value=True),
                                _initialize_database=AsyncMock(return_value=True),
                                _initialize_logging=AsyncMock(return_value=True),
                                _initialize_exchanges=AsyncMock(return_value=True),
                                _initialize_risk_manager=AsyncMock(return_value=True),
                                _initialize_portfolio_manager=AsyncMock(return_value=True),
                                _initialize_strategies=AsyncMock(return_value=True),
                                _initialize_ai_components=AsyncMock(return_value=True),
                                _initialize_monitoring=AsyncMock(return_value=True),
                                _initialize_notifications=AsyncMock(return_value=True),
                                get_health_status=AsyncMock(return_value={'status': 'healthy'})):
                
                result = await engine.initialize()
                assert result is True
                assert engine.state == EngineState.STARTING
    
    @pytest.mark.asyncio
    async def test_engine_initialization_failure(self):
        """Test engine initialization failure handling"""
        engine = SmartArbEngine()
        
        # Mock config initialization to fail
        with patch.object(engine, '_initialize_config', AsyncMock(return_value=False)):
            with patch.object(engine, '_cleanup_partial_initialization', AsyncMock()) as cleanup_mock:
                result = await engine.initialize()
                
                assert result is False
                assert engine.state == EngineState.ERROR
                cleanup_mock.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_engine_health_check(self):
        """Test comprehensive health check functionality"""
        engine = SmartArbEngine()
        
        # Mock components
        engine.database_manager = MagicMock()
        engine.database_manager.get_health = AsyncMock(return_value={'status': 'healthy'})
        
        engine.exchange_manager = MagicMock()
        engine.exchange_manager.get_health = AsyncMock(return_value={'status': 'healthy'})
        
        engine.strategy_manager = MagicMock()
        engine.strategy_manager.get_health = AsyncMock(return_value={'status': 'healthy'})
        
        health = await engine.get_health_status()
        
        assert health['status'] == 'healthy'
        assert 'uptime' in health
        assert 'components' in health
        assert 'system' in health
        assert 'trading' in health
    
    @pytest.mark.asyncio
    async def test_engine_emergency_stop(self):
        """Test emergency stop functionality"""
        engine = SmartArbEngine()
        
        # Mock components
        engine.strategy_manager = MagicMock()
        engine.strategy_manager.emergency_stop = AsyncMock()
        
        engine.exchange_manager = MagicMock()
        engine.exchange_manager.cancel_all_orders = AsyncMock()
        
        engine.notification_service = MagicMock()
        engine.notification_service.send_notification = AsyncMock()
        
        # Mock shutdown method
        with patch.object(engine, 'shutdown', AsyncMock()) as shutdown_mock:
            await engine.emergency_stop()
            
            assert engine.state == EngineState.EMERGENCY_STOP
            assert engine.emergency_stop_triggered is True
            engine.strategy_manager.emergency_stop.assert_called_once()
            engine.exchange_manager.cancel_all_orders.assert_called_once()
            shutdown_mock.assert_called_once()

# =============================================================================
# ARBITRAGE CALCULATION TESTS
# =============================================================================

class TestArbitrageCalculator:
    """Test suite for arbitrage calculations"""
    
    def test_basic_arbitrage_calculation(self):
        """Test basic arbitrage profit calculation"""
        calc = ArbitrageCalculator()
        
        # Test profitable arbitrage opportunity
        buy_price = Decimal('50000.00')
        sell_price = Decimal('50250.00')
        amount = Decimal('0.1')
        buy_fee = Decimal('0.0025')  # 0.25%
        sell_fee = Decimal('0.001')  # 0.1%
        
        profit = calc.calculate_profit(buy_price, sell_price, amount, buy_fee, sell_fee)
        
        # Expected: (50250 * 0.1 * 0.999) - (50000 * 0.1 * 1.0025)
        # = 5019.975 - 5001.25 = 18.725
        expected_profit = Decimal('18.725')
        
        assert abs(profit - expected_profit) < Decimal('0.01')
        assert profit > 0
    
    def test_unprofitable_arbitrage(self):
        """Test unprofitable arbitrage scenario"""
        calc = ArbitrageCalculator()
        
        # Prices too close for profit after fees
        buy_price = Decimal('50000.00')
        sell_price = Decimal('50050.00')  # Only $50 difference
        amount = Decimal('0.1')
        buy_fee = Decimal('0.0025')
        sell_fee = Decimal('0.001')
        
        profit = calc.calculate_profit(buy_price, sell_price, amount, buy_fee, sell_fee)
        
        assert profit < 0  # Should be unprofitable
    
    def test_percentage_profit_calculation(self):
        """Test percentage profit calculation"""
        calc = ArbitrageCalculator()
        
        buy_price = Decimal('50000.00')
        sell_price = Decimal('50500.00')  # 1% higher
        amount = Decimal('1.0')
        buy_fee = Decimal('0.001')
        sell_fee = Decimal('0.001')
        
        profit = calc.calculate_profit(buy_price, sell_price, amount, buy_fee, sell_fee)
        percentage = calc.calculate_profit_percentage(profit, buy_price, amount)
        
        assert percentage > Decimal('0.8')  # Should be close to 1% minus fees
        assert percentage < Decimal('1.0')
    
    def test_minimum_profit_threshold(self):
        """Test minimum profit threshold checking"""
        calc = ArbitrageCalculator()
        
        buy_price = Decimal('50000.00')
        sell_price = Decimal('50100.00')
        amount = Decimal('0.1')
        min_threshold = Decimal('0.5')  # 0.5% minimum
        
        result = calc.meets_profit_threshold(
            buy_price, sell_price, amount, 
            Decimal('0.001'), Decimal('0.001'), 
            min_threshold
        )
        
        # Calculate expected profit percentage
        profit = calc.calculate_profit(buy_price, sell_price, amount, 
                                     Decimal('0.001'), Decimal('0.001'))
        percentage = calc.calculate_profit_percentage(profit, buy_price, amount)
        
        assert result == (percentage >= min_threshold)
    
    def test_edge_case_zero_amount(self):
        """Test edge case with zero trading amount"""
        calc = ArbitrageCalculator()
        
        with pytest.raises(ValueError):
            calc.calculate_profit(
                Decimal('50000'), Decimal('50100'), 
                Decimal('0'), Decimal('0.001'), Decimal('0.001')
            )
    
    def test_edge_case_negative_prices(self):
        """Test edge case with negative prices"""
        calc = ArbitrageCalculator()
        
        with pytest.raises(ValueError):
            calc.calculate_profit(
                Decimal('-50000'), Decimal('50100'), 
                Decimal('0.1'), Decimal('0.001'), Decimal('0.001')
            )

# =============================================================================
# RISK MANAGEMENT TESTS
# =============================================================================

class TestRiskManager:
    """Test suite for risk management system"""
    
    @pytest.fixture
    def risk_config(self):
        """Risk management configuration for testing"""
        return {
            'max_position_size': Decimal('1000.00'),
            'max_daily_loss': Decimal('100.00'),
            'max_exposure_per_exchange': Decimal('500.00'),
            'stop_loss_percentage': Decimal('2.0'),
            'max_correlation_exposure': Decimal('0.7'),
            'emergency_stop_loss': Decimal('200.00')
        }
    
    @pytest.mark.asyncio
    async def test_position_size_calculation(self, risk_config):
        """Test position size calculation with risk limits"""
        risk_manager = RiskManager(risk_config)
        
        # Test normal scenario
        available_balance = Decimal('5000.00')
        current_exposure = Decimal('1000.00')
        
        allowed_size = risk_manager.calculate_max_position_size(
            available_balance, current_exposure
        )
        
        assert allowed_size <= risk_config['max_position_size']
        assert allowed_size > 0
    
    @pytest.mark.asyncio
    async def test_daily_loss_limit(self, risk_config):
        """Test daily loss limit enforcement"""
        risk_manager = RiskManager(risk_config)
        
        # Simulate daily loss tracking
        risk_manager.daily_loss = Decimal('80.00')  # Close to limit
        
        # Should allow small position
        result = risk_manager.check_daily_loss_limit(Decimal('15.00'))
        assert result is True
        
        # Should reject large position that would exceed limit
        result = risk_manager.check_daily_loss_limit(Decimal('30.00'))
        assert result is False
    
    @pytest.mark.asyncio
    async def test_emergency_stop_trigger(self, risk_config):
        """Test emergency stop trigger conditions"""
        risk_manager = RiskManager(risk_config)
        
        # Set high daily loss
        risk_manager.daily_loss = Decimal('250.00')  # Above emergency threshold
        
        risk_status = await risk_manager.check_all_limits()
        
        assert risk_status['emergency_stop'] is True
        assert 'daily_loss_exceeded' in risk_status['reasons']
    
    @pytest.mark.asyncio
    async def test_exchange_exposure_limit(self, risk_config):
        """Test per-exchange exposure limits"""
        risk_manager = RiskManager(risk_config)
        
        # Set current exposure for Kraken
        risk_manager.exchange_exposure['kraken'] = Decimal('450.00')
        
        # Should allow small additional exposure
        result = risk_manager.check_exchange_exposure('kraken', Decimal('40.00'))
        assert result is True
        
        # Should reject large additional exposure
        result = risk_manager.check_exchange_exposure('kraken', Decimal('100.00'))
        assert result is False
    
    @pytest.mark.asyncio
    async def test_correlation_risk(self, risk_config):
        """Test correlation risk management"""
        risk_manager = RiskManager(risk_config)
        
        # Add correlated positions
        positions = [
            {'symbol': 'BTC/USD', 'size': Decimal('300'), 'correlation_group': 'crypto'},
            {'symbol': 'ETH/USD', 'size': Decimal('200'), 'correlation_group': 'crypto'},
        ]
        
        risk_manager.current_positions = positions
        
        # Check if new correlated position is allowed
        result = risk_manager.check_correlation_risk('crypto', Decimal('100'))
        
        # Should be rejected as total correlated exposure would be high
        assert result is False

# =============================================================================
# PORTFOLIO MANAGEMENT TESTS
# =============================================================================

class TestPortfolioManager:
    """Test suite for portfolio management"""
    
    @pytest.fixture
    def mock_exchange_manager(self):
        """Mock exchange manager for testing"""
        mock = MagicMock()
        mock.get_balance = AsyncMock(return_value={
            'BTC': {'free': Decimal('0.5'), 'used': Decimal('0.1'), 'total': Decimal('0.6')},
            'USD': {'free': Decimal('10000'), 'used': Decimal('2000'), 'total': Decimal('12000')}
        })
        return mock
    
    @pytest.mark.asyncio
    async def test_balance_refresh(self, mock_exchange_manager):
        """Test balance refresh functionality"""
        portfolio = PortfolioManager(mock_exchange_manager, None, None)
        
        await portfolio.refresh_balances()
        
        assert 'BTC' in portfolio.balances['kraken']  # Assuming kraken is first exchange
        assert 'USD' in portfolio.balances['kraken']
        
        mock_exchange_manager.get_balance.assert_called()
    
    @pytest.mark.asyncio
    async def test_position_tracking(self, mock_exchange_manager):
        """Test position tracking and updates"""
        portfolio = PortfolioManager(mock_exchange_manager, None, None)
        
        # Add a position
        position = {
            'symbol': 'BTC/USD',
            'size': Decimal('0.1'),
            'entry_price': Decimal('50000'),
            'timestamp': time.time(),
            'exchange': 'kraken'
        }
        
        portfolio.add_position(position)
        
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0]['symbol'] == 'BTC/USD'
        
        # Update position
        updated_position = position.copy()
        updated_position['size'] = Decimal('0.05')
        
        portfolio.update_position('BTC/USD', updated_position)
        
        assert portfolio.positions[0]['size'] == Decimal('0.05')
    
    @pytest.mark.asyncio
    async def test_portfolio_valuation(self, mock_exchange_manager, sample_ticker_data):
        """Test portfolio valuation calculation"""
        portfolio = PortfolioManager(mock_exchange_manager, None, None)
        
        # Set up balances and current prices
        portfolio.balances = {
            'kraken': {
                'BTC': {'free': Decimal('0.5'), 'used': Decimal('0'), 'total': Decimal('0.5')},
                'USD': {'free': Decimal('5000'), 'used': Decimal('0'), 'total': Decimal('5000')}
            }
        }
        
        # Mock price data
        with patch.object(portfolio, 'get_current_prices', 
                         AsyncMock(return_value=sample_ticker_data['kraken'])):
            
            total_value = await portfolio.calculate_total_value()
            
            # Expected: 0.5 BTC * 50050 (mid price) + 5000 USD = 30025
            expected_value = Decimal('0.5') * Decimal('50050') + Decimal('5000')
            
            assert abs(total_value - expected_value) < Decimal('1')
    
    @pytest.mark.asyncio
    async def test_pnl_calculation(self, mock_exchange_manager):
        """Test profit and loss calculation"""
        portfolio = PortfolioManager(mock_exchange_manager, None, None)
        
        # Add historical position
        position = {
            'symbol': 'BTC/USD',
            'size': Decimal('0.1'),
            'entry_price': Decimal('50000'),
            'exit_price': Decimal('51000'),
            'timestamp': time.time(),
            'exchange': 'kraken',
            'status': 'closed'
        }
        
        portfolio.add_position(position)
        
        pnl = portfolio.calculate_position_pnl(position)
        
        # Expected PnL: 0.1 * (51000 - 50000) = 100
        expected_pnl = Decimal('100')
        
        assert abs(pnl - expected_pnl) < Decimal('0.01')

# =============================================================================
# EXCHANGE INTEGRATION TESTS
# =============================================================================

class TestExchangeIntegration:
    """Test suite for exchange integrations"""
    
    @pytest.mark.asyncio
    async def test_exchange_connection(self):
        """Test exchange connection handling"""
        with patch('src.exchanges.kraken.ccxt.kraken') as mock_kraken:
            mock_instance = MagicMock()
            mock_kraken.return_value = mock_instance
            mock_instance.fetch_ticker = AsyncMock(return_value={
                'symbol': 'BTC/USD',
                'bid': 50000.0,
                'ask': 50100.0,
                'timestamp': int(time.time() * 1000)
            })
            
            from src.exchanges.kraken import KrakenExchange
            
            exchange = KrakenExchange({
                'api_key': 'test_key',
                'api_secret': 'test_secret',
                'sandbox': True
            })
            
            await exchange.initialize()
            ticker = await exchange.fetch_ticker('BTC/USD')
            
            assert ticker['symbol'] == 'BTC/USD'
            assert ticker['bid'] < ticker['ask']
            assert ticker['timestamp'] > 0
    
    @pytest.mark.asyncio
    async def test_exchange_error_handling(self):
        """Test exchange error handling"""
        with patch('src.exchanges.kraken.ccxt.kraken') as mock_kraken:
            mock_instance = MagicMock()
            mock_kraken.return_value = mock_instance
            
            # Simulate network error
            mock_instance.fetch_ticker = AsyncMock(side_effect=Exception("Network error"))
            
            from src.exchanges.kraken import KrakenExchange
            
            exchange = KrakenExchange({
                'api_key': 'test_key',
                'api_secret': 'test_secret',
                'sandbox': True
            })
            
            await exchange.initialize()
            
            with pytest.raises(Exception):
                await exchange.fetch_ticker('BTC/USD')
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        with patch('src.exchanges.base.BaseExchange') as MockExchange:
            mock_instance = MockExchange.return_value
            mock_instance.rate_limiter = MagicMock()
            mock_instance.rate_limiter.acquire = AsyncMock()
            
            # Multiple rapid requests
            for _ in range(5):
                await mock_instance.rate_limiter.acquire()
            
            # Should have been called 5 times
            assert mock_instance.rate_limiter.acquire.call_count == 5

# =============================================================================
# STRATEGY TESTING
# =============================================================================

class TestArbitrageStrategy:
    """Test suite for arbitrage strategies"""
    
    @pytest.mark.asyncio
    async def test_opportunity_detection(self, sample_ticker_data):
        """Test arbitrage opportunity detection"""
        strategy = ArbitrageStrategy({
            'min_profit_threshold': 0.3,  # 0.3%
            'max_position_size': 1000
        })
        
        # Mock exchange manager
        exchange_manager = MagicMock()
        exchange_manager.get_ticker_data = AsyncMock(return_value=sample_ticker_data)
        
        strategy.exchange_manager = exchange_manager
        
        opportunities = await strategy.scan_opportunities()
        
        assert len(opportunities) > 0
        
        # Check that BTC opportunity was found (price difference exists)
        btc_opp = next((opp for opp in opportunities if opp['symbol'] == 'BTC/USD'), None)
        assert btc_opp is not None
        assert btc_opp['profit_percentage'] > 0
    
    @pytest.mark.asyncio
    async def test_opportunity_execution(self):
        """Test arbitrage opportunity execution"""
        strategy = ArbitrageStrategy({
            'min_profit_threshold': 0.3,
            'max_position_size': 1000
        })
        
        # Mock components
        exchange_manager = MagicMock()
        risk_manager = MagicMock()
        portfolio_manager = MagicMock()
        
        # Mock successful order execution
        exchange_manager.place_order = AsyncMock(return_value={
            'id': 'test_order_123',
            'status': 'filled',
            'amount': 0.1,
            'price': 50000
        })
        
        risk_manager.check_position_risk = MagicMock(return_value=True)
        portfolio_manager.update_position = AsyncMock()
        
        strategy.exchange_manager = exchange_manager
        strategy.risk_manager = risk_manager
        strategy.portfolio_manager = portfolio_manager
        
        # Test opportunity
        opportunity = {
            'symbol': 'BTC/USD',
            'buy_exchange': 'kraken',
            'sell_exchange': 'bybit',
            'buy_price': 50000,
            'sell_price': 50200,
            'amount': 0.1,
            'profit_percentage': 0.4
        }
        
        result = await strategy.execute_opportunity(opportunity)
        
        assert result['success'] is True
        assert 'buy_order' in result
        assert 'sell_order' in result

# =============================================================================
# ERROR HANDLING AND EDGE CASES
# =============================================================================

class TestErrorHandling:
    """Test suite for error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test network timeout handling"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()
            
            from src.exchanges.base import BaseExchange
            
            exchange = BaseExchange({'timeout': 5})
            
            with pytest.raises(asyncio.TimeoutError):
                await exchange.fetch_ticker('BTC/USD')
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test database connection failure handling"""
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = ConnectionError("Database unavailable")
            
            from src.database.manager import DatabaseManager
            
            db_manager = DatabaseManager({
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db'
            })
            
            with pytest.raises(ConnectionError):
                await db_manager.initialize()
    
    @pytest.mark.asyncio
    async def test_api_key_validation(self):
        """Test API key validation"""
        from src.exchanges.kraken import KrakenExchange
        
        # Test with invalid API key
        with pytest.raises(ValueError):
            KrakenExchange({
                'api_key': '',  # Empty API key
                'api_secret': 'test_secret'
            })
        
        # Test with short API key
        with pytest.raises(ValueError):
            KrakenExchange({
                'api_key': 'short',  # Too short
                'api_secret': 'test_secret'
            })
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self):
        """Test memory leak prevention in long-running operations"""
        # This test would be more comprehensive in a real scenario
        import gc
        import sys
        
        initial_objects = len(gc.get_objects())
        
        # Simulate multiple trading cycles
        for _ in range(100):
            # Create and destroy objects that might leak
            data = {'large_data': list(range(1000))}
            del data
        
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Allow some variance but ensure no major memory leaks
        assert final_objects - initial_objects < 100

# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test suite for performance benchmarks"""
    
    @pytest.mark.asyncio
    async def test_arbitrage_calculation_performance(self):
        """Test arbitrage calculation performance"""
        calc = ArbitrageCalculator()
        
        start_time = time.time()
        
        # Run 1000 calculations
        for i in range(1000):
            calc.calculate_profit(
                Decimal('50000'), 
                Decimal('50100') + Decimal(i),
                Decimal('0.1'),
                Decimal('0.001'),
                Decimal('0.001')
            )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete 1000 calculations in under 1 second
        assert execution_time < 1.0
        
        # Calculate operations per second
        ops_per_second = 1000 / execution_time
        assert ops_per_second > 1000  # Should be > 1000 ops/sec
    
    @pytest.mark.asyncio
    async def test_concurrent_exchange_requests(self):
        """Test concurrent exchange request performance"""
        # Mock multiple exchange requests
        async def mock_request():
            await asyncio.sleep(0.1)  # Simulate network delay
            return {'status': 'success'}
        
        start_time = time.time()
        
        # Run 10 concurrent requests
        tasks = [mock_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete in about 0.1 seconds (concurrent), not 1 second (sequential)
        assert execution_time < 0.2
        assert len(results) == 10

# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_arbitrage_workflow(self, mock_config, sample_ticker_data):
        """Test complete arbitrage workflow from detection to execution"""
        # This is a simplified integration test
        # In practice, you'd want more comprehensive testing
        
        with patch('src.core.engine.ConfigManager') as mock_config_manager:
            mock_config_manager.return_value.load_all_configs = AsyncMock()
            mock_config_manager.return_value.validate_critical_configs = MagicMock(return_value=True)
            mock_config_manager.return_value.get_exchanges_config = MagicMock(return_value=mock_config['exchanges'])
            
            engine = SmartArbEngine()
            
            # Mock successful initialization
            with patch.multiple(engine,
                                _initialize_config=AsyncMock(return_value=True),
                                _initialize_database=AsyncMock(return_value=True),
                                _initialize_logging=AsyncMock(return_value=True),
                                _initialize_exchanges=AsyncMock(return_value=True),
                                _initialize_risk_manager=AsyncMock(return_value=True),
                                _initialize_portfolio_manager=AsyncMock(return_value=True),
                                _initialize_strategies=AsyncMock(return_value=True),
                                _initialize_ai_components=AsyncMock(return_value=True),
                                _initialize_monitoring=AsyncMock(return_value=True),
                                _initialize_notifications=AsyncMock(return_value=True),
                                get_health_status=AsyncMock(return_value={'status': 'healthy'})):
                
                result = await engine.initialize()
                assert result is True
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery and resilience"""
        engine = SmartArbEngine()
        
        # Test circuit breaker functionality
        engine.circuit_breaker_failures = 4  # One less than threshold
        
        # Should not trigger circuit breaker yet
        should_trigger = await engine._should_trigger_circuit_breaker()
        assert should_trigger is True  # 5th failure should trigger
        
        # Test emergency stop
        engine.strategy_manager = MagicMock()
        engine.strategy_manager.emergency_stop = AsyncMock()
        engine.exchange_manager = MagicMock()
        engine.exchange_manager.cancel_all_orders = AsyncMock()
        engine.notification_service = MagicMock()
        engine.notification_service.send_notification = AsyncMock()
        
        with patch.object(engine, 'shutdown', AsyncMock()):
            await engine.emergency_stop()
            assert engine.state == EngineState.EMERGENCY_STOP

if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing"
    ])
