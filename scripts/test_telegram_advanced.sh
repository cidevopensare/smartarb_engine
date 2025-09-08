#!/bin/bash

echo "🚀 Testing Advanced Telegram System"
echo "==================================="

cd /home/smartarb/smartarb_engine

# Activate venv
source venv/bin/activate

# Run advanced test
python3 src/notifications/telegram_live_trading.py

echo "✅ Advanced Telegram test completed"
