#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_all():
    print("🧪 Test completo SmartArb Engine...")
    
    # Test API base
    try:
        r = requests.get('http://localhost:8001/api/metrics', timeout=5)
        print(f"✅ API Metrics: {r.status_code}")
        data = r.json()
        print(f"   Trades: {data.get('trades_executed', 'N/A')}")
        print(f"   Success Rate: {data.get('success_rate', 'N/A')}%")
    except Exception as e:
        print(f"❌ API Error: {e}")
    
    # Test Telegram
    try:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': f'🧪 SmartArb Engine - API Test Completo\n⏰ {os.popen("date").read().strip()}\n📊 Dashboard: http://192.168.1.161:8001\n✅ Sistema operativo!'
        }
        
        r = requests.post(url, json=data, timeout=10)
        result = r.json()
        
        if result.get('ok'):
            print("✅ Telegram: Message sent successfully!")
        else:
            print(f"❌ Telegram Error: {result}")
            
    except Exception as e:
        print(f"❌ Telegram Connection Error: {e}")

if __name__ == "__main__":
    test_all()
