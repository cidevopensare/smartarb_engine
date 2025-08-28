#!/usr/bin/env python3
"""
SmartArb Engine - Core Trading Engine (FIXED VERSION)
Fixed import issues and improved error handling for production deployment
"""

import asyncio
import logging
import sys
import time
import os
import signal
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import structlog
import psutil
from pathlib import Path

# SmartArb Engine imports
from src.exchanges import ExchangeManager
from src.strategies import StrategyManager
from src.risk import RiskManager
from src.portfolio import PortfolioManager
from src.ai.scheduler import AIScheduler
from src.ai.code_updater import CodeUpdater
from src.database import DatabaseManager
from src.monitoring import MonitoringService
from src.notifications import NotificationService
from src.utils.config import ConfigManager
from src.utils.logger import setup_logger

# Setup structured logging
logger = structlog.get_logger(__name__)

class EngineState(Enum):
    """Engine state enumeration"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"

@dataclass
class EngineMetrics:
    """Engine performance metrics"""
    start_time: float
    uptime: float
    trades_executed: int
    total_profit: float
    success_rate: float
    memory_usage: float
    cpu_usage: float
    error_count: int
    last_health_check: float

class SmartArbEngine:
    """
    SmartArb Engine - Main trading engine with AI integration
    FIXED VERSION with improved error handling and imports
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize SmartArb Engine with enhanced error handling"""
        
        # Core attributes
        self.state = EngineState.STOPPED
        self.start_time = time.time()
        self.config_path = config_path or "config/settings.yaml"
        self.shutdown_event = asyncio.Event()
        self.emergency_stop_triggered = False
        
        # Components (initialized later)
        self.config_manager: Optional[ConfigManager] = None
        self.database_manager: Optional[DatabaseManager] = None
        self.exchange_manager: Optional[ExchangeManager] = None
        self.strategy_manager: Optional[StrategyManager] = None
        self.risk_manager: Optional[RiskManager] = None
        self.portfolio_manager: Optional[PortfolioManager] = None
        self.ai_scheduler: Optional[AIScheduler] = None
        self.code_updater: Optional[CodeUpdater] = None
        self.monitoring_service: Optional[MonitoringService] = None
        self.notification_service: Optional[NotificationService] = None
        
        # Metrics and monitoring
        self.metrics = EngineMetrics(
            start_time=self.start_time,
            uptime=0,
            trades_executed=0,
            total_profit=0.0,
            success_rate=0.0,
            memory_usage=0.0,
            cpu_usage=0.0,
            error_count=0,
            last_health_check=time.time()
        )
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Circuit breaker for critical operations
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_reset_time = 300  # 5 minutes
        self.last_circuit_breaker_failure = 0
        
        logger.info("SmartArb Engine initialized", 
                   config_path=self.config_path,
                   pid=os.getpid(),
                   python_version=sys.version)
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        try:
            # Handle SIGTERM (docker stop)
            signal.signal(signal.SIGTERM, self._signal_handler)
            # Handle SIGINT (Ctrl+C)
            signal.signal(signal.SIGINT, self._signal_handler)
            logger.info("Signal handlers setup completed")
        except Exception as e:
            logger.warning("Failed to setup signal handlers", error=str(e))
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received", signal=signum)
        self.shutdown_event.set()
    
    async def initialize(self) -> bool:
        """
        Initialize all engine components with comprehensive error handling
        """
        self.state = EngineState.STARTING
        
        try:
            logger.info("Starting SmartArb Engine initialization...")
            
            # 1. Initialize configuration manager
            if not await self._initialize_config():
                raise RuntimeError("Configuration initialization failed")
            
            # 2. Initialize database
            if not await self._initialize_database():
                raise RuntimeError("Database initialization failed")
            
            # 3. Initialize logging system
            if not await self._initialize_logging():
                raise RuntimeError("Logging initialization failed")
            
            # 4. Initialize exchange manager
            if not await self._initialize_exchanges():
                raise RuntimeError("Exchange initialization failed")
            
            # 5. Initialize risk manager (before strategies)
            if not await self._initialize_risk_manager():
                raise RuntimeError("Risk manager initialization failed")
            
            # 6. Initialize portfolio manager
            if not await self._initialize_portfolio_manager():
                raise RuntimeError("Portfolio manager initialization failed")
            
            # 7. Initialize strategy manager
            if not await self._initialize_strategies():
                raise RuntimeError("Strategy initialization failed")
            
            # 8. Initialize AI components
            if not await self._initialize_ai_components():
                logger.warning("AI components initialization failed - continuing without AI")
            
            # 9. Initialize monitoring
            if not await self._initialize_monitoring():
                logger.warning("Monitoring initialization failed - continuing without monitoring")
            
            # 10. Initialize notifications
            if not await self._initialize_notifications():
                logger.warning("Notifications initialization failed - continuing without notifications")
            
            # 11. Run system health check
            health_status = await self.get_health_status()
            if health_status.get('status') != 'healthy':
                raise RuntimeError(f"System health check failed: {health_status}")
            
            logger.info("SmartArb Engine initialization completed successfully",
                       components_initialized=self._get_initialized_components(),
                       initialization_time=time.time() - self.start_time)
            
            return True
            
        except Exception as e:
            logger.error("Engine initialization failed", 
                        error=str(e),
                        traceback=traceback.format_exc(),
                        initialization_time=time.time() - self.start_time)
            
            # Cleanup partial initialization
            await self._cleanup_partial_initialization()
            self.state = EngineState.ERROR
            return False
    
    async def _initialize_config(self) -> bool:
        """Initialize configuration manager"""
        try:
            self.config_manager = ConfigManager(self.config_path)
            await self.config_manager.load_all_configs()
            
            # Validate critical configurations
            if not self.config_manager.validate_critical_configs():
                raise ValueError("Critical configuration validation failed")
            
            logger.info("Configuration manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Configuration initialization failed", error=str(e))
            return False
    
    async def _initialize_database(self) -> bool:
        """Initialize database manager with connection pooling"""
        try:
            db_config = self.config_manager.get_database_config()
            self.database_manager = DatabaseManager(db_config)
            
            # Test database connection with timeout
            async with asyncio.timeout(30.0):
                await self.database_manager.initialize()
                await self.database_manager.test_connection()
            
            # Run database migrations
            await self.database_manager.run_migrations()
            
            logger.info("Database manager initialized successfully")
            return True
            
        except asyncio.TimeoutError:
            logger.error("Database initialization timeout")
            return False
        except Exception as e:
            logger.error("Database initialization failed", error=str(e))
            return False
    
    async def _initialize_logging(self) -> bool:
        """Initialize advanced logging system"""
        try:
            log_config = self.config_manager.get_logging_config()
            setup_logger(log_config)
            
            logger.info("Advanced logging system initialized")
            return True
            
        except Exception as e:
            logger.error("Logging initialization failed", error=str(e))
            return False
    
    async def _initialize_exchanges(self) -> bool:
        """Initialize exchange manager with all configured exchanges"""
        try:
            exchanges_config = self.config_manager.get_exchanges_config()
            self.exchange_manager = ExchangeManager(exchanges_config)
            
            # Initialize exchanges with timeout
            async with asyncio.timeout(60.0):
                await self.exchange_manager.initialize_all()
            
            # Test all exchange connections
            connection_results = await self.exchange_manager.test_all_connections()
            failed_exchanges = [name for name, status in connection_results.items() if not status]
            
            if len(failed_exchanges) == len(connection_results):
                raise RuntimeError("All exchange connections failed")
            
            if failed_exchanges:
                logger.warning("Some exchanges failed to connect", 
                             failed_exchanges=failed_exchanges)
            
            logger.info("Exchange manager initialized successfully",
                       active_exchanges=list(connection_results.keys()),
                       failed_exchanges=failed_exchanges)
            return True
            
        except asyncio.TimeoutError:
            logger.error("Exchange initialization timeout")
            return False
        except Exception as e:
            logger.error("Exchange initialization failed", error=str(e))
            return False
    
    async def _initialize_risk_manager(self) -> bool:
        """Initialize risk management system"""
        try:
            risk_config = self.config_manager.get_risk_config()
            self.risk_manager = RiskManager(
                config=risk_config,
                database_manager=self.database_manager
            )
            
            await self.risk_manager.initialize()
            
            logger.info("Risk manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Risk manager initialization failed", error=str(e))
            return False
    
    async def _initialize_portfolio_manager(self) -> bool:
        """Initialize portfolio management system"""
        try:
            self.portfolio_manager = PortfolioManager(
                exchange_manager=self.exchange_manager,
                database_manager=self.database_manager,
                risk_manager=self.risk_manager
            )
            
            await self.portfolio_manager.initialize()
            
            # Load current portfolio state
            await self.portfolio_manager.refresh_balances()
            
            logger.info("Portfolio manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Portfolio manager initialization failed", error=str(e))
            return False
    
    async def _initialize_strategies(self) -> bool:
        """Initialize strategy management system"""
        try:
            strategies_config = self.config_manager.get_strategies_config()
            self.strategy_manager = StrategyManager(
                config=strategies_config,
                exchange_manager=self.exchange_manager,
                risk_manager=self.risk_manager,
                portfolio_manager=self.portfolio_manager,
                database_manager=self.database_manager
            )
            
            await self.strategy_manager.initialize()
            
            # Load and validate all strategies
            loaded_strategies = await self.strategy_manager.load_strategies()
            if not loaded_strategies:
                raise RuntimeError("No strategies loaded successfully")
            
            logger.info("Strategy manager initialized successfully",
                       loaded_strategies=loaded_strategies)
            return True
            
        except Exception as e:
            logger.error("Strategy manager initialization failed", error=str(e))
            return False
    
    async def _initialize_ai_components(self) -> bool:
        """Initialize AI system components (optional)"""
        try:
            ai_config = self.config_manager.get_ai_config()
            
            if not ai_config.get('enabled', False):
                logger.info("AI system disabled in configuration")
                return True
            
            # Initialize AI scheduler
            self.ai_scheduler = AIScheduler(
                config=ai_config,
                database_manager=self.database_manager
            )
            await self.ai_scheduler.initialize()
            
            # Initialize code updater
            self.code_updater = CodeUpdater(
                config=ai_config,
                database_manager=self.database_manager
            )
            await self.code_updater.initialize()
            
            logger.info("AI components initialized successfully")
            return True
            
        except Exception as e:
            logger.error("AI components initialization failed", error=str(e))
            # AI is optional, so we don't fail the entire initialization
            return False
    
    async def _initialize_monitoring(self) -> bool:
        """Initialize monitoring and metrics system"""
        try:
            monitoring_config = self.config_manager.get_monitoring_config()
            self.monitoring_service = MonitoringService(
                config=monitoring_config,
                database_manager=self.database_manager
            )
            
            await self.monitoring_service.initialize()
            
            logger.info("Monitoring service initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Monitoring initialization failed", error=str(e))
            return False
    
    async def _initialize_notifications(self) -> bool:
        """Initialize notification system"""
        try:
            notification_config = self.config_manager.get_notification_config()
            self.notification_service = NotificationService(notification_config)
            
            await self.notification_service.initialize()
            
            # Send startup notification
            await self.notification_service.send_notification(
                "🚀 SmartArb Engine Started",
                f"Engine initialized successfully at {datetime.now().isoformat()}",
                priority="info"
            )
            
            logger.info("Notification service initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Notification initialization failed", error=str(e))
            return False
    
    async def start(self) -> bool:
        """Start the trading engine with all components"""
        try:
            if self.state != EngineState.STARTING:
                raise RuntimeError(f"Cannot start engine from state: {self.state}")
            
            logger.info("Starting SmartArb Engine components...")
            
            # Start database connections
            await self.database_manager.start()
            
            # Start exchange connections
            await self.exchange_manager.start_all()
            
            # Start strategy manager
            await self.strategy_manager.start()
            
            # Start AI components (if available)
            if self.ai_scheduler:
                await self.ai_scheduler.start()
            
            if self.code_updater:
                await self.code_updater.start()
            
            # Start monitoring
            if self.monitoring_service:
                await self.monitoring_service.start()
            
            # Update state
            self.state = EngineState.RUNNING
            self.start_time = time.time()
            
            # Start main engine loop
            asyncio.create_task(self._main_loop())
            
            # Start health check loop
            asyncio.create_task(self._health_check_loop())
            
            # Start metrics update loop
            asyncio.create_task(self._metrics_update_loop())
            
            logger.info("SmartArb Engine started successfully",
                       state=self.state.value,
                       components=self._get_initialized_components())
            
            if self.notification_service:
                await self.notification_service.send_notification(
                    "✅ SmartArb Engine Running",
                    "All components started successfully",
                    priority="info"
                )
            
            return True
            
        except Exception as e:
            logger.error("Engine start failed", error=str(e))
            self.state = EngineState.ERROR
            
            if self.notification_service:
                await self.notification_service.send_notification(
                    "❌ SmartArb Engine Start Failed",
                    f"Error: {str(e)}",
                    priority="high"
                )
            
            return False
    
    async def _main_loop(self):
        """Main engine execution loop"""
        logger.info("Main engine loop started")
        
        while self.state == EngineState.RUNNING and not self.shutdown_event.is_set():
            try:
                # Run strategy execution cycle
                await self.strategy_manager.execute_cycle()
                
                # Update portfolio state
                await self.portfolio_manager.update_positions()
                
                # Check risk limits
                risk_status = await self.risk_manager.check_all_limits()
                if risk_status.get('emergency_stop', False):
                    logger.critical("Emergency stop triggered by risk manager")
                    await self.emergency_stop()
                    break
                
                # AI analysis (if enabled)
                if self.ai_scheduler and self.ai_scheduler.should_run_analysis():
                    asyncio.create_task(self.ai_scheduler.run_analysis())
                
                # Sleep before next cycle
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error("Error in main loop", error=str(e))
                self.metrics.error_count += 1
                
                # Circuit breaker logic
                if await self._should_trigger_circuit_breaker():
                    logger.critical("Circuit breaker triggered - emergency stop")
                    await self.emergency_stop()
                    break
                
                # Continue with next cycle after brief pause
                await asyncio.sleep(5.0)
        
        logger.info("Main engine loop stopped")
    
    async def _health_check_loop(self):
        """Periodic health check loop"""
        while self.state == EngineState.RUNNING and not self.shutdown_event.is_set():
            try:
                await self._perform_health_check()
                await asyncio.sleep(30.0)  # Health check every 30 seconds
                
            except Exception as e:
                logger.error("Health check error", error=str(e))
                await asyncio.sleep(60.0)  # Longer wait on error
    
    async def _metrics_update_loop(self):
        """Periodic metrics update loop"""
        while self.state == EngineState.RUNNING and not self.shutdown_event.is_set():
            try:
                await self._update_metrics()
                await asyncio.sleep(60.0)  # Update metrics every minute
                
            except Exception as e:
                logger.error("Metrics update error", error=str(e))
                await asyncio.sleep(120.0)  # Longer wait on error
    
    async def _perform_health_check(self):
        """Perform comprehensive health check"""
        health_data = await self.get_health_status()
        self.metrics.last_health_check = time.time()
        
        # Check for critical issues
        if health_data.get('status') == 'unhealthy':
            logger.warning("Health check failed", health_data=health_data)
            
            if self.notification_service:
                await self.notification_service.send_notification(
                    "⚠️ SmartArb Engine Health Warning",
                    f"Health check failed: {health_data}",
                    priority="medium"
                )
    
    async def _update_metrics(self):
        """Update engine performance metrics"""
        try:
            # Update basic metrics
            self.metrics.uptime = time.time() - self.start_time
            
            # System metrics
            process = psutil.Process(os.getpid())
            self.metrics.memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            self.metrics.cpu_usage = process.cpu_percent()
            
            # Trading metrics (from strategy manager)
            if self.strategy_manager:
                trading_stats = await self.strategy_manager.get_trading_stats()
                self.metrics.trades_executed = trading_stats.get('total_trades', 0)
                self.metrics.total_profit = trading_stats.get('total_profit', 0.0)
                self.metrics.success_rate = trading_stats.get('success_rate', 0.0)
            
        except Exception as e:
            logger.error("Metrics update failed", error=str(e))
    
    async def _should_trigger_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be triggered"""
        current_time = time.time()
        
        # Reset failure count if enough time has passed
        if current_time - self.last_circuit_breaker_failure > self.circuit_breaker_reset_time:
            self.circuit_breaker_failures = 0
        
        # Increment failure count
        self.circuit_breaker_failures += 1
        self.last_circuit_breaker_failure = current_time
        
        return self.circuit_breaker_failures >= self.circuit_breaker_threshold
    
    async def _cleanup_partial_initialization(self):
        """Cleanup components that were partially initialized"""
        logger.info("Cleaning up partial initialization...")
        
        components = [
            self.notification_service,
            self.monitoring_service,
            self.ai_scheduler,
            self.code_updater,
            self.strategy_manager,
            self.portfolio_manager,
            self.risk_manager,
            self.exchange_manager,
            self.database_manager
        ]
        
        for component in components:
            if component:
                try:
                    if hasattr(component, 'cleanup'):
                        await component.cleanup()
                    elif hasattr(component, 'stop'):
                        await component.stop()
                except Exception as e:
                    logger.warning("Component cleanup failed", 
                                 component=component.__class__.__name__, 
                                 error=str(e))
    
    def _get_initialized_components(self) -> List[str]:
        """Get list of successfully initialized components"""
        components = []
        
        component_map = {
            'config_manager': self.config_manager,
            'database_manager': self.database_manager,
            'exchange_manager': self.exchange_manager,
            'strategy_manager': self.strategy_manager,
            'risk_manager': self.risk_manager,
            'portfolio_manager': self.portfolio_manager,
            'ai_scheduler': self.ai_scheduler,
            'code_updater': self.code_updater,
            'monitoring_service': self.monitoring_service,
            'notification_service': self.notification_service
        }
        
        for name, component in component_map.items():
            if component is not None:
                components.append(name)
        
        return components
    
    @property
    def is_running(self) -> bool:
        """Check if engine is currently running"""
        return self.state == EngineState.RUNNING
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        try:
            health = {
                'status': 'healthy',
                'timestamp': time.time(),
                'uptime': time.time() - self.start_time,
                'state': self.state.value,
                'components': {},
                'system': {
                    'memory_usage_mb': self.metrics.memory_usage,
                    'cpu_usage_percent': self.metrics.cpu_usage,
                    'python_version': sys.version,
                    'platform': sys.platform
                },
                'trading': {
                    'trades_executed': self.metrics.trades_executed,
                    'total_profit': self.metrics.total_profit,
                    'success_rate': self.metrics.success_rate,
                    'error_count': self.metrics.error_count
                }
            }
            
            # Check component health
            if self.database_manager:
                health['components']['database'] = await self.database_manager.get_health()
            
            if self.exchange_manager:
                health['components']['exchanges'] = await self.exchange_manager.get_health()
            
            if self.strategy_manager:
                health['components']['strategies'] = await self.strategy_manager.get_health()
            
            if self.risk_manager:
                health['components']['risk_manager'] = await self.risk_manager.get_health()
            
            if self.ai_scheduler:
                health['components']['ai_scheduler'] = self.ai_scheduler.get_health()
            
            # Determine overall status
            component_statuses = [comp.get('status', 'unknown') 
                                for comp in health['components'].values()]
            
            if 'critical' in component_statuses or self.state == EngineState.ERROR:
                health['status'] = 'critical'
            elif 'unhealthy' in component_statuses or self.metrics.error_count > 10:
                health['status'] = 'unhealthy'
            elif 'warning' in component_statuses:
                health['status'] = 'warning'
            
            return health
            
        except Exception as e:
            logger.error("Health status check failed", error=str(e))
            return {
                'status': 'critical',
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        try:
            metrics = {
                'engine': {
                    'state': self.state.value,
                    'uptime': self.metrics.uptime,
                    'start_time': self.metrics.start_time,
                    'error_count': self.metrics.error_count,
                    'last_health_check': self.metrics.last_health_check
                },
                'system': {
                    'memory_usage_mb': self.metrics.memory_usage,
                    'cpu_usage_percent': self.metrics.cpu_usage,
                    'python_version': sys.version,
                    'pid': os.getpid()
                },
                'trading': {
                    'trades_executed': self.metrics.trades_executed,
                    'total_profit': self.metrics.total_profit,
                    'success_rate': self.metrics.success_rate
                }
            }
            
            # Get detailed component metrics
            if self.strategy_manager:
                metrics['strategies'] = await self.strategy_manager.get_detailed_stats()
            
            if self.portfolio_manager:
                metrics['portfolio'] = await self.portfolio_manager.get_portfolio_summary()
            
            if self.ai_scheduler:
                metrics['ai'] = {
                    'scheduler': self.ai_scheduler.get_scheduler_status(),
                    'triggers': self.ai_scheduler.get_trigger_status()
                }
            
            if self.code_updater:
                metrics['code_updates'] = self.code_updater.get_update_stats()
            
            return metrics
            
        except Exception as e:
            logger.error("Detailed metrics retrieval failed", error=str(e))
            return {'error': str(e), 'timestamp': time.time()}
    
    async def shutdown(self):
        """Graceful shutdown of all components"""
        if self.state in [EngineState.STOPPING, EngineState.STOPPED]:
            logger.info("Shutdown already in progress or completed")
            return
        
        logger.info("Starting graceful shutdown...")
        self.state = EngineState.STOPPING
        
        try:
            # Set shutdown event
            self.shutdown_event.set()
            
            # Stop AI components first (non-critical)
            if self.code_updater:
                await self.code_updater.stop()
            
            if self.ai_scheduler:
                await self.ai_scheduler.stop()
            
            # Stop trading components
            if self.strategy_manager:
                await self.strategy_manager.stop()
            
            if self.portfolio_manager:
                await self.portfolio_manager.stop()
            
            # Stop exchange connections
            if self.exchange_manager:
                await self.exchange_manager.stop_all()
            
            # Stop monitoring and notifications
            if self.monitoring_service:
                await self.monitoring_service.stop()
            
            # Send shutdown notification before stopping notification service
            if self.notification_service:
                await self.notification_service.send_notification(
                    "🛑 SmartArb Engine Shutdown",
                    f"Engine shutdown completed at {datetime.now().isoformat()}",
                    priority="info"
                )
                await self.notification_service.stop()
            
            # Stop database connections last
            if self.database_manager:
                await self.database_manager.stop()
            
            self.state = EngineState.STOPPED
            logger.info("Graceful shutdown completed successfully")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
            self.state = EngineState.ERROR
            raise
    
    async def emergency_stop(self):
        """Emergency stop - immediately halt all trading operations"""
        logger.critical("EMERGENCY STOP TRIGGERED")
        self.state = EngineState.EMERGENCY_STOP
        self.emergency_stop_triggered = True
        
        try:
            # Immediately stop all trading
            if self.strategy_manager:
                await self.strategy_manager.emergency_stop()
            
            # Cancel all pending orders
            if self.exchange_manager:
                await self.exchange_manager.cancel_all_orders()
            
            # Send emergency notification
            if self.notification_service:
                await self.notification_service.send_notification(
                    "🚨 EMERGENCY STOP - SmartArb Engine",
                    f"Emergency stop triggered at {datetime.now().isoformat()}",
                    priority="critical"
                )
            
            # Continue with normal shutdown
            await self.shutdown()
            
        except Exception as e:
            logger.critical("Error during emergency stop", error=str(e))
            # Force exit if emergency stop fails
            sys.exit(1)

# Main entry point
async def main():
    """Main entry point for SmartArb Engine"""
    
    # Create and initialize engine
    engine = SmartArbEngine()
    
    try:
        # Initialize and start engine
        if not await engine.initialize():
            logger.error("Engine initialization failed")
            return 1
        
        if not await engine.start():
            logger.error("Engine start failed")
            return 1
        
        logger.info("SmartArb Engine running successfully")
        
        # Keep running until shutdown
        while engine.is_running:
            await asyncio.sleep(1)
        
        logger.info("Engine shutdown completed")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await engine.shutdown()
        return 0
        
    except Exception as e:
        logger.critical("Unexpected engine error", error=str(e))
        await engine.emergency_stop()
        return 1

if __name__ == "__main__":
    # Set up basic logging for startup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the engine
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical("Fatal error", error=str(e))
        sys.exit(1)
