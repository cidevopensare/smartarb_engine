#!/bin/bash

# SmartArb Telegram Helper Script
# Automatically handles virtual environment activation

cd /home/smartarb/smartarb_engine

# Activate virtual environment
source venv/bin/activate

# Function to run Telegram command
run_telegram_command() {
    python3 -c "
import asyncio, sys, os
sys.path.append('.')

# Load .env function
def load_env():
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip().split('#')[0].strip()

load_env()
from src.notifications.telegram_live_trading import SmartArbTelegramBot

async def main():
    async with SmartArbTelegramBot() as bot:
        $1

asyncio.run(main())
"
}

case $1 in
    "startup")
        echo "🚀 Sending startup notification..."
        run_telegram_command "await bot.send_startup_message()"
        ;;
    "report")
        echo "📊 Sending daily report..."
        run_telegram_command "await bot.send_daily_report()"
        ;;
    "trade")
        echo "💰 Testing trade alert..."
        run_telegram_command "await bot.alert_trade_executed({'profit': 85.50, 'pair': 'BTC/USDT', 'amount': 400})"
        ;;
    "opportunity")
        echo "⚡ Testing opportunity alert..."
        run_telegram_command "await bot.alert_opportunity({'potential_profit': 55.25, 'spread_percent': 2.3, 'pair': 'ETH/USDT', 'buy_exchange': 'Kraken', 'sell_exchange': 'Bybit'})"
        ;;
    "emergency")
        echo "🚨 Testing emergency alert..."
        run_telegram_command "await bot.alert_emergency_stop('Test emergency - System operational')"
        ;;
    "error")
        echo "⚠️ Testing error alert..."
        run_telegram_command "await bot.alert_system_error('Test system warning', 'WARNING')"
        ;;
    "test-all")
        echo "🧪 Running complete Telegram test suite..."
        for cmd in startup trade opportunity report emergency; do
            echo "Testing: $cmd"
            $0 $cmd
            sleep 2
        done
        echo "✅ All tests completed!"
        ;;
    *)
        echo "📱 SmartArb Telegram Helper"
        echo "Usage: $0 {startup|report|trade|opportunity|emergency|error|test-all}"
        echo ""
        echo "Commands:"
        echo "  startup     - Send startup notification"
        echo "  report      - Send daily report"
        echo "  trade       - Test trade alert"
        echo "  opportunity - Test opportunity alert"
        echo "  emergency   - Test emergency alert"
        echo "  error       - Test error alert"
        echo "  test-all    - Run all tests"
        ;;
esac
