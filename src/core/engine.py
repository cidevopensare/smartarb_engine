#!/usr/bin/env python3
"""
SmartArb Engine - Core Trading Engine (Enhanced with Telegram)
"""

import asyncio
import logging
import time
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Import configuration
from ..config.config_manager import AppConfig, ExchangeConfig, StrategyConfig
from ..core.logger import get_logger, log_trade_activity
from ..notifications.telegram_notifier import TelegramNotifier, NotificationConfig

class SmartArbEngine:
    """Enhanced trading engine with Telegram notifications"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger('engine')
        self.is_running = False
        self.is_stopping = False
        
        # System state
        self.start_time = datetime.now()
        self.last_health_check = time.time()
        self.stats = {
            'opportunities_found': 0,
            'trades_executed': 0,
            'total_profit': 0.0,
            'api_calls': 0,
            'errors': 0
        }
        
        # Trading state
        self.active_exchanges = {}
        self.active_strategies = {}
        self.market_data = {}
        
        # Milestones tracking
        self.last_profit_milestone = 0
        self.last_trade_milestone = 0
        
        # Initialize Telegram notifier
        self.telegram = self._setup_telegram_notifier()
        
        self.logger.info("🎯 SmartArb Engine initialized with Telegram notifications")
        
    def _setup_telegram_notifier(self) -> Optional[TelegramNotifier]:
        """Setup Telegram notifier"""
        try:
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            enabled = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
            
            if not enabled or not bot_token or not chat_id:
                self.logger.info("📱 Telegram notifications disabled")
                return None
            
            config = NotificationConfig(
                bot_token=bot_token,
                chat_id=chat_id,
                enabled=enabled,
                min_profit_threshold=float(os.getenv('TELEGRAM_MIN_PROFIT_THRESHOLD', '25.0')),
                min_spread_threshold=float(os.getenv('TELEGRAM_MIN_SPREAD_THRESHOLD', '1.0')),
                max_notifications_per_hour=int(os.getenv('TELEGRAM_MAX_NOTIFICATIONS_PER_HOUR', '15')),
                status_report_interval=int(os.getenv('TELEGRAM_STATUS_REPORT_INTERVAL', '1800')),
                error_notifications=os.getenv('TELEGRAM_ERROR_NOTIFICATIONS', 'true').lower() == 'true'
            )
            
            return TelegramNotifier(config)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to setup Telegram notifier: {e}")
            return None
        
    async def start(self) -> None:
        """Start the trading engine"""
        if self.is_running:
            self.logger.warning("⚠️ Engine is already running")
            return
            
        self.logger.info("🚀 Starting SmartArb Engine...")
        self.is_running = True
        
        try:
            # Start Telegram notifier
            if self.telegram:
                await self.telegram.start()
            
            # Initialize components
            await self._initialize_exchanges()
            await self._initialize_strategies()
            await self._start_market_data()
            
            # Start main trading loop
            self.logger.info("✅ SmartArb Engine started successfully")
            asyncio.create_task(self._main_loop())
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start engine: {str(e)}")
            if self.telegram:
                await self.telegram.notify_error(f"Engine startup failed: {str(e)}", "STARTUP_ERROR")
            self.is_running = False
            raise
            
    async def shutdown(self) -> None:
        """Gracefully shutdown the engine"""
        if not self.is_running:
            return
            
        self.logger.info("🛑 Shutting down SmartArb Engine...")
        self.is_stopping = True
        
        try:
            # Stop Telegram notifier
            if self.telegram:
                await self.telegram.stop()
            
            # Log final statistics
            await self._log_final_stats()
            
            self.is_running = False
            self.logger.info("✅ SmartArb Engine shutdown complete")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {str(e)}")
            
    async def _initialize_exchanges(self) -> None:
        """Initialize exchange connections"""
        self.logger.info("🔗 Initializing exchange connections...")
        
        for exchange_name, exchange_config in self.config.exchanges.items():
            if not exchange_config.enabled:
                self.logger.info(f"⏭️ Skipping disabled exchange: {exchange_name}")
                continue
                
            self.logger.info(f"🔌 Connecting to {exchange_name.upper()}...")
            
            # Simulate exchange initialization
            self.active_exchanges[exchange_name] = {
                'name': exchange_name,
                'connected': True,
                'last_ping': time.time(),
                'config': exchange_config
            }
            
            await asyncio.sleep(0.5)  # Simulate connection delay
            self.logger.info(f"✅ {exchange_name.upper()} connected successfully")
            
        if not self.active_exchanges:
            error_msg = "No exchanges were successfully initialized"
            if self.telegram:
                await self.telegram.notify_error(error_msg, "EXCHANGE_ERROR")
            raise Exception(error_msg)
            
        self.logger.info(f"🎉 Initialized {len(self.active_exchanges)} exchanges")
    
    async def _initialize_strategies(self) -> None:
        """Initialize trading strategies"""
        self.logger.info("🎯 Initializing trading strategies...")
        
        for strategy_name, strategy_config in self.config.strategies.items():
            if not strategy_config.enabled:
                self.logger.info(f"⏭️ Skipping disabled strategy: {strategy_name}")
                continue
                
            self.logger.info(f"🎲 Loading strategy: {strategy_name}")
            
            self.active_strategies[strategy_name] = {
                'name': strategy_name,
                'config': strategy_config,
                'opportunities_found': 0
            }
            
            self.logger.info(f"✅ Strategy {strategy_name} loaded")
            
        if not self.active_strategies:
            error_msg = "No strategies were successfully initialized"
            if self.telegram:
                await self.telegram.notify_error(error_msg, "STRATEGY_ERROR")
            raise Exception(error_msg)
            
        self.logger.info(f"🎉 Initialized {len(self.active_strategies)} strategies")
    
    async def _start_market_data(self) -> None:
        """Start market data simulation"""
        self.logger.info("📊 Starting market data feeds...")
        
        # Initialize market data for common pairs
        trading_pairs = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        
        for pair in trading_pairs:
            self.market_data[pair] = {
                'last_update': time.time(),
                'prices': {}
            }
            
            # Simulate price data for each exchange
            import random
            base_price = 50000 if 'BTC' in pair else 3000 if 'ETH' in pair else 1.0
            
            for exchange_name in self.active_exchanges.keys():
                price_variation = random.uniform(0.95, 1.05)
                self.market_data[pair]['prices'][exchange_name] = {
                    'price': base_price * price_variation,
                    'timestamp': time.time()
                }
        
        self.logger.info(f"✅ Market data initialized for {len(trading_pairs)} pairs")
        
    async def _main_loop(self) -> None:
        """Main trading loop with Telegram integration"""
        self.logger.info("🔄 Starting main trading loop...")
        
        loop_count = 0
        while self.is_running and not self.is_stopping:
            try:
                loop_count += 1
                
                # Scan for opportunities
                await self._scan_opportunities()
                
                # Check for milestones
                await self._check_milestones()
                
                # Send status reports
                await self._send_status_reports()
                
                # Log status every 10 loops
                if loop_count % 10 == 0:
                    await self._log_status()
                
                # Wait based on strategy frequency
                scan_frequency = 5  # Default 5 seconds
                if self.active_strategies:
                    scan_frequency = min(
                        strategy['config'].scan_frequency 
                        for strategy in self.active_strategies.values()
                    )
                
                await asyncio.sleep(scan_frequency)
                
            except Exception as e:
                error_msg = f"Error in main loop: {str(e)}"
                self.logger.error(f"❌ {error_msg}")
                self.stats['errors'] += 1
                
                if self.telegram:
                    await self.telegram.notify_error(error_msg, "RUNTIME_ERROR")
                
                await asyncio.sleep(10)
    
    async def _scan_opportunities(self) -> None:
        """Scan for arbitrage opportunities with Telegram notifications"""
        import random
        
        # Simulate opportunity detection
        for strategy_name in self.active_strategies:
            if strategy_name == "spatial_arbitrage":
                # Simulate finding opportunities with more variety
                if random.random() < 0.35:  # 35% chance of finding opportunity
                    
                    pair = random.choice(list(self.market_data.keys()))
                    exchanges = list(self.active_exchanges.keys())
                    buy_exchange = random.choice(exchanges)
                    sell_exchange = random.choice([e for e in exchanges if e != buy_exchange])
                    
                    spread = random.uniform(0.05, 3.5)  # Wider spread range
                    profit = random.uniform(5, 150)     # Wider profit range
                    
                    opportunity = {
                        'strategy': strategy_name,
                        'pair': pair,
                        'buy_exchange': buy_exchange,
                        'sell_exchange': sell_exchange,
                        'spread_percent': spread,
                        'potential_profit': profit,
                        'timestamp': time.time()
                    }
                    
                    self.stats['opportunities_found'] += 1
                    self.active_strategies[strategy_name]['opportunities_found'] += 1
                    
                    # Log opportunity
                    log_trade_activity(
                        f"🎯 OPPORTUNITY FOUND: {opportunity['pair']} | "
                        f"{opportunity['buy_exchange'].upper()} → {opportunity['sell_exchange'].upper()} | "
                        f"Spread: {opportunity['spread_percent']:.2f}% | "
                        f"Profit: ${opportunity['potential_profit']:.2f}"
                    )
                    
                    # Send Telegram notification
                    if self.telegram:
                        await self.telegram.notify_opportunity(opportunity)
                    
                    # Simulate trade execution in paper mode
                    if self.config.trading_mode == "PAPER":
                        await self._execute_paper_trade(opportunity)
        
        # Update market data
        await self._update_market_data()
    
    async def _execute_paper_trade(self, opportunity):
        """Execute a paper trade with Telegram notification"""
        await asyncio.sleep(0.1)  # Simulate execution time
        
        profit = opportunity['potential_profit']
        self.stats['trades_executed'] += 1
        self.stats['total_profit'] += profit
        
        trade = {
            'pair': opportunity['pair'],
            'profit': profit,
            'total_profit': self.stats['total_profit'],
            'timestamp': time.time()
        }
        
        log_trade_activity(
            f"📄 PAPER TRADE EXECUTED: {trade['pair']} | "
            f"Profit: ${profit:.2f} | "
            f"Total: ${self.stats['total_profit']:.2f}"
        )
        
        # Send Telegram notification for significant trades
        if self.telegram:
            await self.telegram.notify_trade_execution(trade)
    
    async def _check_milestones(self):
        """Check and notify about milestones"""
        if not self.telegram:
            return
            
        # Profit milestones (every $1000)
        current_profit_milestone = int(self.stats['total_profit'] / 1000) * 1000
        if current_profit_milestone > self.last_profit_milestone and current_profit_milestone > 0:
            self.last_profit_milestone = current_profit_milestone
            await self.telegram.notify_milestone("profit_milestone", current_profit_milestone)
        
        # Trade milestones (every 100 trades)
        current_trade_milestone = int(self.stats['trades_executed'] / 100) * 100
        if current_trade_milestone > self.last_trade_milestone and current_trade_milestone > 0:
            self.last_trade_milestone = current_trade_milestone
            await self.telegram.notify_milestone("trade_milestone", current_trade_milestone)
    
    async def _send_status_reports(self):
        """Send periodic status reports"""
        if not self.telegram:
            return
            
        status_data = {
            'uptime': str(datetime.now() - self.start_time),
            'opportunities_found': self.stats['opportunities_found'],
            'trades_executed': self.stats['trades_executed'],
            'total_profit': self.stats['total_profit'],
            'active_exchanges': len(self.active_exchanges),
            'active_strategies': len(self.active_strategies),
            'errors': self.stats['errors']
        }
        
        await self.telegram.notify_status_report(status_data)
    
    async def _update_market_data(self):
        """Update simulated market data"""
        import random
        
        for pair_data in self.market_data.values():
            for exchange_name in pair_data['prices']:
                # Small price movements
                current_price = pair_data['prices'][exchange_name]['price']
                change = random.uniform(-0.01, 0.01)
                new_price = current_price * (1 + change)
                
                pair_data['prices'][exchange_name]['price'] = new_price
                pair_data['prices'][exchange_name]['timestamp'] = time.time()
            
            pair_data['last_update'] = time.time()
    
    async def _log_status(self):
        """Log current status"""
        uptime = datetime.now() - self.start_time
        
        self.logger.info("=" * 50)
        self.logger.info("📊 SMARTARB ENGINE STATUS")
        self.logger.info(f"⏱️  Uptime: {uptime}")
        self.logger.info(f"🔗 Active Exchanges: {len(self.active_exchanges)}")
        self.logger.info(f"🎯 Active Strategies: {len(self.active_strategies)}")
        self.logger.info(f"🎲 Opportunities Found: {self.stats['opportunities_found']}")
        self.logger.info(f"📈 Trades Executed: {self.stats['trades_executed']}")
        self.logger.info(f"💰 Total Profit: ${self.stats['total_profit']:.2f}")
        if self.telegram:
            self.logger.info(f"📱 Telegram: {self.telegram.stats['notifications_sent']} notifications sent")
        self.logger.info("=" * 50)
    
    async def health_check(self):
        """Perform health check"""
        self.last_health_check = time.time()
        self.logger.debug("💚 Health check completed")
        
        return {
            'status': 'healthy',
            'uptime': str(datetime.now() - self.start_time),
            'exchanges': len(self.active_exchanges),
            'strategies': len(self.active_strategies),
            'telegram_enabled': self.telegram is not None
        }
    
    async def _log_final_stats(self) -> None:
        """Log final statistics"""
        self.logger.info("=" * 60)
        self.logger.info("📊 FINAL STATISTICS")
        self.logger.info(f"⏱️  Total Uptime: {datetime.now() - self.start_time}")
        self.logger.info(f"🎲 Total Opportunities: {self.stats['opportunities_found']}")
        self.logger.info(f"📈 Total Trades: {self.stats['trades_executed']}")
        self.logger.info(f"💰 Total Profit: ${self.stats['total_profit']:.2f}")
        if self.telegram:
            self.logger.info(f"📱 Telegram Notifications: {self.telegram.stats['notifications_sent']}")
        self.logger.info("=" * 60)
        
        self.is_running = False
        self.logger.info("✅ SmartArb Engine shutdown complete")
