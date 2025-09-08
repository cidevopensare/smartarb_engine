#!/usr/bin/env python3
import asyncio
import os
from src.notifications.telegram_notifier import TelegramNotifier, NotificationConfig

async def test_telegram():
    config = NotificationConfig(
        bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
        chat_id=os.getenv('TELEGRAM_CHAT_ID'),
        enabled=True,
        min_profit_threshold=1.0,  # Test with low threshold
        min_spread_threshold=0.1   # Test with low threshold
    )
    
    notifier = TelegramNotifier(config)
    await notifier.start()
    
    # Test opportunity notification
    test_opportunity = {
        'pair': 'BTC/USDT',
        'buy_exchange': 'kraken',
        'sell_exchange': 'bybit',
        'spread_percent': 2.5,
        'potential_profit': 75.50
    }
    
    await notifier.notify_opportunity(test_opportunity)
    print("✅ Test notification sent!")
    
    await asyncio.sleep(5)  # Wait for delivery
    await notifier.stop()

if __name__ == "__main__":
    asyncio.run(test_telegram())
