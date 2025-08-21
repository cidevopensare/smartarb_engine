"""
SmartArb Engine - Core Engine
Main orchestrator for the arbitrage trading system
"""

import asyncio
import signal
import sys
from typing import Dict, List, Optional, Any
from decimal import Decimal
import structlog
import yaml
from pathlib import Path

# Import our components
from ..exchanges.base_exchange import BaseExchange
from ..exchanges.kraken import KrakenExchange
from ..exchanges.bybit import BybitExchange
from ..exchanges.mexc import MEXCExchange
from ..utils.config import ConfigManager
from ..utils.logging import setup_logging
from ..utils.notifications import NotificationManager
from .strategy_manager import StrategyManager
from .risk_manager import RiskManager
from .portfolio_manager import PortfolioManager
from .execution_engine import ExecutionEngine
from ..ai.claude_integration import ClaudeAnalysisEngine
from ..ai.analysis_scheduler import AIAnalysisScheduler
from ..ai.code_updater import CodeUpdateManager
from ..ai.dashboard import AIDashboard

logger = structlog.get_logger(__name__)


class SmartArbEngine:
    """
    Main arbitrage engine orchestrator
    
    Responsibilities:
    - Initialize and manage all components
    - Coordinate exchange connections
    - Monitor system health
    - Handle graceful shutdown
    """
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """Initialize SmartArb Engine"""
        self.config_path = config_path
        self.config = None
        self.exchanges: Dict[str, BaseExchange] = {}
        self.strategy_manager = None
        self.risk_manager = None
        self.portfolio_manager = None
        self.execution_engine = None
        self.notification_manager = None
        
        # AI System Components
        self.claude_engine = None
        self.ai_scheduler = None
        self.code_updater = None
        self.ai_dashboard = None
        
        # Engine state
        self.is_running = False
        self.is_stopping = False
        self.main_task = None
        self.health_check_task = None
        
        # Performance tracking
        self.start_time = None
        self.total_opportunities_found = 0
        self.total_trades_executed = 0
        self.total_profit = Decimal('0')
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info("shutdown_signal_received", signal=signum)
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize(self):
        """Initialize all engine components"""
        logger.info("smartarb_engine_initializing")
        
        try:
            # Load configuration
            self.config = ConfigManager(self.config_path)
            
            # Setup logging
            setup_logging(self.config.get('logging', {}))
            
            # Initialize notification system
            self.notification_manager = NotificationManager(
                self.config.get('monitoring', {})
            )
            
            # Initialize exchanges
            await self._initialize_exchanges()
            
            # Initialize core components
            self.risk_manager = RiskManager(self.config.get('risk_management', {}))
            self.portfolio_manager = PortfolioManager(self.exchanges, self.config)
            self.execution_engine = ExecutionEngine(
                self.exchanges, 
                self.risk_manager,
                self.config.get('trading', {})
            )
            self.strategy_manager = StrategyManager(
                self.exchanges,
                self.risk_manager,
                self.execution_engine,
                self.config.get('strategies', {})
            )
            
            # Initialize AI system if enabled
            if self.config.get('ai', {}).get('enabled', False):
                await self._initialize_ai_system()
            
            logger.info("smartarb_engine_initialized", 
                       exchanges=list(self.exchanges.keys()),
                       strategies=self.strategy_manager.enabled_strategies,
                       ai_enabled=bool(self.claude_engine))
            
        except Exception as e:
            logger.error("initialization_failed", error=str(e))
            raise
    
    async def _initialize_exchanges(self):
        """Initialize exchange connections"""
        exchange_configs = self.config.get('exchanges', {})
        
        # Exchange factory
        exchange_classes = {
            'kraken': KrakenExchange,
            'bybit': BybitExchange,
            'mexc': MEXCExchange
        }
        
        for exchange_name, exchange_config in exchange_configs.items():
            if not exchange_config.get('enabled', False):
                logger.info("exchange_disabled", exchange=exchange_name)
                continue
                
            if exchange_name not in exchange_classes:
                logger.warning("unknown_exchange", exchange=exchange_name)
                continue
            
            try:
                # Create exchange instance
                exchange_class = exchange_classes[exchange_name]
                exchange = exchange_class(exchange_config)
                
                # Test connection
                if await exchange.connect():
                    self.exchanges[exchange_name] = exchange
                    logger.info("exchange_connected", exchange=exchange_name)
                else:
                    logger.error("exchange_connection_failed", exchange=exchange_name)
                    
            except Exception as e:
                logger.error("exchange_initialization_failed", 
                           exchange=exchange_name, error=str(e))
        
        if not self.exchanges:
            raise RuntimeError("No exchanges could be initialized")
        
        logger.info("exchanges_initialized", count=len(self.exchanges))
    
    async def _initialize_ai_system(self):
        """Initialize AI analysis system"""
        try:
            logger.info("initializing_ai_system")
            
            # Initialize Claude Analysis Engine
            self.claude_engine = ClaudeAnalysisEngine(
                self.config, 
                self.db_manager if hasattr(self, 'db_manager') else None
            )
            
            # Initialize Code Update Manager
            self.code_updater = CodeUpdateManager(self.notification_manager)
            
            # Initialize AI Analysis Scheduler
            self.ai_scheduler = AIAnalysisScheduler(
                self.config,
                self.db_manager if hasattr(self, 'db_manager') else None,
                self.notification_manager
            )
            
            # Initialize AI Dashboard
            self.ai_dashboard = AIDashboard(
                self.claude_engine,
                self.ai_scheduler,
                self.code_updater,
                self.notification_manager
            )
            
            # Start AI scheduler
            await self.ai_scheduler.start()
            
            logger.info("ai_system_initialized")
            
            # Send AI startup notification
            await self.notification_manager.send_notification(
                "🧠 AI System Activated",
                "SmartArb Engine now includes Claude AI analysis and optimization",
                NotificationManager.NotificationLevel.INFO
            )
            
        except Exception as e:
            logger.error("ai_system_initialization_failed", error=str(e))
            # AI system is optional, continue without it
            self.claude_engine = None
            self.ai_scheduler = None
            self.code_updater = None
            self.ai_dashboard = None
    
    async def start(self):
        """Start the arbitrage engine"""
        if self.is_running:
            logger.warning("engine_already_running")
            return
        
        logger.info("smartarb_engine_starting")
        
        try:
            # Initialize if not done already
            if not self.config:
                await self.initialize()
            
            self.is_running = True
            self.start_time = asyncio.get_event_loop().time()
            
            # Send startup notification
            await self.notification_manager.send_notification(
                "🚀 SmartArb Engine Started",
                f"Engine started with {len(self.exchanges)} exchanges: {', '.join(self.exchanges.keys())}"
            )
            
            # Start main engine loop
            self.main_task = asyncio.create_task(self._main_loop())
            
            # Start health monitoring
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            # Start AI dashboard monitoring if available
            if self.ai_dashboard:
                self.ai_dashboard_task = asyncio.create_task(self.ai_dashboard.start_monitoring())
            
            # Wait for tasks to complete
            tasks = [self.main_task, self.health_check_task]
            if hasattr(self, 'ai_dashboard_task'):
                tasks.append(self.ai_dashboard_task)
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error("engine_start_failed", error=str(e))
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the arbitrage engine gracefully"""
        if self.is_stopping:
            return
            
        logger.info("smartarb_engine_stopping")
        self.is_stopping = True
        self.is_running = False
        
        try:
            # Cancel main tasks
            if self.main_task and not self.main_task.done():
                self.main_task.cancel()
                try:
                    await self.main_task
                except asyncio.CancelledError:
                    pass
            
            if self.health_check_task and not self.health_check_task.done():
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Stop AI system
            if self.ai_scheduler:
                await self.ai_scheduler.stop()
            
            if hasattr(self, 'ai_dashboard_task') and not self.ai_dashboard_task.done():
                self.ai_dashboard_task.cancel()
                try:
                    await self.ai_dashboard_task
                except asyncio.CancelledError:
                    pass
            
            # Stop strategy manager
            if self.strategy_manager:
                await self.strategy_manager.stop()
            
            # Close exchange connections
            for exchange_name, exchange in self.exchanges.items():
                try:
                    await exchange.disconnect()
                    logger.info("exchange_disconnected", exchange=exchange_name)
                except Exception as e:
                    logger.warning("exchange_disconnect_failed", 
                                 exchange=exchange_name, error=str(e))
            
            # Send shutdown notification
            runtime = asyncio.get_event_loop().time() - (self.start_time or 0)
            await self.notification_manager.send_notification(
                "🛑 SmartArb Engine Stopped",
                f"Engine stopped after {runtime:.1f}s. "
                f"Opportunities: {self.total_opportunities_found}, "
                f"Trades: {self.total_trades_executed}, "
                f"Profit: {self.total_profit} USDT"
            )
            
            logger.info("smartarb_engine_stopped",
                       runtime=runtime,
                       opportunities=self.total_opportunities_found,
                       trades=self.total_trades_executed,
                       profit=float(self.total_profit))
            
        except Exception as e:
            logger.error("engine_stop_failed", error=str(e))
    
    async def _main_loop(self):
        """Main engine loop - orchestrates all activities"""
        update_interval = self.config.get('engine', {}).get('update_interval', 5)
        
        logger.info("main_loop_started", update_interval=update_interval)
        
        while self.is_running:
            try:
                # Update portfolio balances
                await self.portfolio_manager.update_balances()
                
                # Scan for arbitrage opportunities
                opportunities = await self.strategy_manager.scan_opportunities()
                
                if opportunities:
                    self.total_opportunities_found += len(opportunities)
                    logger.info("opportunities_found", count=len(opportunities))
                    
                    # Execute opportunities (if risk management allows)
                    for opportunity in opportunities:
                        if await self.risk_manager.validate_opportunity(opportunity):
                            result = await self.execution_engine.execute_opportunity(opportunity)
                            
                            if result and result.get('success'):
                                self.total_trades_executed += 1
                                profit = result.get('profit', Decimal('0'))
                                self.total_profit += profit
                                
                                logger.info("opportunity_executed",
                                          symbol=opportunity.symbol,
                                          profit=float(profit))
                                
                                # Send profitable trade notification
                                if profit > Decimal('0'):
                                    await self.notification_manager.send_notification(
                                        f"💰 Profitable Trade: {opportunity.symbol}",
                                        f"Profit: {profit} USDT"
                                    )
                
                # Wait before next iteration
                await asyncio.sleep(update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("main_loop_error", error=str(e))
                await asyncio.sleep(update_interval)
        
        logger.info("main_loop_stopped")
    
    async def _health_check_loop(self):
        """Monitor system health and exchange connectivity"""
        check_interval = self.config.get('monitoring', {}).get('health_check', {}).get('interval', 60)
        
        logger.info("health_check_started", interval=check_interval)
        
        while self.is_running:
            try:
                # Check exchange connections
                for exchange_name, exchange in self.exchanges.items():
                    if not exchange.is_connected:
                        logger.warning("exchange_disconnected", exchange=exchange_name)
                        
                        # Attempt reconnection
                        try:
                            if await exchange.connect():
                                logger.info("exchange_reconnected", exchange=exchange_name)
                            else:
                                logger.error("exchange_reconnection_failed", exchange=exchange_name)
                        except Exception as e:
                            logger.error("exchange_reconnection_error", 
                                       exchange=exchange_name, error=str(e))
                
                # Check risk manager status
                risk_status = self.risk_manager.get_status()
                if risk_status.get('emergency_stop'):
                    logger.critical("emergency_stop_activated")
                    await self.notification_manager.send_notification(
                        "🚨 Emergency Stop Activated",
                        "Trading has been halted due to risk management rules"
                    )
                    await self.stop()
                    break
                
                # Log system status
                await self._log_system_status()
                
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("health_check_error", error=str(e))
                await asyncio.sleep(check_interval)
        
        logger.info("health_check_stopped")
    
    async def _log_system_status(self):
        """Log current system status"""
        connected_exchanges = [name for name, ex in self.exchanges.items() if ex.is_connected]
        
        status = {
            'running_time': asyncio.get_event_loop().time() - (self.start_time or 0),
            'connected_exchanges': connected_exchanges,
            'opportunities_found': self.total_opportunities_found,
            'trades_executed': self.total_trades_executed,
            'total_profit': float(self.total_profit),
            'risk_status': self.risk_manager.get_status(),
            'portfolio_value': float(await self.portfolio_manager.get_total_value()) if self.portfolio_manager else 0
        }
        
        logger.info("system_status", **status)
    
    @property
    def status(self) -> Dict[str, Any]:
        """Get current engine status"""
        base_status = {
            'running': self.is_running,
            'stopping': self.is_stopping,
            'exchanges': {name: ex.status for name, ex in self.exchanges.items()},
            'opportunities_found': self.total_opportunities_found,
            'trades_executed': self.total_trades_executed,
            'total_profit': float(self.total_profit),
            'start_time': self.start_time
        }
        
        # Add AI system status if available
        if self.ai_dashboard:
            try:
                ai_status = self.ai_dashboard.get_real_time_stats()
                base_status['ai_system'] = ai_status
            except Exception as e:
                logger.warning("ai_status_retrieval_failed", error=str(e))
                base_status['ai_system'] = {'error': str(e)}
        
        return base_status


async def main():
    """Main entry point for SmartArb Engine"""
    engine = SmartArbEngine()
    
    try:
        await engine.start()
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt_received")
    except Exception as e:
        logger.error("engine_failed", error=str(e))
        sys.exit(1)
    finally:
        await engine.stop()


if __name__ == "__main__":
    # Run the engine
    asyncio.run(main())
