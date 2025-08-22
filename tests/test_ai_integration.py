"""
Tests for SmartArb Engine AI Integration
Comprehensive test suite for Claude AI system components
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal

# Import AI components
from src.ai.claude_integration import ClaudeAnalysisEngine, ClaudeRecommendation, PerformanceReport
from src.ai.analysis_scheduler import AIAnalysisScheduler
from src.ai.code_updater import CodeUpdateManager
from src.ai.dashboard import AIDashboard
from src.utils.config import ConfigManager
from src.utils.notifications import NotificationManager


@pytest.fixture
def mock_config():
    """Mock configuration manager"""
    config = {
        'ai': {
            'enabled': True,
            'claude_api_key': 'test_api_key',
            'model': 'claude-3-sonnet-20240229',
            'analysis_frequency': 'daily',
            'auto_apply_safe_changes': False,
            'scheduling': {
                'default': '0 6 * * *',
                'emergency_triggers': {
                    'low_success_rate': 60.0,
                    'high_drawdown': -100.0
                }
            }
        },
        'monitoring': {
            'telegram_alerts': False
        }
    }
    
    mock_config_manager = Mock(spec=ConfigManager)
    mock_config_manager.get.side_effect = lambda key, default=None: _get_nested_value(config, key, default)
    mock_config_manager.to_dict.return_value = config
    
    return mock_config_manager


def _get_nested_value(data, key, default=None):
    """Helper to get nested dictionary values using dot notation"""
    keys = key.split('.')
    value = data
    
    try:
        for k in keys:
            value = value[k]
        return value
    except KeyError:
        return default


@pytest.fixture
def mock_db_manager():
    """Mock database manager"""
    mock_db = AsyncMock()
    mock_db.get_session = AsyncMock()
    return mock_db


@pytest.fixture
def mock_notification_manager():
    """Mock notification manager"""
    mock_notif = Mock(spec=NotificationManager)
    mock_notif.send_notification = AsyncMock()
    return mock_notif


@pytest.fixture
def sample_performance_report():
    """Sample performance report for testing"""
    return PerformanceReport(
        period="2024-01-01 to 2024-01-07",
        total_trades=50,
        successful_trades=40,
        total_profit=125.50,
        total_fees=15.25,
        success_rate=80.0,
        profit_per_trade=2.51,
        max_drawdown=-25.0,
        sharpe_ratio=1.5,
        exchange_performance={
            'kraken': {'trades': 20, 'profit': 50.0, 'success_rate': 85.0},
            'bybit': {'trades': 30, 'profit': 75.5, 'success_rate': 77.0}
        },
        strategy_performance={
            'spatial_arbitrage': {'trades': 50, 'profit': 125.5, 'avg_profit_pct': 0.35}
        },
        risk_metrics={
            'max_drawdown': -25.0,
            'sharpe_ratio': 1.5,
            'volatility': 12.5
        },
        market_conditions={'volatility_level': 'medium', 'trend': 'sideways'},
        issues_detected=['Low profit per trade: $2.51'],
        opportunities_missed=5,
        execution_latency_avg=850.0
    )


@pytest.fixture
def sample_recommendations():
    """Sample recommendations for testing"""
    return [
        ClaudeRecommendation(
            category='risk',
            priority='high',
            title='Increase minimum profit threshold',
            description='Current threshold too low for market conditions',
            config_changes={'risk_management.min_profit_threshold': 0.25},
            expected_impact='Reduce failed trades by 15%',
            risks=['May reduce trade frequency']
        ),
        ClaudeRecommendation(
            category='technical',
            priority='medium',
            title='Optimize execution latency',
            description='Reduce API call overhead',
            code_changes=[{
                'file': 'src/core/execution_engine.py',
                'function': 'place_order',
                'change_type': 'optimize',
                'current_value': 'await asyncio.sleep(1)',
                'suggested_value': 'await asyncio.sleep(0.5)',
                'reason': 'Reduce unnecessary delay'
            }],
            expected_impact='Improve execution speed by 20%'
        )
    ]


class TestClaudeAnalysisEngine:
    """Test Claude Analysis Engine"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_config, mock_db_manager):
        """Test Claude engine initialization"""
        engine = ClaudeAnalysisEngine(mock_config, mock_db_manager)
        
        assert engine.config == mock_config
        assert engine.db_manager == mock_db_manager
        assert engine.claude_api_key == 'test_api_key'
        assert engine.model == 'claude-3-sonnet-20240229'
    
    @pytest.mark.asyncio
    async def test_generate_performance_report(self, mock_config, mock_db_manager):
        """Test performance report generation"""
        engine = ClaudeAnalysisEngine(mock_config, mock_db_manager)
        
        # Mock database session and queries
        mock_session = AsyncMock()
        mock_db_manager.get_session.return_value.__aenter__.return_value = mock_session
        
        # Mock opportunity data
        mock_opportunity = Mock()
        mock_opportunity.status = 'completed'
        mock_opportunity.actual_profit = Decimal('5.0')
        mock_opportunity.actual_fees = Decimal('0.5')
        mock_opportunity.strategy_name = 'spatial_arbitrage'
        mock_opportunity.buy_exchange.name = 'kraken'
        mock_opportunity.sell_exchange.name = 'bybit'
        mock_opportunity.execution_time_ms = 1000
        mock_opportunity.expected_profit_percentage = Decimal('0.5')
        
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_opportunity] * 10
        
        report = await engine._generate_performance_report()
        
        assert isinstance(report, PerformanceReport)
        assert report.total_trades >= 0
        assert report.success_rate >= 0
        assert isinstance(report.exchange_performance, dict)
    
    @pytest.mark.asyncio
    async def test_manual_analysis(self, mock_config, mock_db_manager):
        """Test manual analysis functionality"""
        engine = ClaudeAnalysisEngine(mock_config, mock_db_manager)
        
        # Mock Claude API response
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'content': [{'text': 'Test analysis response'}]
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await engine.get_manual_analysis("Test prompt")
            
            assert result == 'Test analysis response'
            mock_post.assert_called_once()
    
    def test_parse_claude_response(self, mock_config, mock_db_manager):
        """Test Claude response parsing"""
        engine = ClaudeAnalysisEngine(mock_config, mock_db_manager)
        
        # Mock Claude response with JSON
        response_text = '''
        Here's my analysis:
        
        ```json
        {
          "recommendations": [
            {
              "category": "risk",
              "priority": "high", 
              "title": "Test recommendation",
              "description": "Test description",
              "config_changes": {"test.param": "new_value"},
              "expected_impact": "Test impact"
            }
          ]
        }
        ```
        '''
        
        recommendations = engine._parse_claude_response(response_text)
        
        assert len(recommendations) == 1
        assert recommendations[0].category == 'risk'
        assert recommendations[0].priority == 'high'
        assert recommendations[0].title == 'Test recommendation'


class TestAnalysisScheduler:
    """Test Analysis Scheduler"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_config, mock_db_manager, mock_notification_manager):
        """Test scheduler initialization"""
        with patch('src.ai.analysis_scheduler.ClaudeAnalysisEngine'):
            scheduler = AIAnalysisScheduler(mock_config, mock_db_manager, mock_notification_manager)
            
            assert scheduler.config == mock_config
            assert scheduler.default_schedule == '0 6 * * *'
            assert not scheduler.is_running
    
    @pytest.mark.asyncio
    async def test_queue_analysis(self, mock_config, mock_db_manager, mock_notification_manager):
        """Test analysis queuing"""
        with patch('src.ai.analysis_scheduler.ClaudeAnalysisEngine'):
            scheduler = AIAnalysisScheduler(mock_config, mock_db_manager, mock_notification_manager)
            
            await scheduler.queue_analysis('test_analysis', 'high')
            
            assert scheduler.analysis_queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_emergency_triggers(self, mock_config, mock_db_manager, mock_notification_manager):
        """Test emergency trigger detection"""
        with patch('src.ai.analysis_scheduler.ClaudeAnalysisEngine'):
            scheduler = AIAnalysisScheduler(mock_config, mock_db_manager, mock_notification_manager)
            
            # Mock performance data that should trigger emergency
            with patch.object(scheduler, '_get_recent_performance_data') as mock_perf:
                mock_perf.return_value = {
                    'success_rate': 50.0,  # Below threshold of 60%
                    'drawdown': -150.0,    # Below threshold of -100
                    'avg_latency': 6000,   # Above threshold of 5000
                    'consecutive_failures': 6  # Above threshold of 5
                }
                
                should_trigger = await scheduler._check_emergency_triggers()
                assert should_trigger


class TestCodeUpdateManager:
    """Test Code Update Manager"""
    
    def test_initialization(self, mock_notification_manager):
        """Test code updater initialization"""
        updater = CodeUpdateManager(mock_notification_manager)
        
        assert updater.notification_manager == mock_notification_manager
        assert updater.backup_dir.exists()
    
    @pytest.mark.asyncio
    async def test_safety_check(self, mock_notification_manager, sample_recommendations):
        """Test code change safety validation"""
        updater = CodeUpdateManager(mock_notification_manager)
        
        # Test safe recommendation
        safe_rec = sample_recommendations[0]  # Config change only
        safety_result = await updater._safety_check(safe_rec)
        assert safety_result['safe']
        
        # Test unsafe recommendation
        unsafe_rec = ClaudeRecommendation(
            category='technical',
            priority='critical',
            title='Dangerous change',
            description='This change could break things',
            code_changes=[{
                'file': 'src/core/engine.py',  # Protected file
                'function': 'place_order',     # Protected function
                'suggested_value': 'os.system("rm -rf /")'  # Dangerous code
            }]
        )
        
        safety_result = await updater._safety_check(unsafe_rec)
        assert not safety_result['safe']
    
    def test_code_safety_validation(self, mock_notification_manager):
        """Test individual code safety checks"""
        updater = CodeUpdateManager(mock_notification_manager)
        
        # Safe code
        safe_code = "config_value = 0.25"
        assert updater._is_code_safe(safe_code)
        
        # Dangerous code
        dangerous_codes = [
            "os.system('rm -rf /')",
            "exec(user_input)",
            "eval(malicious_code)",
            "subprocess.run(['rm', '-rf', '/'])"
        ]
        
        for code in dangerous_codes:
            assert not updater._is_code_safe(code)
    
    @pytest.mark.asyncio
    async def test_backup_creation(self, mock_notification_manager):
        """Test backup creation"""
        updater = CodeUpdateManager(mock_notification_manager)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# Test file content\ntest_variable = 'value'\n")
            temp_file = Path(f.name)
        
        try:
            changes = [{'file': str(temp_file)}]
            backup_path = await updater._create_backup('test_update', changes)
            
            assert backup_path is not None
            assert backup_path.exists()
            assert (backup_path / temp_file.name).exists()
            
            # Check metadata
            metadata_file = backup_path / 'metadata.json'
            assert metadata_file.exists()
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            assert metadata['update_id'] == 'test_update'
            assert str(temp_file) in metadata['files']
        
        finally:
            # Cleanup
            temp_file.unlink(missing_ok=True)


class TestAIDashboard:
    """Test AI Dashboard"""
    
    @pytest.fixture
    def mock_components(self, mock_notification_manager):
        """Create mock AI components for dashboard testing"""
        mock_claude = Mock(spec=ClaudeAnalysisEngine)
        mock_claude.last_analysis_time = datetime.now()
        mock_claude.get_latest_recommendations.return_value = []
        mock_claude.get_analysis_history.return_value = []
        
        mock_scheduler = Mock(spec=AIAnalysisScheduler)
        mock_scheduler.get_analysis_status = AsyncMock(return_value={
            'is_running': True,
            'total_analyses': 10,
            'successful_analyses': 8,
            'success_rate': 80.0,
            'queue_size': 2,
            'last_analysis': None
        })
        
        mock_code_updater = Mock(spec=CodeUpdateManager)
        mock_code_updater.get_update_history.return_value = []
        mock_code_updater.get_available_rollbacks.return_value = []
        
        return mock_claude, mock_scheduler, mock_code_updater, mock_notification_manager
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_components):
        """Test dashboard initialization"""
        claude, scheduler, code_updater, notification_manager = mock_components
        
        dashboard = AIDashboard(claude, scheduler, code_updater, notification_manager)
        
        assert dashboard.claude_engine == claude
        assert dashboard.scheduler == scheduler
        assert dashboard.code_updater == code_updater
        assert dashboard.notification_manager == notification_manager
    
    @pytest.mark.asyncio
    async def test_dashboard_data_update(self, mock_components):
        """Test dashboard data update"""
        claude, scheduler, code_updater, notification_manager = mock_components
        
        dashboard = AIDashboard(claude, scheduler, code_updater, notification_manager)
        
        await dashboard.update_dashboard_data()
        
        dashboard_data = dashboard.get_dashboard_data()
        
        assert 'timestamp' in dashboard_data
        assert 'system_status' in dashboard_data
        assert 'analysis_stats' in dashboard_data
        assert 'recommendation_overview' in dashboard_data
    
    @pytest.mark.asyncio
    async def test_manual_analysis_request(self, mock_components):
        """Test manual analysis request through dashboard"""
        claude, scheduler, code_updater, notification_manager = mock_components
        
        dashboard = AIDashboard(claude, scheduler, code_updater, notification_manager)
        
        # Mock scheduler method
        scheduler.request_manual_analysis = AsyncMock(return_value="Analysis result")
        
        result = await dashboard.request_manual_analysis("performance", "Custom prompt")
        
        assert result == "Analysis result"
        scheduler.request_manual_analysis.assert_called_once_with("performance", "Custom prompt")


class TestIntegration:
    """Integration tests for AI system"""
    
    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self, mock_config, mock_db_manager, 
                                        mock_notification_manager, sample_recommendations):
        """Test complete analysis workflow"""
        
        # Initialize components
        with patch('src.ai.analysis_scheduler.ClaudeAnalysisEngine') as mock_claude_class:
            mock_claude_engine = Mock()
            mock_claude_engine.run_automated_analysis = AsyncMock(return_value=sample_recommendations)
            mock_claude_class.return_value = mock_claude_engine
            
            scheduler = AIAnalysisScheduler(mock_config, mock_db_manager, mock_notification_manager)
            code_updater = CodeUpdateManager(mock_notification_manager)
            
            # Queue and process analysis
            await scheduler.queue_analysis('test_analysis')
            
            # Verify queue
            assert scheduler.analysis_queue.qsize() == 1
            
            # Process code updates
            with patch.object(code_updater, '_create_backup') as mock_backup:
                with patch.object(code_updater, '_run_tests') as mock_tests:
                    mock_backup.return_value = Path('/tmp/test_backup')
                    mock_tests.return_value = True
                    
                    results = await code_updater.process_recommendations(sample_recommendations)
                    
                    assert 'total_recommendations' in results
                    assert results['total_recommendations'] == len(sample_recommendations)
    
    @pytest.mark.asyncio 
    async def test_error_handling(self, mock_config, mock_db_manager, mock_notification_manager):
        """Test error handling in AI components"""
        
        # Test Claude engine with invalid API key
        mock_config.get.side_effect = lambda key, default=None: None if 'api_key' in key else _get_nested_value({}, key, default)
        
        engine = ClaudeAnalysisEngine(mock_config, mock_db_manager)
        
        # Should handle missing API key gracefully
        recommendations = await engine.run_automated_analysis()
        assert recommendations is None or len(recommendations) == 0
    
    def test_configuration_validation(self, mock_config):
        """Test AI configuration validation"""
        
        # Test valid configuration
        assert mock_config.get('ai.enabled', False) is True
        assert mock_config.get('ai.claude_api_key') == 'test_api_key'
        
        # Test missing configuration
        assert mock_config.get('ai.nonexistent_key', 'default') == 'default'


@pytest.mark.asyncio
async def test_api_integration():
    """Test AI API endpoints (requires running server)"""
    
    # This would test the actual API endpoints
    # For now, just verify the API module imports correctly
    try:
        from src.api.ai_api import app, ai_manager
        assert app is not None
        assert ai_manager is not None
    except ImportError as e:
        pytest.skip(f"API dependencies not available: {e}")


def test_cli_integration():
    """Test AI CLI commands"""
    
    # Test CLI module imports
    try:
        from src.cli.ai_cli import cli, ai_manager
        assert cli is not None
        assert ai_manager is not None
    except ImportError as e:
        pytest.skip(f"CLI dependencies not available: {e}")


# Performance and stress tests
@pytest.mark.slow
class TestPerformance:
    """Performance tests for AI system"""
    
    @pytest.mark.asyncio
    async def test_large_recommendation_processing(self, mock_notification_manager):
        """Test processing many recommendations"""
        updater = CodeUpdateManager(mock_notification_manager)
        
        # Create many recommendations
        large_rec_list = []
        for i in range(100):
            rec = ClaudeRecommendation(
                category='technical',
                priority='low',
                title=f'Recommendation {i}',
                description=f'Description {i}',
                config_changes={f'param_{i}': f'value_{i}'}
            )
            large_rec_list.append(rec)
        
        # Process should handle large lists efficiently
        start_time = datetime.now()
        results = await updater.process_recommendations(large_rec_list)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        assert processing_time < 30  # Should process in under 30 seconds
        assert results['total_recommendations'] == 100
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis_requests(self, mock_config, mock_db_manager, mock_notification_manager):
        """Test handling concurrent analysis requests"""
        
        with patch('src.ai.analysis_scheduler.ClaudeAnalysisEngine'):
            scheduler = AIAnalysisScheduler(mock_config, mock_db_manager, mock_notification_manager)
            
            # Queue multiple analyses concurrently
            tasks = []
            for i in range(10):
                task = scheduler.queue_analysis(f'analysis_{i}', 'normal')
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Should have queued all requests
            assert scheduler.analysis_queue.qsize() == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
