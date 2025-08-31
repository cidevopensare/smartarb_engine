#!/usr/bin/env python3
"""
SmartArb Engine - Simple Exchange Test
Quick test to verify CCXT and exchange connections
"""

import sys
import os
from datetime import datetime

print("🚀 SmartArb Engine - Simple Exchange Test")
print("=" * 50)

# Test 1: Check Python environment
print(f"Python version: {sys.version}")
print(f"Virtual env: {hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)}")
print(f"Working directory: {os.getcwd()}")

# Test 2: Import basic modules
print("\n📦 Testing imports...")
try:
    import ccxt
    print(f"✅ CCXT: {ccxt.__version__}")
except ImportError as e:
    print(f"❌ CCXT: {e}")
    print("Run: pip install ccxt")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("✅ python-dotenv: OK")
except ImportError:
    print("❌ python-dotenv: Missing")
    print("Run: pip install python-dotenv")

try:
    import aiohttp
    print("✅ aiohttp: OK")
except ImportError:
    print("❌ aiohttp: Missing") 
    print("Run: pip install aiohttp")

try:
    import asyncio
    print("✅ asyncio: OK")
except ImportError:
    print("❌ asyncio: Missing")

# Test 3: Check .env file
print("\n🔧 Checking configuration...")
load_dotenv()

env_file_exists = os.path.exists('.env')
print(f"📄 .env file exists: {env_file_exists}")

if env_file_exists:
    with open('.env', 'r') as f:
        lines = f.readlines()
    
    api_keys_configured = []
    for line in lines:
        if 'API_KEY' in line and not line.startswith('#'):
            key_name = line.split('=')[0]
            has_value = len(line.split('=')[1].strip()) > 10
            api_keys_configured.append((key_name, has_value))
    
    print("🔑 API Keys configured:")
    for key_name, has_value in api_keys_configured:
        status = "✅" if has_value else "❌"
        print(f"  {status} {key_name}")

# Test 4: Basic CCXT exchange initialization
print("\n🌐 Testing exchange connections...")

exchanges_to_test = {
    'bybit': ccxt.bybit,
    'mexc': ccxt.mexc, 
    'kraken': ccxt.kraken
}

for exchange_id, exchange_class in exchanges_to_test.items():
    try:
        # Test without API keys first (public endpoints)
        exchange = exchange_class({
            'enableRateLimit': True,
            'sandbox': True
        })
        
        # Test loading markets (public endpoint)
        markets = exchange.load_markets()
        market_count = len(markets)
        
        print(f"✅ {exchange_id.upper()}: Connected ({market_count} markets)")
        
    except Exception as e:
        print(f"❌ {exchange_id.upper()}: {str(e)[:50]}...")

# Test 5: Quick Redis connection test
print("\n🔧 Testing Redis connection...")
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.ping()
    print("✅ Redis: Connected")
    
    # Show Redis memory usage
    info = r.info('memory')
    used_memory = info.get('used_memory_human', 'Unknown')
    max_memory = info.get('maxmemory_human', 'No limit') 
    print(f"📊 Redis memory: {used_memory} / {max_memory}")
    
except Exception as e:
    print(f"❌ Redis: {e}")

# Test 6: System resources
print("\n🖥️  System resources...")
try:
    import psutil
    
    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=1)
    
    print(f"💾 RAM: {memory.percent}% used ({memory.used // 1024**2}MB / {memory.total // 1024**2}MB)")
    print(f"🖥️  CPU: {cpu_percent}%")
    
    # Check temperature (Raspberry Pi specific)
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp_c = int(f.read()) / 1000
            print(f"🌡️  CPU Temperature: {temp_c:.1f}°C")
    except:
        print("🌡️  CPU Temperature: Not available")
        
except ImportError:
    print("⚠️  psutil not available for system monitoring")

print("\n" + "=" * 50)
print("🏁 Test completed!")
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Final recommendations
print("\n💡 Next steps:")
print("1. If CCXT is missing: pip install ccxt")
print("2. Configure API keys in .env file") 
print("3. Run full test: python test_exchanges.py")
print("4. Start with paper trading mode")
