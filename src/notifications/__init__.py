"""
Real Telegram Notification Service for SmartArb Engine
"""

import asyncio
import aiohttp
import json
import os
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

class NotificationLevel(Enum):
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"
    SUCCESS = "success"

class NotificationService:
    """Real notification service with Telegram support"""
    
    def __init__(self, config):
        self.config = config
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
        
        # Emoji mapping
        self.emojis = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌", 
            NotificationLevel.CRITICAL: "🚨",
            NotificationLevel.SUCCESS: "✅"
        }
        
        if self.enabled:
            logger.info("Telegram notifications enabled", chat_id=self.chat_id)
        else:
            logger.warning("Telegram notifications disabled - missing token/chat_id")
    
    async def initialize(self):
        """Initialize notification service"""
        if self.enabled:
            # Test Telegram connection
            try:
                await self._test_telegram_connection()
                logger.info("Telegram connection test successful")
            except Exception as e:
                logger.error("Telegram connection test failed", error=str(e))
                self.enabled = False
        return True
    
    async def _test_telegram_connection(self):
        """Test Telegram bot connection"""
        url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Telegram API test failed: {response.status}")
                
                data = await response.json()
                if not data.get('ok'):
                    raise Exception(f"Telegram bot error: {data}")
    
    async def send_notification(self, title: str, message: str, priority: str = "info"):
        """Send notification via Telegram and console"""
        
        # Always log to console
        level = NotificationLevel(priority.lower())
        emoji = self.emojis.get(level, "📢")
        console_msg = f"{emoji} {title}: {message}"
        
        if level in [NotificationLevel.ERROR, NotificationLevel.CRITICAL]:
            logger.error(console_msg)
        elif level == NotificationLevel.WARNING:
            logger.warning(console_msg) 
        else:
            logger.info(console_msg)
        
        # Send to Telegram if enabled
        if self.enabled:
            await self._send_telegram(title, message, level)
    
    async def _send_telegram(self, title: str, message: str, level: NotificationLevel):
        """Send message to Telegram"""
        try:
            emoji = self.emojis.get(level, "📢")
            text = f"{emoji} *{title}*\n\n{message}\n\n🕐 {datetime.now().strftime('%H:%M:%S')}"
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.debug("Telegram notification sent successfully")
                    else:
                        logger.error("Telegram send failed", status=response.status)
                        
        except Exception as e:
            logger.error("Telegram notification error", error=str(e))
    
    # Trading-specific notifications
    async def notify_opportunity_found(self, symbol: str, profit: float, exchanges: list):
        """Notify about arbitrage opportunity"""
        title = "💰 Arbitrage Opportunity!"
        message = f"""
📊 **Symbol:** {symbol}
💵 **Expected Profit:** ${profit:.2f}
🏦 **Exchanges:** {' → '.join(exchanges)}
⚡ **Status:** Analyzing...
        """.strip()
        
        await self.send_notification(title, message, "info")
    
    async def notify_trade_executed(self, symbol: str, profit: float, exchange_from: str, exchange_to: str):
        """Notify about executed trade"""
        title = "🎯 Trade Executed!"
        message = f"""
📊 **Symbol:** {symbol}  
💰 **Profit:** ${profit:.2f}
🔄 **Route:** {exchange_from} → {exchange_to}
✅ **Status:** Completed
        """.strip()
        
        level = "success" if profit > 0 else "warning"
        await self.send_notification(title, message, level)
    
    async def notify_error(self, error_type: str, details: str):
        """Notify about system errors"""
        title = f"🚨 System Error: {error_type}"
        message = f"⚠️ **Details:** {details}\n🔧 **Action Required:** Check logs"
        
        await self.send_notification(title, message, "error")
    
    async def notify_daily_summary(self, stats: dict):
        """Send daily performance summary"""
        title = "📊 Daily Trading Summary"
        message = f"""
📈 **Total Trades:** {stats.get('total_trades', 0)}
💰 **Total Profit:** ${stats.get('total_profit', 0):.2f}
📊 **Success Rate:** {stats.get('success_rate', 0):.1f}%
🎯 **Best Trade:** ${stats.get('best_trade', 0):.2f}
        """.strip()
        
        await self.send_notification(title, message, "info")
