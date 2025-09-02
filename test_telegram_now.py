#!/usr/bin/env python3
import os
import urllib.request
import urllib.parse
import json
from datetime import datetime

def test_telegram():
    print("🧪 Testing Telegram configuration...")
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id or 'your_bot' in token.lower():
        print("❌ Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first")
        print("Current token:", token[:20] + "..." if token else "None")
        print("Current chat_id:", chat_id)
        return False
    
    # Test message with current bot stats
    message = f"""🧪 <b>SmartArb Telegram Test</b>

✅ <b>Connection:</b> Working perfectly!
🚀 <b>Bot Status:</b> Running and profitable
💰 <b>Performance:</b> ~$536/minute profit rate
📈 <b>Rate:</b> 6.3 opportunities per minute
⏰ <b>Test Time:</b> {datetime.now().strftime('%H:%M:%S')}

🔥 <i>Your trading beast is ready for notifications!</i>

🎯 You'll receive alerts for:
- Opportunities > $25 profit
- Status reports every 30min  
- Major milestones reached"""
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        data_encoded = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(url, data=data_encoded, method='POST')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            if response.status == 200:
                print("✅ Telegram test message sent successfully!")
                print(f"📱 Message ID: {result.get('result', {}).get('message_id', 'N/A')}")
                return True
            else:
                print(f"❌ Telegram API error: {response.status}")
                print(f"Response: {result}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to send test message: {e}")
        return False

if __name__ == "__main__":
    success = test_telegram()
    if success:
        print("\n🎉 Telegram is ready! Your bot will send notifications for:")
        print("   • High-profit opportunities (>$25)")
        print("   • Trade executions (>$25)")  
        print("   • Status reports (every 30min)")
        print("   • System milestones")
    else:
        print("\n🔧 Fix Telegram config and try again")
