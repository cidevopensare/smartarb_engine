#!/usr/bin/env python3
"""
Telegram Notification System for SmartArb Engine
Sends intelligent alerts for trading opportunities and system status
"""

import asyncio
import aiohttp
import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..core.logger import get_logger

@dataclass
class NotificationConfig:
    """Configuration for Telegram notifications"""
    bot_token: str
    chat_id: str
    enabled: bool = True
    min_profit_threshold: float = 50.0  # Only notify for profits > $50
    min_spread_threshold: float = 1.5   # Only notify for spreads > 1.5%
    max_notifications_per_hour: int = 10
    status_report_interval: int = 1800  # 30 minutes
    error_notifications: bool = True

class TelegramNotifier:
    """Advanced Telegram notification system"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.logger = get_logger('telegram')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.notification_count = 0
        self.last_reset_time = datetime.now()
        self.last_status_report = datetime.now()
        
        # Message queuing
        self.message_queue = []
        self.is_sending = False
        
        # Statistics
        self.stats = {
            'notifications_sent': 0,
            'opportunities_reported': 0,
            'errors_reported': 0,
            'status_reports_sent': 0,
            'last_notification': None
        }
        
        if self.config.enabled:
            self.logger.info("📱 Telegram Notifier initialized")
        else:
            self.logger.info("📱 Telegram Notifier disabled")
    
    async def start(self):
        """Initialize the Telegram notifier"""
        if not self.config.enabled:
            return
            
        self.session = aiohttp.ClientSession()
        
        # Send startup message
        await self._send_startup_message()
        
        # Start message processing task
        asyncio.create_task(self._process_message_queue())
        
        self.logger.info("✅ Telegram Notifier started")
    
    async def stop(self):
        """Stop the Telegram notifier"""
        if self.session:
            await self.session.close()
        
        # Send shutdown message
        if self.config.enabled:
            await self._send_shutdown_message()
        
        self.logger.info("🛑 Telegram Notifier stopped")
    
    async def notify_opportunity(self, opportunity: Dict[str, Any]):
        """Notify about a trading opportunity"""
        if not self.config.enabled:
            return
            
        # Check if opportunity meets thresholds
        profit = opportunity.get('potential_profit', 0)
        spread = opportunity.get('spread_percent', 0)
        
        if (profit < self.config.min_profit_threshold or 
            spread < self.config.min_spread_threshold):
            return
            
        # Check rate limit
        if not self._check_rate_limit():
            return
        
        # Create opportunity message
        message = self._format_opportunity_message(opportunity)
        await self._queue_message(message, priority='high')
        
        self.stats['opportunities_reported'] += 1
        self.logger.debug(f"📱 Queued opportunity notification: {opportunity['pair']}")
    
    async def notify_trade_execution(self, trade: Dict[str, Any]):
        """Notify about trade execution"""
        if not self.config.enabled:
            return
            
        profit = trade.get('profit', 0)
        
        # Only notify for significant trades
        if profit < self.config.min_profit_threshold:
            return
            
        if not self._check_rate_limit():
            return
        
        message = self._format_trade_message(trade)
        await self._queue_message(message, priority='medium')
        
        self.logger.debug(f"📱 Queued trade notification: ${profit:.2f}")
    
    async def notify_status_report(self, stats: Dict[str, Any]):
        """Send periodic status report"""
        if not self.config.enabled:
            return
            
        # Check if it's time for status report
        now = datetime.now()
        if (now - self.last_status_report).seconds < self.config.status_report_interval:
            return
            
        self.last_status_report = now
        
        message = self._format_status_report(stats)
        await self._queue_message(message, priority='low')
        
        self.stats['status_reports_sent'] += 1
        self.logger.debug("📱 Queued status report")
    
    async def notify_error(self, error_message: str, error_type: str = "ERROR"):
        """Notify about system errors"""
        if not self.config.enabled or not self.config.error_notifications:
            return
            
        message = self._format_error_message(error_message, error_type)
        await self._queue_message(message, priority='urgent')
        
        self.stats['errors_reported'] += 1
        self.logger.debug(f"📱 Queued error notification: {error_type}")
    
    async def notify_milestone(self, milestone_type: str, value: Any):
        """Notify about important milestones"""
        if not self.config.enabled:
            return
            
        message = self._format_milestone_message(milestone_type, value)
        await self._queue_message(message, priority='medium')
        
        self.logger.debug(f"📱 Queued milestone notification: {milestone_type}")
    
    def _check_rate_limit(self) -> bool:
        """Check if we can send another notification"""
        now = datetime.now()
        
        # Reset counter every hour
        if (now - self.last_reset_time).seconds >= 3600:
            self.notification_count = 0
            self.last_reset_time = now
        
        if self.notification_count >= self.config.max_notifications_per_hour:
            return False
            
        self.notification_count += 1
        return True
    
    async def _queue_message(self, message: str, priority: str = 'medium'):
        """Queue message for sending"""
        self.message_queue.append({
            'message': message,
            'priority': priority,
            'timestamp': datetime.now(),
            'retries': 0
        })
        
        # Sort queue by priority
        priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
        self.message_queue.sort(key=lambda x: priority_order.get(x['priority'], 2))
    
    async def _process_message_queue(self):
        """Process queued messages"""
        while True:
            try:
                if self.message_queue and not self.is_sending:
                    self.is_sending = True
                    
                    message_data = self.message_queue.pop(0)
                    success = await self._send_message(message_data['message'])
                    
                    if not success and message_data['retries'] < 3:
                        # Re-queue with retry
                        message_data['retries'] += 1
                        self.message_queue.append(message_data)
                        self.logger.warning(f"📱 Retrying message: {message_data['retries']}")
                    
                    self.is_sending = False
                    
                # Wait before processing next message
                await asyncio.sleep(2)  # 2 second delay between messages
                
            except Exception as e:
                self.logger.error(f"❌ Error processing message queue: {e}")
                self.is_sending = False
                await asyncio.sleep(10)
    
    async def _send_message(self, message: str) -> bool:
        """Send message to Telegram"""
        if not self.session:
            return False
            
        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.config.chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    self.stats['notifications_sent'] += 1
                    self.stats['last_notification'] = datetime.now()
                    return True
                else:
                    self.logger.error(f"❌ Telegram API error: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def _format_opportunity_message(self, opportunity: Dict[str, Any]) -> str:
        """Format opportunity notification message"""
        pair = opportunity.get('pair', 'UNKNOWN')
        buy_exchange = opportunity.get('buy_exchange', 'N/A')
        sell_exchange = opportunity.get('sell_exchange', 'N/A')
        spread = opportunity.get('spread_percent', 0)
        profit = opportunity.get('potential_profit', 0)
        
        message = f"""🎯 <b>ARBITRAGE OPPORTUNITY</b>
        
💱 <b>Pair:</b> {pair}
🔄 <b>Route:</b> {buy_exchange.upper()} → {sell_exchange.upper()}
📈 <b>Spread:</b> {spread:.2f}%
💰 <b>Profit:</b> ${profit:.2f}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

💡 <i>Opportunity detected by SmartArb Engine</i>"""
        
        return message
    
    def _format_trade_message(self, trade: Dict[str, Any]) -> str:
        """Format trade execution message"""
        pair = trade.get('pair', 'UNKNOWN')
        profit = trade.get('profit', 0)
        total_profit = trade.get('total_profit', 0)
        
        message = f"""✅ <b>TRADE EXECUTED</b>
        
💱 <b>Pair:</b> {pair}
💰 <b>Profit:</b> ${profit:.2f}
📊 <b>Total:</b> ${total_profit:.2f}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

🚀 <i>Paper trade completed successfully</i>"""
        
        return message
    
    def _format_status_report(self, stats: Dict[str, Any]) -> str:
        """Format status report message"""
        uptime = stats.get('uptime', 'Unknown')
        opportunities = stats.get('opportunities_found', 0)
        trades = stats.get('trades_executed', 0)
        profit = stats.get('total_profit', 0)
        exchanges = stats.get('active_exchanges', 0)
        
        message = f"""📊 <b>SMARTARB STATUS REPORT</b>
        
⏱️ <b>Uptime:</b> {uptime}
🔗 <b>Exchanges:</b> {exchanges} active
🎯 <b>Opportunities:</b> {opportunities}
📈 <b>Trades:</b> {trades}
💰 <b>Total Profit:</b> ${profit:.2f}
📱 <b>Notifications:</b> {self.stats['notifications_sent']}

✅ <i>All systems operational</i>"""
        
        return message
    
    def _format_error_message(self, error_message: str, error_type: str) -> str:
        """Format error notification message"""
        message = f"""🚨 <b>SYSTEM {error_type}</b>
        
❌ <b>Error:</b> {error_message}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

🔧 <i>Check system logs for details</i>"""
        
        return message
    
    def _format_milestone_message(self, milestone_type: str, value: Any) -> str:
        """Format milestone notification message"""
        if milestone_type == "profit_milestone":
            message = f"""🏆 <b>PROFIT MILESTONE REACHED!</b>
            
💰 <b>Total Profit:</b> ${value:.2f}
🎉 <b>Achievement:</b> New profit record!
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

🚀 <i>SmartArb Engine performing excellently!</i>"""
        
        elif milestone_type == "trade_milestone":
            message = f"""🎯 <b>TRADE MILESTONE REACHED!</b>
            
📈 <b>Total Trades:</b> {value}
🏆 <b>Achievement:</b> New trade count record!
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

💪 <i>Trading machine in full swing!</i>"""
        
        else:
            message = f"""🎉 <b>MILESTONE: {milestone_type.upper()}</b>
            
🏆 <b>Value:</b> {value}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}"""
        
        return message
    
    async def _send_startup_message(self):
        """Send startup notification"""
        message = f"""🚀 <b>SMARTARB ENGINE STARTED</b>
        
✅ <b>Status:</b> Online
⏰ <b>Time:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🎯 <b>Mode:</b> Active Trading
📱 <b>Notifications:</b> Enabled

🔥 <i>Ready to hunt for arbitrage opportunities!</i>"""
        
        await self._queue_message(message, priority='medium')
    
    async def _send_shutdown_message(self):
        """Send shutdown notification"""
        message = f"""🛑 <b>SMARTARB ENGINE STOPPED</b>
        
📊 <b>Session Stats:</b>
📱 Notifications sent: {self.stats['notifications_sent']}
🎯 Opportunities reported: {self.stats['opportunities_reported']}
❌ Errors reported: {self.stats['errors_reported']}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

👋 <i>System shutdown complete</i>"""
        
        # Send immediately, don't queue
        await self._send_message(message)
