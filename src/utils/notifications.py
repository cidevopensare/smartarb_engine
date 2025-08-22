“””
Notification System for SmartArb Engine
Supports multiple notification channels: Telegram, Email, Webhooks, Discord
“””

import asyncio
import aiohttp
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import structlog
import json
from datetime import datetime, timedelta
import os

logger = structlog.get_logger(**name**)

class NotificationLevel(Enum):
“”“Notification priority levels”””
INFO = “info”
WARNING = “warning”
ERROR = “error”
CRITICAL = “critical”
SUCCESS = “success”

class NotificationChannel(Enum):
“”“Supported notification channels”””
TELEGRAM = “telegram”
EMAIL = “email”
WEBHOOK = “webhook”
DISCORD = “discord”
CONSOLE = “console”

@dataclass
class Notification:
“”“Notification message structure”””
title: str
message: str
level: NotificationLevel
channel: NotificationChannel
timestamp: datetime
data: Optional[Dict[str, Any]] = None
retry_count: int = 0
max_retries: int = 3

```
def __post_init__(self):
    if not self.timestamp:
        self.timestamp = datetime.now()
```

class NotificationManager:
“””
Centralized notification management system

```
Features:
- Multiple notification channels
- Priority-based filtering
- Rate limiting
- Retry mechanisms
- Template support
- Batch notifications
"""

def __init__(self, config: Dict[str, Any]):
    self.config = config
    self.notification_config = config.get('notifications', {})
    
    # Initialize channels
    self.channels = {}
    self._initialize_channels()
    
    # Rate limiting
    self.rate_limits = {
        NotificationLevel.INFO: 60,      # Max 1 per minute
        NotificationLevel.WARNING: 30,   # Max 1 per 30 seconds
        NotificationLevel.ERROR: 10,     # Max 1 per 10 seconds
        NotificationLevel.CRITICAL: 0,   # No limit
        NotificationLevel.SUCCESS: 60    # Max 1 per minute
    }
    
    # Track last notification times for rate limiting
    self.last_notification_times = {}
    
    # Queue for batch processing
    self.notification_queue = asyncio.Queue()
    self.batch_size = 10
    self.batch_timeout = 30  # seconds
    
    # Notification history
    self.notification_history = []
    self.max_history_size = 1000
    
    # Statistics
    self.stats = {
        'total_sent': 0,
        'failed_sends': 0,
        'by_channel': {},
        'by_level': {}
    }
    
    # Start background processor
    self.processor_task = None
    
    logger.info("notification_manager_initialized",
               channels=list(self.channels.keys()),
               rate_limits=self.rate_limits)

def _initialize_channels(self):
    """Initialize notification channels based on configuration"""
    
    # Telegram
    if self.notification_config.get('telegram', {}).get('enabled', False):
        self.channels[NotificationChannel.TELEGRAM] = TelegramNotifier(
            self.notification_config['telegram']
        )
    
    # Email
    if self.notification_config.get('email', {}).get('enabled', False):
        self.channels[NotificationChannel.EMAIL] = EmailNotifier(
            self.notification_config['email']
        )
    
    # Webhook
    if self.notification_config.get('webhook', {}).get('enabled', False):
        self.channels[NotificationChannel.WEBHOOK] = WebhookNotifier(
            self.notification_config['webhook']
        )
    
    # Discord
    if self.notification_config.get('discord', {}).get('enabled', False):
        self.channels[NotificationChannel.DISCORD] = DiscordNotifier(
            self.notification_config['discord']
        )
    
    # Console (always enabled)
    self.channels[NotificationChannel.CONSOLE] = ConsoleNotifier()

async def start(self):
    """Start the notification processor"""
    if not self.processor_task:
        self.processor_task = asyncio.create_task(self._process_notifications())
        logger.info("notification_processor_started")

async def stop(self):
    """Stop the notification processor"""
    if self.processor_task:
        self.processor_task.cancel()
        try:
            await self.processor_task
        except asyncio.CancelledError:
            pass
        logger.info("notification_processor_stopped")

async def notify(self, title: str, message: str, 
                level: NotificationLevel = NotificationLevel.INFO,
                channels: Optional[List[NotificationChannel]] = None,
                data: Optional[Dict[str, Any]] = None):
    """Send notification through specified channels"""
    
    # Default to all configured channels if none specified
    if channels is None:
        channels = list(self.channels.keys())
    
    # Apply rate limiting
    if not self._check_rate_limit(level):
        logger.debug("notification_rate_limited", level=level.value)
        return
    
    # Create notifications for each channel
    for channel in channels:
        if channel in self.channels:
            notification = Notification(
                title=title,
                message=message,
                level=level,
                channel=channel,
                timestamp=datetime.now(),
                data=data
            )
            
            await self.notification_queue.put(notification)
    
    # Update rate limiting
    self._update_rate_limit(level)

def _check_rate_limit(self, level: NotificationLevel) -> bool:
    """Check if notification is within rate limits"""
    
    rate_limit = self.rate_limits.get(level, 0)
    if rate_limit == 0:  # No limit
        return True
    
    last_time = self.last_notification_times.get(level)
    if last_time is None:
        return True
    
    time_since_last = (datetime.now() - last_time).total_seconds()
    return time_since_last >= rate_limit

def _update_rate_limit(self, level: NotificationLevel):
    """Update last notification time for rate limiting"""
    self.last_notification_times[level] = datetime.now()

async def _process_notifications(self):
    """Background processor for notifications"""
    
    while True:
        try:
            batch = []
            
            # Collect batch of notifications
            try:
                # Get first notification with timeout
                notification = await asyncio.wait_for(
                    self.notification_queue.get(),
                    timeout=self.batch_timeout
                )
                batch.append(notification)
                
                # Collect additional notifications up to batch size
                while len(batch) < self.batch_size:
                    try:
                        notification = self.notification_queue.get_nowait()
                        batch.append(notification)
                    except asyncio.QueueEmpty:
                        break
            
            except asyncio.TimeoutError:
                continue  # No notifications to process
            
            # Process batch
            if batch:
                await self._process_batch(batch)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("notification_processor_error", error=str(e))
            await asyncio.sleep(5)  # Brief pause before retrying

async def _process_batch(self, notifications: List[Notification]):
    """Process a batch of notifications"""
    
    # Group by channel for efficient processing
    by_channel = {}
    for notification in notifications:
        channel = notification.channel
        if channel not in by_channel:
            by_channel[channel] = []
        by_channel[channel].append(notification)
    
    # Send notifications for each channel
    tasks = []
    for channel, channel_notifications in by_channel.items():
        if channel in self.channels:
            task = asyncio.create_task(
                self._send_channel_notifications(channel, channel_notifications)
            )
            tasks.append(task)
    
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def _send_channel_notifications(self, channel: NotificationChannel, 
                                    notifications: List[Notification]):
    """Send notifications for a specific channel"""
    
    channel_handler = self.channels[channel]
    
    for notification in notifications:
        try:
            success = await channel_handler.send(notification)
            
            if success:
                self._update_stats(notification, True)
                self.notification_history.append(notification)
            else:
                self._update_stats(notification, False)
                await self._handle_failed_notification(notification)
            
        except Exception as e:
            logger.error("notification_send_error",
                       channel=channel.value,
                       error=str(e))
            self._update_stats(notification, False)
            await self._handle_failed_notification(notification)
    
    # Limit history size
    if len(self.notification_history) > self.max_history_size:
        self.notification_history = self.notification_history[-self.max_history_size:]

async def _handle_failed_notification(self, notification: Notification):
    """Handle failed notification with retry logic"""
    
    notification.retry_count += 1
    
    if notification.retry_count <= notification.max_retries:
        # Exponential backoff
        delay = 2 ** notification.retry_count
        await asyncio.sleep(delay)
        
        # Re-queue for retry
        await self.notification_queue.put(notification)
        
        logger.info("notification_retry_queued",
                   title=notification.title,
                   retry_count=notification.retry_count,
                   delay=delay)
    else:
        logger.error("notification_max_retries_exceeded",
                    title=notification.title,
                    retries=notification.retry_count)

def _update_stats(self, notification: Notification, success: bool):
    """Update notification statistics"""
    
    self.stats['total_sent'] += 1
    
    if not success:
        self.stats['failed_sends'] += 1
    
    # Update channel stats
    channel_name = notification.channel.value
    if channel_name not in self.stats['by_channel']:
        self.stats['by_channel'][channel_name] = {'sent': 0, 'failed': 0}
    
    self.stats['by_channel'][channel_name]['sent'] += 1
    if not success:
        self.stats['by_channel'][channel_name]['failed'] += 1
    
    # Update level stats
    level_name = notification.level.value
    if level_name not in self.stats['by_level']:
        self.stats['by_level'][level_name] = {'sent': 0, 'failed': 0}
    
    self.stats['by_level'][level_name]['sent'] += 1
    if not success:
        self.stats['by_level'][level_name]['failed'] += 1

# Convenience methods for different notification levels
async def info(self, title: str, message: str, **kwargs):
    """Send info notification"""
    await self.notify(title, message, NotificationLevel.INFO, **kwargs)

async def warning(self, title: str, message: str, **kwargs):
    """Send warning notification"""
    await self.notify(title, message, NotificationLevel.WARNING, **kwargs)

async def error(self, title: str, message: str, **kwargs):
    """Send error notification"""
    await self.notify(title, message, NotificationLevel.ERROR, **kwargs)

async def critical(self, title: str, message: str, **kwargs):
    """Send critical notification"""
    await self.notify(title, message, NotificationLevel.CRITICAL, **kwargs)

async def success(self, title: str, message: str, **kwargs):
    """Send success notification"""
    await self.notify(title, message, NotificationLevel.SUCCESS, **kwargs)

# Trading-specific notification methods
async def notify_trade_executed(self, execution_result):
    """Notify about executed trade"""
    title = "🎯 Trade Executed"
    message = f"""
    Execution ID: {execution_result.execution_id}
    Profit/Loss: ${execution_result.profit_loss:.2f}
    Execution Time: {execution_result.execution_time:.2f}s
    Fees: ${execution_result.fees_paid:.2f}
    Slippage: {execution_result.slippage:.2f}%
    """
    
    level = NotificationLevel.SUCCESS if execution_result.success else NotificationLevel.ERROR
    await self.notify(title, message.strip(), level)

async def notify_opportunity_found(self, opportunity):
    """Notify about arbitrage opportunity"""
    title = "💰 Arbitrage Opportunity"
    message = f"""
    Strategy: {opportunity.strategy_name}
    Symbol: {opportunity.symbol}
    Expected Profit: ${opportunity.expected_profit:.2f} ({opportunity.expected_profit_percent:.2f}%)
    Risk Score: {opportunity.risk_score:.2f}
    Confidence: {opportunity.confidence_level:.2f}
    """
    
    await self.notify(title, message.strip(), NotificationLevel.INFO)

async def notify_system_status(self, status):
    """Notify about system status changes"""
    title = f"🔧 System Status: {status['status']}"
    message = f"""
    Engine Status: {status['status']}
    Connected Exchanges: {len([ex for ex in status.get('exchanges', {}).values() if ex.get('connected', False)])}
    Active Strategies: {len(status.get('strategies', {}))}
    Portfolio Value: ${status.get('portfolio', {}).get('total_value', 0):.2f}
    """
    
    level = NotificationLevel.INFO
    if status['status'] in ['ERROR', 'EMERGENCY_STOP']:
        level = NotificationLevel.CRITICAL
    elif status['status'] == 'STOPPING':
        level = NotificationLevel.WARNING
    
    await self.notify(title, message.strip(), level)

def get_stats(self) -> Dict[str, Any]:
    """Get notification statistics"""
    return self.stats.copy()
```

class TelegramNotifier:
“”“Telegram bot notifier”””

```
def __init__(self, config: Dict[str, Any]):
    self.bot_token = config.get('bot_token')
    self.chat_id = config.get('chat_id')
    self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    # Emoji mapping for different levels
    self.level_emojis = {
        NotificationLevel.INFO: "ℹ️",
        NotificationLevel.WARNING: "⚠️",
        NotificationLevel.ERROR: "❌",
        NotificationLevel.CRITICAL: "🚨",
        NotificationLevel.SUCCESS: "✅"
    }

async def send(self, notification: Notification) -> bool:
    """Send Telegram notification"""
    
    try:
        emoji = self.level_emojis.get(notification.level, "📢")
        text = f"{emoji} *{notification.title}*\n\n{notification.message}"
        
        async with aiohttp.ClientSession() as session:
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            async with session.post(f"{self.base_url}/sendMessage", data=data) as response:
                return response.status == 200
                
    except Exception as e:
        logger.error("telegram_send_error", error=str(e))
        return False
```

class EmailNotifier:
“”“Email notifier using SMTP”””

```
def __init__(self, config: Dict[str, Any]):
    self.smtp_server = config.get('smtp_server')
    self.smtp_port = config.get('smtp_port', 587)
    self.username = config.get('username')
    self.password = config.get('password')
    self.from_email = config.get('from_email', self.username)
    self.to_emails = config.get('to_emails', [])
    if isinstance(self.to_emails, str):
        self.to_emails = [self.to_emails]

async def send(self, notification: Notification) -> bool:
    """Send email notification"""
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = ', '.join(self.to_emails)
        msg['Subject'] = f"[SmartArb] {notification.title}"
        
        # Create HTML body
        body = self._create_html_body(notification)
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls(context=context)
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.from_email, self.to_emails, text)
        
        return True
        
    except Exception as e:
        logger.error("email_send_error", error=str(e))
        return False

def _create_html_body(self, notification: Notification) -> str:
    """Create HTML email body"""
    
    level_colors = {
        NotificationLevel.INFO: "#17a2b8",
        NotificationLevel.WARNING: "#ffc107",
        NotificationLevel.ERROR: "#dc3545",
        NotificationLevel.CRITICAL: "#721c24",
        NotificationLevel.SUCCESS: "#28a745"
    }
    
    color = level_colors.get(notification.level, "#6c757d")
    
    html = f"""
    <html>
    <head></head>
    <body>
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: {color}; color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0;">{notification.title}</h2>
                <p style="margin: 5px 0 0 0;">SmartArb Engine - {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div style="padding: 20px; background-color: #f8f9fa;">
                <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{notification.message}</pre>
            </div>
            <div style="padding: 10px; background-color: #e9ecef; text-align: center; font-size: 12px; color: #6c757d;">
                This is an automated message from SmartArb Engine
            </div>
        </div>
    </body>
    </html>
    """
    
    return html
```

class WebhookNotifier:
“”“Generic webhook notifier”””

```
def __init__(self, config: Dict[str, Any]):
    self.url = config.get('url')
    self.headers = config.get('headers', {})
    self.timeout = config.get('timeout', 10)

async def send(self, notification: Notification) -> bool:
    """Send webhook notification"""
    
    try:
        payload = {
            'title': notification.title,
            'message': notification.message,
            'level': notification.level.value,
            'timestamp': notification.timestamp.isoformat(),
            'data': notification.data
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.url,
                json=payload,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                return response.status < 400
                
    except Exception as e:
        logger.error("webhook_send_error", error=str(e))
        return False
```

class DiscordNotifier:
“”“Discord webhook notifier”””

```
def __init__(self, config: Dict[str, Any]):
    self.webhook_url = config.get('webhook_url')
    
    # Color mapping for embed
    self.level_colors = {
        NotificationLevel.INFO: 0x3498db,      # Blue
        NotificationLevel.WARNING: 0xf39c12,   # Orange
        NotificationLevel.ERROR: 0xe74c3c,     # Red
        NotificationLevel.CRITICAL: 0x8b0000,  # Dark Red
        NotificationLevel.SUCCESS: 0x2ecc71    # Green
    }

async def send(self, notification: Notification) -> bool:
    """Send Discord notification"""
    
    try:
        color = self.level_colors.get(notification.level, 0x95a5a6)
        
        embed = {
            "title": notification.title,
            "description": notification.message,
            "color": color,
            "timestamp": notification.timestamp.isoformat(),
            "footer": {
                "text": "SmartArb Engine"
            }
        }
        
        payload = {
            "embeds": [embed]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.webhook_url, json=payload) as response:
                return response.status == 204
                
    except Exception as e:
        logger.error("discord_send_error", error=str(e))
        return False
```

class ConsoleNotifier:
“”“Console/stdout notifier”””

```
def __init__(self):
    self.level_prefixes = {
        NotificationLevel.INFO: "ℹ️  INFO",
        NotificationLevel.WARNING: "⚠️  WARNING",
        NotificationLevel.ERROR: "❌ ERROR",
        NotificationLevel.CRITICAL: "🚨 CRITICAL",
        NotificationLevel.SUCCESS: "✅ SUCCESS"
    }

async def send(self, notification: Notification) -> bool:
    """Send console notification"""
    
    try:
        prefix = self.level_prefixes.get(notification.level, "📢 NOTICE")
        timestamp = notification.timestamp.strftime('%H:%M:%S')
        
        print(f"\n[{timestamp}] {prefix}: {notification.title}")
        print(f"{notification.message}")
        print("-" * 50)
        
        return True
        
    except Exception as e:
        logger.error("console_send_error", error=str(e))
        return False
```