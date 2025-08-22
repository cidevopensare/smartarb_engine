"""
Notification Manager for SmartArb Engine
Handles alerts and notifications via multiple channels
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import time
import structlog

logger = structlog.get_logger(__name__)


class NotificationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"


class NotificationManager:
    """
    Multi-channel notification system
    
    Features:
    - Telegram bot integration
    - Email notifications (future)
    - Webhook notifications
    - Rate limiting to prevent spam
    - Message formatting and templating
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Telegram configuration
        self.telegram_enabled = config.get('telegram_alerts', False)
        self.telegram_bot_token = config.get('telegram_bot_token')
        self.telegram_chat_id = config.get('telegram_chat_id')
        
        # Rate limiting
        self.rate_limit_window = 300  # 5 minutes
        self.max_messages_per_window = 10
        self.message_history: List[float] = []
        
        # Message queuing
        self.message_queue: List[Dict[str, Any]] = []
        self.queue_processor_task = None
        
        # Notification templates
        self.templates = {
            'startup': "🚀 *{title}*\n{message}",
            'shutdown': "🛑 *{title}*\n{message}",
            'profit': "💰 *{title}*\n{message}",
            'error': "❌ *{title}*\n{message}",
            'warning': "⚠️ *{title}*\n{message}",
            'info': "ℹ️ *{title}*\n{message}",
            'emergency': "🚨 *EMERGENCY*\n{message}"
        }
        
        logger.info("notification_manager_initialized",
                   telegram_enabled=self.telegram_enabled)
    
    async def send_notification(self, title: str, message: str, 
                              level: NotificationLevel = NotificationLevel.INFO,
                              channels: Optional[List[NotificationChannel]] = None):
        """
        Send notification via configured channels
        
        Args:
            title: Notification title
            message: Notification message
            level: Notification severity level
            channels: Specific channels to use (if None, uses all configured)
        """
        
        # Rate limiting check
        if not self._check_rate_limit():
            logger.warning("notification_rate_limited", title=title)
            return
        
        # Default channels based on level
        if channels is None:
            channels = self._get_default_channels(level)
        
        # Queue notification for processing
        notification = {
            'title': title,
            'message': message,
            'level': level,
            'channels': channels,
            'timestamp': time.time()
        }
        
        self.message_queue.append(notification)
        
        # Process immediately for critical messages
        if level == NotificationLevel.CRITICAL:
            await self._process_notification(notification)
        else:
            # Process in background
            if not self.queue_processor_task or self.queue_processor_task.done():
                self.queue_processor_task = asyncio.create_task(self._process_queue())
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        current_time = time.time()
        
        # Remove old messages outside window
        self.message_history = [
            timestamp for timestamp in self.message_history
            if current_time - timestamp < self.rate_limit_window
        ]
        
        # Check if we can send more messages
        if len(self.message_history) >= self.max_messages_per_window:
            return False
        
        # Add current message to history
        self.message_history.append(current_time)
        return True
    
    def _get_default_channels(self, level: NotificationLevel) -> List[NotificationChannel]:
        """Get default channels based on notification level"""
        channels = [NotificationChannel.LOG]  # Always log
        
        if self.telegram_enabled:
            if level in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]:
                channels.append(NotificationChannel.TELEGRAM)
            elif level == NotificationLevel.WARNING and self.config.get('telegram_warnings', False):
                channels.append(NotificationChannel.TELEGRAM)
            elif level == NotificationLevel.INFO and self.config.get('telegram_info', False):
                channels.append(NotificationChannel.TELEGRAM)
        
        return channels
    
    async def _process_queue(self):
        """Process notification queue in background"""
        while self.message_queue:
            notification = self.message_queue.pop(0)
            try:
                await self._process_notification(notification)
                await asyncio.sleep(1)  # Small delay to avoid overwhelming channels
            except Exception as e:
                logger.error("notification_processing_failed", error=str(e))
    
    async def _process_notification(self, notification: Dict[str, Any]):
        """Process individual notification"""
        for channel in notification['channels']:
            try:
                if channel == NotificationChannel.TELEGRAM:
                    await self._send_telegram(notification)
                elif channel == NotificationChannel.LOG:
                    await self._send_to_log(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook(notification)
                    
            except Exception as e:
                logger.error("notification_channel_failed",
                           channel=channel.value,
                           title=notification['title'],
                           error=str(e))
    
    async def _send_telegram(self, notification: Dict[str, Any]):
        """Send notification via Telegram"""
        if not self.telegram_enabled or not self.telegram_bot_token or not self.telegram_chat_id:
            return
        
        # Format message
        template_key = self._get_template_key(notification['level'])
        formatted_message = self.templates[template_key].format(
            title=notification['title'],
            message=notification['message']
        )
        
        # Telegram API URL
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        
        # Message payload
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': formatted_message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.debug("telegram_notification_sent", 
                                   title=notification['title'])
                    else:
                        response_text = await response.text()
                        logger.error("telegram_api_error",
                                   status=response.status,
                                   response=response_text)
                        
        except Exception as e:
            logger.error("telegram_send_failed", error=str(e))
    
    async def _send_to_log(self, notification: Dict[str, Any]):
        """Send notification to log"""
        level = notification['level']
        
        if level == NotificationLevel.CRITICAL:
            logger.critical("notification",
                          title=notification['title'],
                          message=notification['message'])
        elif level == NotificationLevel.ERROR:
            logger.error("notification",
                        title=notification['title'],
                        message=notification['message'])
        elif level == NotificationLevel.WARNING:
            logger.warning("notification",
                          title=notification['title'],
                          message=notification['message'])
        else:
            logger.info("notification",
                       title=notification['title'],
                       message=notification['message'])
    
    async def _send_webhook(self, notification: Dict[str, Any]):
        """Send notification via webhook"""
        webhook_url = self.config.get('webhook_url')
        if not webhook_url:
            return
        
        payload = {
            'title': notification['title'],
            'message': notification['message'],
            'level': notification['level'].value,
            'timestamp': notification['timestamp'],
            'source': 'SmartArb Engine'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.debug("webhook_notification_sent",
                                   title=notification['title'])
                    else:
                        logger.error("webhook_error",
                                   status=response.status)
                        
        except Exception as e:
            logger.error("webhook_send_failed", error=str(e))
    
    def _get_template_key(self, level: NotificationLevel) -> str:
        """Get template key based on notification level"""
        template_map = {
            NotificationLevel.INFO: 'info',
            NotificationLevel.WARNING: 'warning',
            NotificationLevel.ERROR: 'error',
            NotificationLevel.CRITICAL: 'emergency'
        }
        return template_map.get(level, 'info')
    
    # Convenience methods for common notifications
    async def notify_startup(self, message: str):
        """Send startup notification"""
        await self.send_notification(
            "SmartArb Engine Started",
            message,
            NotificationLevel.INFO,
            [NotificationChannel.TELEGRAM, NotificationChannel.LOG]
        )
    
    async def notify_shutdown(self, message: str):
        """Send shutdown notification"""
        await self.send_notification(
            "SmartArb Engine Stopped",
            message,
            NotificationLevel.INFO,
            [NotificationChannel.TELEGRAM, NotificationChannel.LOG]
        )
    
    async def notify_profit(self, symbol: str, profit: float, exchange_pair: str):
        """Send profitable trade notification"""
        message = f"Symbol: {symbol}\nProfit: {profit:.4f} USDT\nExchanges: {exchange_pair}"
        await self.send_notification(
            "Profitable Trade Executed",
            message,
            NotificationLevel.INFO,
            [NotificationChannel.TELEGRAM, NotificationChannel.LOG]
        )
    
    async def notify_error(self, title: str, error_message: str):
        """Send error notification"""
        await self.send_notification(
            title,
            error_message,
            NotificationLevel.ERROR,
            [NotificationChannel.TELEGRAM, NotificationChannel.LOG]
        )
    
    async def notify_emergency_stop(self, reason: str):
        """Send emergency stop notification"""
        message = f"Trading halted due to: {reason}\nImmediate attention required!"
        await self.send_notification(
            "EMERGENCY STOP ACTIVATED",
            message,
            NotificationLevel.CRITICAL,
            [NotificationChannel.TELEGRAM, NotificationChannel.LOG]
        )
    
    async def notify_exchange_error(self, exchange: str, error: str):
        """Send exchange connectivity error notification"""
        message = f"Exchange: {exchange}\nError: {error}\nRetrying connection..."
        await self.send_notification(
            "Exchange Connection Error",
            message,
            NotificationLevel.WARNING,
            [NotificationChannel.LOG]
        )
    
    async def notify_performance_summary(self, stats: Dict[str, Any]):
        """Send performance summary notification"""
        message = (
            f"Opportunities Found: {stats.get('opportunities_found', 0)}\n"
            f"Trades Executed: {stats.get('trades_executed', 0)}\n"
            f"Total Profit: {stats.get('total_profit', 0):.4f} USDT\n"
            f"Success Rate: {stats.get('success_rate', 0):.1f}%"
        )
        await self.send_notification(
            "Daily Performance Summary",
            message,
            NotificationLevel.INFO,
            [NotificationChannel.TELEGRAM, NotificationChannel.LOG]
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification system statistics"""
        return {
            'telegram_enabled': self.telegram_enabled,
            'messages_in_queue': len(self.message_queue),
            'messages_sent_in_window': len(self.message_history),
            'rate_limit_window': self.rate_limit_window,
            'max_messages_per_window': self.max_messages_per_window
        }
