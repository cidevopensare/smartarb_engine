#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
from datetime import datetime

# Le tue credenziali reali (dal file .env)
BOT_TOKEN = "8478412531:AAEvX9OdKjc7RQ9tDQUv3WnlhxUzS320U9k"
CHAT_ID = "536544467"

def test_telegram_now():
    print("🧪 Testing SmartArb Telegram Integration...")
    print(f"📱 Bot Token: {BOT_TOKEN[:20]}...")
    print(f"📱 Chat ID: {CHAT_ID}")
    
    # Current bot stats (from your running bot)
    message = """🚀 <b>SmartArb Engine - Telegram Test</b>

✅ <b>Status:</b> Integration successful!
💰 <b>Current Profit:</b> $1,764+ (and growing!)
📈 <b>Performance:</b> 6.3 opportunities/minute
⚡ <b>Rate:</b> One trade every ~10 seconds
⏱️ <b>Test Time:</b> """ + datetime.now().strftime('%H:%M:%S') + """

🔥 <b>Your SmartArb Beast is ready!</b>

🎯 <b>You'll now receive notifications for:</b>
- 💰 Opportunities > $25 profit
- 📊 Status reports every 30 minutes  
- 🏆 Milestones and achievements
- ⚠️ System alerts and errors

🎉 <i>Welcome to automated trading notifications!</i>"""
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        data_encoded = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(url, data=data_encoded, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        print("📡 Sending test message...")
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode())
            if response.status == 200:
                print("✅ SUCCESS! Telegram message sent!")
                print(f"📱 Message ID: {result['result']['message_id']}")
                print(f"📱 Sent to: {result['result']['chat']['first_name']} ({result['result']['chat']['id']})")
                print("\n🎉 CHECK YOUR TELEGRAM NOW!")
                return True
            else:
                print(f"❌ Telegram API error: {response.status}")
                print(f"Response: {result}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to send message: {e}")
        if "chat not found" in str(e).lower():
            print("💡 Make sure you started the bot and sent /start")
        elif "unauthorized" in str(e).lower():
            print("💡 Check if the bot token is correct")
        return False

if __name__ == "__main__":
    success = test_telegram_now()
    if success:
        print("\n🚀 TELEGRAM INTEGRATION READY!")
        print("📱 Your SmartArb bot can now send live notifications!")
        print("💰 Watch for alerts on profitable trades!")
    else:
        print("\n🔧 Something went wrong - let me know what error you see")
