#!/usr/bin/env python3
"""
SmartArb Engine - Core Trading Engine
Complete main orchestrator for the arbitrage trading system
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
    Complete orchestrator for cryptocurrency arbitrage trading
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize SmartArb Engine"""
        
        # Core attributes
        self.state = EngineState.STOPPED
        self.start_time = time.time()
        self.config_path = config_path or "config/settings.yaml"
        self.shutdown_event = asyncio.Event()
        self.emergency_stop_triggered = False
        self.is_running = False
        
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
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info("SmartArb Engine initialized")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info("Shutdown signal received", signal=signum)
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize(self) -> bool:
        """Initialize all engine components"""
        try:
            self.state = EngineState.STARTING
            logger.info("Initializing SmartArb Engine...")
            
            # 1. Initialize configuration
            if not await self._initialize_config():
                return False
            
            # 2. Initialize database
            if not await self._initialize_database():
                logger.warning("Database initialization failed - continuing")
            
            # 3. Initialize exchanges
            if not await self._initialize_exchanges():
                return False
            
            # 4. Initialize core components
            if not await self._initialize_core_components():
                return False
            
            # 5. Initialize AI components (optional)
            if not await self._initialize_ai_components():
                logger.warning("AI initialization failed - continuing without AI")
            
            # 6. Initialize monitoring
            if not await self._initialize_monitoring():
                logger.warning("Monitoring initialization failed - continuing")
            
            # 7. Initialize notifications
            if not await self._initialize_notifications():
                logger.warning("Notifications initialization failed - continuing")
            
            logger.info("SmartArb Engine initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error("Engine initialization failed", error=str(e))
            self.state = EngineState.ERROR
            return False
    
    async def _initialize_config(self) -> bool:
        """Initialize configuration manager"""
        try:
            self.config_manager = ConfigManager(self.config_path)
            await self.config_manager.load_all_configs()
            
            if not self.config_manager.validate_critical_configs():
                raise ValueError("Critical configuration validation failed")
            
            logger.info("Configuration initialized")
            return True
            
        except Exception as e:
            logger.error("Configuration initialization failed", error=str(e))
            return False
    
    async def _initialize_database(self) -> bool:
        """Initialize database manager"""
        try:
            db_config = self.config_manager.get_database_config()
            self.database_manager = DatabaseManager(db_config)
            
            await self.database_manager.initialize()
            await self.database_manager.test_connection()
            await self.database_manager.run_migrations()
            
            logger.info("Database initialized")
            return True
            
        except Exception as e:
            logger.error("Database initialization failed", error=str(e))
            return False
    
    async def _initialize_exchanges(self) -> bool:
        """Initialize exchange connections"""
        try:
            exchange_config = self.config_manager.get_exchange_config()
            self.exchange_manager = ExchangeManager(exchange_config)
            
            await self.exchange_manager.initialize()
            
            logger.info("Exchange manager initialized")
            return True
            
        except Exception as e:
            logger.error("Exchange initialization failed", error=str(e))
            return False
    
    async def _initialize_core_components(self) -> bool:
        """Initialize core trading components"""
        try:
            # Initialize strategy manager
            self.strategy_manager = StrategyManager(self.config_manager)
            await self.strategy_manager.initialize()
            
            # Initialize risk manager
            self.risk_manager = RiskManager(self.config_manager)
            await self.risk_manager.initialize()
            
            # Initialize portfolio manager
            self.portfolio_manager = PortfolioManager(self.config_manager)
            await self.portfolio_manager.initialize()
            
            logger.info("Core components initialized")
            return True
            
        except Exception as e:
            logger.error("Core components initialization failed", error=str(e))
            return False
    
    async def _initialize_ai_components(self) -> bool:
        """Initialize AI system components"""
        try:
            ai_config = self.config_manager.get_ai_config()
            
            # Initialize AI scheduler
            self.ai_scheduler = AIScheduler(ai_config)
            await self.ai_scheduler.initialize()
            
            # Initialize code updater
            self.code_updater = CodeUpdater(ai_config, self.database_manager)
            await self.code_updater.initialize()
            
            logger.info("AI components initialized")
            return True
            
        except Exception as e:
            logger.error("AI components initialization failed", error=str(e))
            return False
    
    async def _initialize_monitoring(self) -> bool:
        """Initialize monitoring service"""
        try:
            monitoring_config = self.config_manager.get_monitoring_config()
            self.monitoring_service = MonitoringService(monitoring_config)
            
            await self.monitoring_service.initialize()
            
            logger.info("Monitoring initialized")
            return True
            
        except Exception as e:
            logger.error("Monitoring initialization failed", error=str(e))
            return False
    
    async def _initialize_notifications(self) -> bool:
        """Initialize notification service"""
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
            
            logger.info("Notifications initialized")
            return True
            
        except Exception as e:
            logger.error("Notifications initialization failed", error=str(e))
            return False
    
    async def start(self) -> bool:
        """Start the trading engine"""
        try:
            if not await self.initialize():
                return False
            
            # Start all services
            await self.database_manager.start() if self.database_manager else None
            await self.exchange_manager.start() if self.exchange_manager else None
            await self.strategy_manager.start() if self.strategy_manager else None
            await self.risk_manager.start() if self.risk_manager else None
            await self.portfolio_manager.start() if self.portfolio_manager else None
            await self.ai_scheduler.start() if self.ai_scheduler else None
            await self.monitoring_service.start() if self.monitoring_service else None
            
            self.state = EngineState.RUNNING
            self.is_running = True
            
            logger.info("🚀 SmartArb Engine is running!")
            return True
            
        except Exception as e:
            logger.error("Engine start failed", error=str(e))
            self.state = EngineState.ERROR
            return False
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("⏹️  Shutting down SmartArb Engine...")
        self.is_running = False
        self.state = EngineState.STOPPING
        
        # Send shutdown notification
        if self.notification_service:
            await self.notification_service.send_notification(
                "⏹️ SmartArb Engine Stopped", 
                "Engine shut down gracefully"
            )
        
        self.state = EngineState.STOPPED
        logger.info("👋 SmartArb Engine stopped")

async def main():
    """Main entry point"""
    engine = SmartArbEngine()
    
    try:
        if not await engine.start():
            logger.error("Engine start failed")
            return 1
        
        # Keep running until shutdown
        while engine.is_running:
            await asyncio.sleep(1)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await engine.shutdown()
        return 0
        
    except Exception as e:
        logger.critical("Unexpected engine error", error=str(e))
        return 1

if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the engine
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
