“””
Notification System for SmartArb Engine
Comprehensive notification system supporting Telegram, email, and webhooks
“””

import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
import time
from datetime import datetime
import structlog

logger = structlog.get_logger(**name**)

class NotificationType(Enum):
“”“Types of notifications”””
INFO = “info”
SUCCESS = “success”
WARNING = “warning”
ERROR = “error”
CRITICAL = “critical”
TRADE_EXECUTED = “trade_executed”
LARGE_OPPORTUNITY = “large_opportunity”
SYSTEM_ERROR = “system_error”
DAILY_SUMMARY = “daily_summary”
AI_ANALYSIS = “ai_analysis”
AI_RECOMMENDATION = “ai_recommendation”
EMERGENCY = “emergency”

class NotificationPriority(Enum):
“”“Notification priority levels”””
LOW = 1
MEDIUM = 2
HIGH = 3
CRITICAL = 4
EMERGENCY = 5

@dataclass
class Notification:
“”“Notification data structure”””
title: str
message: str
notification_type: NotificationType
priority: NotificationPriority
data: Dict[str, Any]
timestamp: float
retry_count: int = 0
max_retries: int = 3

```
def to_dict(self) -> Dict[str, Any]:
    """Convert notification to dictionary"""
    return {
        'title': self.title,
        'message': self.message,
        'type': self.notification_type.value,
        'priority': self.priority.value,
        'data': self.data,
        'timestamp': self.timestamp,
        'datetime': datetime.fromtimestamp(self.timestamp).isoformat()
    }
```

class NotificationManager:
“””
Comprehensive Notification Management System

```
Features:
- Multiple notification channels (Telegram, Email, Webhook)
- Priority-based routing
- Rate limiting and deduplication
- Retry mechanism with exponential backoff
- Template system for consistent messaging
- AI-enhanced notifications
"""

def __init__(self, config: Dict[str, Any]):
    self.config = config
    
    # Notification configuration
    notification_config = config.get('notifications', {})
    
    # Telegram configuration
    self.telegram_enabled = notification_config.get('telegram', {}).get('enabled', False)
    self.telegram_bot_token = notification_config.get('telegram', {}).get('bot_token', '')
    self.telegram_chat_id = notification_config.get('telegram', {}).get('chat_id', '')
    
    # Email configuration
    self.email_enabled = notification_config.get('email', {}).get('enabled', False)
    self.smtp_host = notification_config.get('email', {}).get('smtp_host', '')
    self.smtp_port = notification_config.get('email', {}).get('smtp_port', 587)
    self.smtp_username = notification_config.get('email', {}).get('username', '')
    self.smtp_password = notification_config.get('email', {}).get('password', '')
    
    # Webhook configuration
    self.webhook_enabled = notification_config.get('webhook', {}).get('enabled', False)
    self.webhook_url = notification_config.get('webhook', {}).get('url', '')
    self.webhook_timeout = notification_config.get('webhook', {}).get('timeout', 10)
    self.webhook_retry_attempts = notification_config.get('webhook', {}).get('retry_attempts', 3)
    
    # Alert settings
    alert_config = notification_config.get('alerts', {})
    self.alert_settings = {
        'trade_executed': alert_config.get('trade_executed', True),
        'large_opportunity': alert_config.get('large_opportunity', True),
        'system_errors': alert_config.get('system_errors', True),
        'daily_summary': alert_config.get('daily_summary', True),
        'ai_analysis': alert_config.get('ai_analysis', True)
    }
    
    # Rate limiting
    self.rate_limits = {
        NotificationType.INFO: 10,  # Max 10 info notifications per hour
        NotificationType.WARNING: 20,
        NotificationType.ERROR: 50,
        NotificationType.CRITICAL: 100,
        NotificationType.EMERGENCY: 1000  # No practical limit for emergencies
    }
    
    # Tracking
    self.sent_notifications = []
    self.rate_limit_counters = {}
    self.last_notification_times = {}
    
    # Deduplication
    self.recent_notifications = {}  # Hash -> timestamp for deduplication
    self.deduplication_window = 300  # 5 minutes
    
    logger.info("notification_manager_initialized",
               telegram_enabled=self.telegram_enabled,
               email_enabled=self.email_enabled,
               webhook_enabled=self.webhook_enabled)

async def send_notification(self, title: str, message: str, 
                          notification_type: NotificationType = NotificationType.INFO,
                          priority: NotificationPriority = NotificationPriority.MEDIUM,
                          data: Optional[Dict[str, Any]] = None,
                          force: bool = False) -> bool:
    """
    Send a notification through configured channels
    
    Args:
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        priority: Priority level
        data: Additional data to include
        force: Force send even if rate limited
        
    Returns:
        True if notification was sent successfully
    """
    
    # Create notification object
    notification = Notification(
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        data=data or {},
        timestamp=time.time()
    )
    
    try:
        # Check if notification should be sent
        if not force and not self._should_send_notification(notification):
            logger.debug("notification_skipped",
                       title=title,
                       type=notification_type.value,
                       reason="rate_limited_or_duplicate")
            return False
        
        # Check alert settings
        if not self._is_alert_enabled(notification_type):
            logger.debug("notification_skipped",
                       title=title,
                       type=notification_type.value,
                       reason="alert_disabled")
            return False
        
        # Send through all enabled channels
        success_count = 0
        total_channels = 0
        
        # Telegram
        if self.telegram_enabled:
            total_channels += 1
            if await self._send_telegram(notification):
                success_count += 1
        
        # Email
        if self.email_enabled and priority.value >= NotificationPriority.HIGH.value:
            total_channels += 1
            if await self._send_email(notification):
                success_count += 1
        
        # Webhook
        if self.webhook_enabled:
            total_channels += 1
            if await self._send_webhook(notification):
                success_count += 1
        
        # Update tracking
        self._update_notification_tracking(notification)
        
        # Consider successful if at least one channel worked
        success = success_count > 0 or total_channels == 0
        
        logger.info("notification_sent",
                   title=title,
                   type=notification_type.value,
                   priority=priority.value,
                   success_channels=success_count,
                   total_channels=total_channels,
                   success=success)
        
        return success
        
    except Exception as e:
        logger.error("notification_send_failed",
                    title=title,
                    type=notification_type.value,
                    error=str(e))
        return False

async def _send_telegram(self, notification: Notification) -> bool:
    """Send notification via Telegram"""
    if not self.telegram_bot_token or not self.telegram_chat_id:
        return False
    
    try:
        # Format message for Telegram
        telegram_message = self._format_telegram_message(notification)
        
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            'chat_id': self.telegram_chat_id,
            'text': telegram_message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    logger.debug("telegram_notification_sent",
                               title=notification.title)
                    return True
                else:
                    error_text = await response.text()
                    logger.error("telegram_notification_failed",
                               status=response.status,
                               error=error_text)
                    return False
                    
    except Exception as e:
        logger.error("telegram_send_error", error=str(e))
        return False

async def _send_email(self, notification: Notification) -> bool:
    """Send notification via email"""
    if not all([self.smtp_host, self.smtp_username, self.smtp_password]):
        return False
    
    try:
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = self.smtp_username
        msg['To'] = self.smtp_username  # Send to self
        msg['Subject'] = f"SmartArb Alert: {notification.title}"
        
        # Format email body
        email_body = self._format_email_message(notification)
        msg.attach(MIMEText(email_body, 'html'))
        
        # Send email
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.smtp_username, self.smtp_username, text)
        
        logger.debug("email_notification_sent", title=notification.title)
        return True
        
    except Exception as e:
        logger.error("email_send_error", error=str(e))
        return False

async def _send_webhook(self, notification: Notification) -> bool:
    """Send notification via webhook"""
    if not self.webhook_url:
        return False
    
    try:
        payload = {
            'notification': notification.to_dict(),
            'source': 'smartarb_engine',
            'version': '1.0'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.webhook_url,
                json=payload,
                timeout=self.webhook_timeout
            ) as response:
                if response.status in [200, 201, 202]:
                    logger.debug("webhook_notification_sent",
                               title=notification.title,
                               url=self.webhook_url)
                    return True
                else:
                    error_text = await response.text()
                    logger.error("webhook_notification_failed",
                               status=response.status,
                               error=error_text)
                    return False
                    
    except Exception as e:
        logger.error("webhook_send_error", error=str(e))
        return False

def _format_telegram_message(self, notification: Notification) -> str:
    """Format notification for Telegram"""
    
    # Priority emoji
    priority_emojis = {
        NotificationPriority.LOW: "ℹ️",
        NotificationPriority.MEDIUM: "⚠️",
        NotificationPriority.HIGH: "🚨",
        NotificationPriority.CRITICAL: "💥",
        NotificationPriority.EMERGENCY: "🆘"
    }
    
    # Type emoji
    type_emojis = {
        NotificationType.INFO: "ℹ️",
        NotificationType.SUCCESS: "✅",
        NotificationType.WARNING: "⚠️",
        NotificationType.ERROR: "❌",
        NotificationType.CRITICAL: "💥",
        NotificationType.TRADE_EXECUTED: "💰",
        NotificationType.LARGE_OPPORTUNITY: "🎯",
        NotificationType.SYSTEM_ERROR: "⚙️",
        NotificationType.DAILY_SUMMARY: "📊",
        NotificationType.AI_ANALYSIS: "🧠",
        NotificationType.AI_RECOMMENDATION: "💡",
        NotificationType.EMERGENCY: "🆘"
    }
    
    priority_emoji = priority_emojis.get(notification.priority, "")
    type_emoji = type_emojis.get(notification.notification_type, "")
    
    # Build message
    message_parts = []
    
    # Header
    header = f"{priority_emoji} {type_emoji} <b>{notification.title}</b>"
    message_parts.append(header)
    
    # Main message
    message_parts.append(notification.message)
    
    # Additional data
    if notification.data:
        message_parts.append("\n<b>Details:</b>")
        for key, value in notification.data.items():
            if key not in ['raw_data', 'internal']:  # Skip internal fields
                if isinstance(value, float):
                    formatted_value = f"{value:.4f}"
                else:
                    formatted_value = str(value)
                message_parts.append(f"• {key}: {formatted_value}")
    
    # Timestamp
    dt = datetime.fromtimestamp(notification.timestamp)
    timestamp_str = dt.strftime("%H:%M:%S")
    message_parts.append(f"\n⏰ {timestamp_str}")
    
    return "\n".join(message_parts)

def _format_email_message(self, notification: Notification) -> str:
    """Format notification for email"""
    
    # HTML email template
    html_template = """
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px; }}
            .content {{ margin: 20px 0; }}
            .details {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            .footer {{ color: #666; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{title}</h2>
            <p>Priority: {priority} | Type: {type}</p>
        </div>
        
        <div class="content">
            <p>{message}</p>
        </div>
        
        {details_section}
        
        <div class="footer">
            <p>SmartArb Engine | {timestamp}</p>
        </div>
    </body>
    </html>
    """
    
    # Choose color based on priority
    priority_colors = {
        NotificationPriority.LOW: "#007bff",
        NotificationPriority.MEDIUM: "#ffc107",
        NotificationPriority.HIGH: "#fd7e14",
        NotificationPriority.CRITICAL: "#dc3545",
        NotificationPriority.EMERGENCY: "#6f42c1"
    }
    
    color = priority_colors.get(notification.priority, "#007bff")
    
    # Details section
    details_html = ""
    if notification.data:
        details_items = []
        for key, value in notification.data.items():
            if key not in ['raw_data', 'internal']:
                details_items.append(f"<li><strong>{key}:</strong> {value}</li>")
        
        if details_items:
            details_html = f"""
            <div class="details">
                <h4>Details:</h4>
                <ul>
                    {''.join(details_items)}
                </ul>
            </div>
            """
    
    # Format timestamp
    dt = datetime.fromtimestamp(notification.timestamp)
    timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    return html_template.format(
        title=notification.title,
        priority=notification.priority.name,
        type=notification.notification_type.value.replace('_', ' ').title(),
        message=notification.message,
        details_section=details_html,
        timestamp=timestamp_str,
        color=color
    )

def _should_send_notification(self, notification: Notification) -> bool:
    """Check if notification should be sent based on rate limits and deduplication"""
    
    # Check deduplication
    notification_hash = self._get_notification_hash(notification)
    now = time.time()
    
    if notification_hash in self.recent_notifications:
        last_sent = self.recent_notifications[notification_hash]
        if now - last_sent < self.deduplication_window:
            return False
    
    # Check rate limits (except for high priority notifications)
    if notification.priority.value < NotificationPriority.HIGH.value:
        rate_limit = self.rate_limits.get(notification.notification_type, 100)
        
        # Reset counters hourly
        hour_key = int(now // 3600)
        counter_key = (notification.notification_type, hour_key)
        
        current_count = self.rate_limit_counters.get(counter_key, 0)
        if current_count >= rate_limit:
            return False
    
    return True

def _update_notification_tracking(self, notification: Notification) -> None:
    """Update notification tracking counters"""
    now = time.time()
    
    # Update deduplication tracking
    notification_hash = self._get_notification_hash(notification)
    self.recent_notifications[notification_hash] = now
    
    # Clean old deduplication entries
    cutoff_time = now - self.deduplication_window
    self.recent_notifications = {
        h: t for h, t in self.recent_notifications.items() 
        if t > cutoff_time
    }
    
    # Update rate limit counters
    hour_key = int(now // 3600)
    counter_key = (notification.notification_type, hour_key)
    self.rate_limit_counters[counter_key] = self.rate_limit_counters.get(counter_key, 0) + 1
    
    # Clean old rate limit counters (keep only last 2 hours)
    current_hour = hour_key
    self.rate_limit_counters = {
        k: v for k, v in self.rate_limit_counters.items()
        if k[1] >= current_hour - 1
    }
    
    # Add to sent notifications history
    self.sent_notifications.append(notification.to_dict())
    
    # Keep only last 1000 notifications
    if len(self.sent_notifications) > 1000:
        self.sent_notifications = self.sent_notifications[-1000:]

def _get_notification_hash(self, notification: Notification) -> str:
    """Generate hash for notification deduplication"""
    import hashlib
    
    # Create hash from title, message, and type
    content = f"{notification.title}:{notification.message}:{notification.notification_type.value}"
    return hashlib.md5(content.encode()).hexdigest()

def _is_alert_enabled(self, notification_type: NotificationType) -> bool:
    """Check if alert type is enabled"""
    alert_mapping = {
        NotificationType.TRADE_EXECUTED: 'trade_executed',
        NotificationType.LARGE_OPPORTUNITY: 'large_opportunity',
        NotificationType.SYSTEM_ERROR: 'system_errors',
        NotificationType.ERROR: 'system_errors',
        NotificationType.CRITICAL: 'system_errors',
        NotificationType.DAILY_SUMMARY: 'daily_summary',
        NotificationType.AI_ANALYSIS: 'ai_analysis',
        NotificationType.AI_RECOMMENDATION: 'ai_analysis'
    }
    
    alert_key = alert_mapping.get(notification_type)
    if alert_key:
        return self.alert_settings.get(alert_key, True)
    
    # Always allow emergency and high-priority notifications
    return True

# Convenience methods for common notifications
async def notify_trade_executed(self, opportunity_id: str, profit: float, 
                              symbol: str, **details) -> bool:
    """Send trade execution notification"""
    
    # Determine priority based on profit
    if profit > 100:
        priority = NotificationPriority.HIGH
        title = f"🎯 Large Profit: ${profit:.2f}"
    elif profit > 0:
        priority = NotificationPriority.MEDIUM
        title = f"✅ Trade Profitable: ${profit:.2f}"
    else:
        priority = NotificationPriority.HIGH  # Losses are important
        title = f"❌ Trade Loss: ${profit:.2f}"
    
    message = f"Trade executed for {symbol}\nOpportunity: {opportunity_id}\nProfit: ${profit:.2f}"
    
    data = {
        'opportunity_id': opportunity_id,
        'symbol': symbol,
        'profit': profit,
        **details
    }
    
    return await self.send_notification(
        title=title,
        message=message,
        notification_type=NotificationType.TRADE_EXECUTED,
        priority=priority,
        data=data
    )

async def notify_large_opportunity(self, opportunity_id: str, expected_profit: float,
                                 symbol: str, spread_percent: float, **details) -> bool:
    """Send large opportunity notification"""
    title = f"🎯 Large Opportunity: ${expected_profit:.2f}"
    message = f"Large arbitrage opportunity detected!\nSymbol: {symbol}\nExpected Profit: ${expected_profit:.2f}\nSpread: {spread_percent:.2f}%"
    
    data = {
        'opportunity_id': opportunity_id,
        'symbol': symbol,
        'expected_profit': expected_profit,
        'spread_percent': spread_percent,
        **details
    }
    
    return await self.send_notification(
        title=title,
        message=message,
        notification_type=NotificationType.LARGE_OPPORTUNITY,
        priority=NotificationPriority.HIGH,
        data=data
    )

async def notify_system_error(self, error_type: str, error_message: str, 
                            **details) -> bool:
    """Send system error notification"""
    title = f"⚙️ System Error: {error_type}"
    message = f"SmartArb Engine encountered an error:\n{error_message}"
    
    return await self.send_notification(
        title=title,
        message=message,
        notification_type=NotificationType.SYSTEM_ERROR,
        priority=NotificationPriority.HIGH,
        data={'error_type': error_type, 'error_message': error_message, **details}
    )

async def notify_daily_summary(self, trades_count: int, total_profit: float,
                             success_rate: float, **details) -> bool:
    """Send daily summary notification"""
    title = "📊 Daily Trading Summary"
    message = (f"Daily SmartArb Summary:\n"
              f"Trades: {trades_count}\n"
              f"Total Profit: ${total_profit:.2f}\n"
              f"Success Rate: {success_rate:.1f}%")
    
    data = {
        'trades_count': trades_count,
        'total_profit': total_profit,
        'success_rate': success_rate,
        **details
    }
    
    return await self.send_notification(
        title=title,
        message=message,
        notification_type=NotificationType.DAILY_SUMMARY,
        priority=NotificationPriority.MEDIUM,
        data=data
    )

async def notify_ai_analysis(self, analysis_type: str, recommendations_count: int,
                           **details) -> bool:
    """Send AI analysis notification"""
    title = f"🧠 AI Analysis Complete: {analysis_type}"
    message = f"Claude AI has completed {analysis_type} analysis.\nRecommendations: {recommendations_count}"
    
    data = {
        'analysis_type': analysis_type,
        'recommendations_count': recommendations_count,
        **details
    }
    
    return await self.send_notification(
        title=title,
        message=message,
        notification_type=NotificationType.AI_ANALYSIS,
        priority=NotificationPriority.MEDIUM,
        data=data
    )

async def notify_emergency(self, title: str, message: str, **details) -> bool:
    """Send emergency notification"""
    return await self.send_notification(
        title=f"🆘 EMERGENCY: {title}",
        message=message,
        notification_type=NotificationType.EMERGENCY,
        priority=NotificationPriority.EMERGENCY,
        data=details,
        force=True  # Force send regardless of rate limits
    )

# Status and management methods
def get_notification_stats(self) -> Dict[str, Any]:
    """Get notification statistics"""
    now = time.time()
    
    # Count recent notifications by type
    recent_notifications = [
        n for n in self.sent_notifications
        if now - n['timestamp'] < 86400  # Last 24 hours
    ]
    
    type_counts = {}
    for notification in recent_notifications:
        ntype = notification['type']
        type_counts[ntype] = type_counts.get(ntype, 0) + 1
    
    return {
        'total_sent': len(self.sent_notifications),
        'sent_24h': len(recent_notifications),
        'type_counts_24h': type_counts,
        'enabled_channels': {
            'telegram': self.telegram_enabled,
            'email': self.email_enabled,
            'webhook': self.webhook_enabled
        },
        'rate_limit_status': self.rate_limit_counters
    }

def get_recent_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent notifications"""
    return self.sent_notifications[-limit:]

async def test_all_channels(self) -> Dict[str, bool]:
    """Test all notification channels"""
    test_notification = Notification(
        title="Test Notification",
        message="This is a test notification from SmartArb Engine",
        notification_type=NotificationType.INFO,
        priority=NotificationPriority.LOW,
        data={'test': True},
        timestamp=time.time()
    )
    
    results = {}
    
    if self.telegram_enabled:
        results['telegram'] = await self._send_telegram(test_notification)
    
    if self.email_enabled:
        results['email'] = await self._send_email(test_notification)
    
    if self.webhook_enabled:
        results['webhook'] = await self._send_webhook(test_notification)
    
    return results
```