#!/usr/bin/env python3
"""
Advanced Telegram Alerts for SmartArb Live Trading
Optimized for real-time trading notifications
"""

import asyncio
import aiohttp
import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import sys

# Add project root to path
sys.path.append('/home/smartarb/smartarb_engine')

# Load .env file manually if needed
def load_env_file():
    """Load environment variables from .env file"""
    env_path = '/home/smartarb/smartarb_engine/.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Load environment variables
load_env_file()

# Try to import psutil, fallback gracefully
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️ psutil not available - system stats disabled")

class AlertLevel(Enum):
    """Alert priority levels"""
    LOW = ("🔵", 300)        # 5 min cooldown
    MEDIUM = ("🟡", 120)     # 2 min cooldown  
    HIGH = ("🟠", 60)        # 1 min cooldown
    CRITICAL = ("🔴", 10)    # 10 sec cooldown
    EMERGENCY = ("🚨", 0)    # Immediate

    def __init__(self, emoji, cooldown):
        self.emoji = emoji
        self.cooldown = cooldown

class SmartArbTelegramBot:
    """Smart Telegram bot for live trading alerts"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.backup_chat_id = os.getenv('TELEGRAM_BACKUP_CHAT_ID', '')
        
        print(f"🔍 Debug - Bot Token: {self.bot_token[:20] + '...' if self.bot_token else 'None'}")
        print(f"🔍 Debug - Chat ID: {self.chat_id}")
        
        if not self.bot_token or not self.chat_id:
            print("❌ Environment variables not found:")
            print(f"   TELEGRAM_BOT_TOKEN: {'✅' if self.bot_token else '❌'}")
            print(f"   TELEGRAM_CHAT_ID: {'✅' if self.chat_id else '❌'}")
            raise ValueError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        
        self.session = None
        self.last_alert_time = {}
        self.stats = {
            'trades_notified': 0,
            'opportunities_sent': 0,
            'errors_reported': 0,
            'uptime_start': datetime.now()
        }
        
        # Rate limiting settings
        self.max_alerts_per_hour = int(os.getenv('TELEGRAM_MAX_NOTIFICATIONS_PER_HOUR', '15'))
        self.hour_counter = 0
        self.hour_reset_time = datetime.now()
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        await self.send_startup_message()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.send_shutdown_message()
            await self.session.close()
    
    def _check_rate_limit(self, alert_level: AlertLevel) -> bool:
        """Smart rate limiting"""
        if alert_level == AlertLevel.EMERGENCY:
            return True  # Never rate limit emergencies
            
        # Reset hourly counter
        now = datetime.now()
        if (now - self.hour_reset_time).total_seconds() >= 3600:
            self.hour_counter = 0
            self.hour_reset_time = now
            
        # Check hourly limit
        if self.hour_counter >= self.max_alerts_per_hour:
            return False
            
        # Check cooldown for this alert type
        alert_key = alert_level.name
        last_time = self.last_alert_time.get(alert_key)
        if last_time:
            elapsed = (now - last_time).total_seconds()
            if elapsed < alert_level.cooldown:
                return False
                
        # Update counters
        self.hour_counter += 1
        self.last_alert_time[alert_key] = now
        return True
    
    def _get_system_status(self) -> str:
        """Real-time system status"""
        if not PSUTIL_AVAILABLE:
            mode = "🔴 LIVE" if os.getenv('TRADING_MODE') == 'LIVE' else "📄 PAPER"
            return f"Status: OK {mode}"
            
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory().percent
            uptime = datetime.now() - self.stats['uptime_start']
            
            mode = "🔴 LIVE" if os.getenv('TRADING_MODE') == 'LIVE' else "📄 PAPER"
            
            return f"CPU:{cpu:.1f}% RAM:{ram:.1f}% Up:{uptime.days}d{uptime.seconds//3600}h {mode}"
        except:
            return "Status: Unknown"
    
    async def _send_message(self, message: str, silent: bool = False) -> bool:
        """Send message with retry logic"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_notification': silent,
            'disable_web_page_preview': True
        }
        
        for attempt in range(3):  # 3 retry attempts
            try:
                async with self.session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        error = await response.text()
                        print(f"Telegram API error {response.status}: {error}")
                        
            except Exception as e:
                print(f"Telegram send attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
        return False
    
    async def alert_trade_executed(self, trade_data: Dict) -> bool:
        """Alert for executed trades"""
        if not self._check_rate_limit(AlertLevel.HIGH):
            return False
            
        profit = trade_data.get('profit', 0)
        pair = trade_data.get('pair', 'N/A')
        amount = trade_data.get('amount', 0)
        
        # Only alert for significant profits
        min_profit = float(os.getenv('TELEGRAM_MIN_PROFIT_THRESHOLD', '25'))
        if profit < min_profit:
            return False
            
        message = f"""
🎯 <b>TRADE EXECUTED</b> {AlertLevel.HIGH.emoji}

💰 <b>Profit:</b> ${profit:.2f}
📊 <b>Pair:</b> {pair}
💵 <b>Amount:</b> ${amount:.2f}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

📈 <b>Status:</b> {self._get_system_status()}
        """
        
        success = await self._send_message(message.strip())
        if success:
            self.stats['trades_notified'] += 1
        return success
    
    async def alert_opportunity(self, opp_data: Dict) -> bool:
        """Alert for high-value opportunities"""
        if not self._check_rate_limit(AlertLevel.MEDIUM):
            return False
            
        profit = opp_data.get('potential_profit', 0)
        spread = opp_data.get('spread_percent', 0)
        pair = opp_data.get('pair', 'N/A')
        
        message = f"""
⚡ <b>OPPORTUNITY DETECTED</b> {AlertLevel.MEDIUM.emoji}

🎯 <b>Potential Profit:</b> ${profit:.2f}
📈 <b>Spread:</b> {spread:.2f}%
📊 <b>Pair:</b> {pair}
🏢 <b>Exchanges:</b> {opp_data.get('buy_exchange', 'N/A')} → {opp_data.get('sell_exchange', 'N/A')}

⏰ <b>Detected:</b> {datetime.now().strftime('%H:%M:%S')}
        """
        
        success = await self._send_message(message.strip())
        if success:
            self.stats['opportunities_sent'] += 1
        return success
    
    async def alert_system_error(self, error_msg: str, error_type: str = "ERROR") -> bool:
        """Alert for system errors"""
        if not self._check_rate_limit(AlertLevel.CRITICAL):
            return False
            
        message = f"""
⚠️ <b>SYSTEM {error_type}</b> {AlertLevel.CRITICAL.emoji}

🔍 <b>Error:</b> {error_msg}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 <b>System:</b> {self._get_system_status()}

🛠️ <b>Action Required:</b> Check system immediately
        """
        
        success = await self._send_message(message.strip())
        if success:
            self.stats['errors_reported'] += 1
        return success
    
    async def send_daily_report(self) -> bool:
        """Send daily performance report"""
        uptime = datetime.now() - self.stats['uptime_start']
        
        # Get trading stats (mock for now - integrate with your system)
        trading_stats = {
            'total_trades': 127,  # Replace with real data
            'success_rate': 89.2,  # Replace with real data
            'total_profit': 284.50,  # Replace with real data
        }
        
        message = f"""
📊 <b>DAILY REPORT</b> {AlertLevel.LOW.emoji}

🎯 <b>Trading Performance:</b>
- Total Trades: {trading_stats['total_trades']}
- Success Rate: {trading_stats['success_rate']:.1f}%
- Total Profit: ${trading_stats['total_profit']:.2f}

🔔 <b>Notification Stats:</b>
- Trades Notified: {self.stats['trades_notified']}
- Opportunities: {self.stats['opportunities_sent']}
- Errors Reported: {self.stats['errors_reported']}

⚡ <b>System Health:</b>
- Uptime: {uptime.days}d {uptime.seconds//3600}h
- {self._get_system_status()}

📅 <b>Report Date:</b> {datetime.now().strftime('%Y-%m-%d')}
        """
        
        return await self._send_message(message.strip(), silent=True)
    
    async def send_startup_message(self) -> bool:
        """Send startup notification"""
        message = f"""
🚀 <b>SmartArb Engine STARTED</b>

⚡ <b>Status:</b> System online and monitoring
🌐 <b>IP:</b> 192.168.1.100
📊 <b>Mode:</b> {os.getenv('TRADING_MODE', 'PAPER')}
⏰ <b>Started:</b> {datetime.now().strftime('%H:%M:%S')}

🔔 <b>Alert Settings:</b>
- Min Profit: ${os.getenv('TELEGRAM_MIN_PROFIT_THRESHOLD', '25')}
- Max Alerts/Hour: {self.max_alerts_per_hour}

🎯 <b>Ready for live trading notifications!</b>
        """
        
        return await self._send_message(message.strip())
    
    async def send_shutdown_message(self) -> bool:
        """Send shutdown notification"""
        uptime = datetime.now() - self.stats['uptime_start']
        
        message = f"""
🛑 <b>SmartArb Engine STOPPED</b>

⏰ <b>Shutdown:</b> {datetime.now().strftime('%H:%M:%S')}
📊 <b>Session Uptime:</b> {uptime.days}d {uptime.seconds//3600}h

🔔 <b>Session Stats:</b>
- Trades Notified: {self.stats['trades_notified']}
- Opportunities: {self.stats['opportunities_sent']}
- Errors: {self.stats['errors_reported']}

💤 <b>System going offline...</b>
        """
        
        return await self._send_message(message.strip())


    async def alert_emergency_stop(self, reason: str) -> bool:
        """Emergency stop alert - highest priority"""
        return await self.alert_system_error(f"EMERGENCY STOP: {reason}", "EMERGENCY")


# Test function
async def test_telegram_live_system():
    """Test the live trading Telegram system"""
    print("🧪 Testing SmartArb Live Trading Telegram System...")
    
    async with SmartArbTelegramBot() as bot:
        # Test different alert types
        tests = [
            ("Trade Alert", bot.alert_trade_executed({
                'profit': 45.75,
                'pair': 'BTC/USDT',
                'amount': 250.00
            })),
            
            ("Opportunity Alert", bot.alert_opportunity({
                'potential_profit': 32.50,
                'spread_percent': 1.85,
                'pair': 'ETH/USDT',
                'buy_exchange': 'Kraken',
                'sell_exchange': 'Bybit'
            })),
            
            ("System Error", bot.alert_system_error(
                "Network connectivity issue detected", "WARNING"
            ))
        ]
        
        for test_name, test_coro in tests:
            print(f"Testing {test_name}...")
            success = await test_coro
            print(f"{'✅' if success else '❌'} {test_name}: {'Success' if success else 'Failed'}")
            await asyncio.sleep(2)  # Prevent rate limiting
            
        # Test daily report
        print("Testing Daily Report...")
        report_success = await bot.send_daily_report()
        print(f"{'✅' if report_success else '❌'} Daily Report: {'Success' if report_success else 'Failed'}")
        
        print(f"\n📊 Bot Stats: {bot.stats}")
        return True


if __name__ == "__main__":
    asyncio.run(test_telegram_live_system())
