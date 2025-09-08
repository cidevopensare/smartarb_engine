#!/usr/bin/env python3

import ccxt
import os
from dotenv import load_dotenv

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def main():
    load_dotenv()
    
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.WHITE}🔧 Bybit Unified Account Diagnostic{Colors.END}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
    
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    
    if not api_key or not api_secret:
        print(f"{Colors.RED}❌ API keys not found in .env file{Colors.END}")
        return
    
    # Test different configurations
    configs = [
        {
            'name': 'Unified Account (Basic)',
            'options': {
                'defaultType': 'spot',
                'unified': True,
            }
        },
        {
            'name': 'Unified Account (With AccountType)',
            'options': {
                'defaultType': 'spot',
                'unified': True,
                'accountType': 'UNIFIED',
            }
        },
        {
            'name': 'Classic Spot',
            'options': {
                'defaultType': 'spot',
            }
        },
        {
            'name': 'Contract/Derivatives',
            'options': {
                'defaultType': 'swap',
            }
        }
    ]
    
    best_config = None
    
    for config_info in configs:
        print(f"\n{Colors.BLUE}🧪 Testing: {config_info['name']}{Colors.END}")
        
        try:
            bybit = ccxt.bybit({
                'apiKey': api_key,
                'secret': api_secret,
                'sandbox': False,
                'enableRateLimit': True,
                'options': config_info['options']
            })
            
            balance = bybit.fetch_balance()
            
            usdt_free = balance['free'].get('USDT', 0) or 0
            usdt_used = balance['used'].get('USDT', 0) or 0
            usdt_total = balance['total'].get('USDT', 0) or 0
            
            print(f"  Free:  ${usdt_free:>8.2f}")
            print(f"  Used:  ${usdt_used:>8.2f}")
            print(f"  Total: ${usdt_total:>8.2f}")
            
            if usdt_free > 0:
                print(f"  {Colors.GREEN}🎉 SUCCESS! This config shows FREE funds!{Colors.END}")
                best_config = config_info
            elif usdt_total > 0:
                print(f"  {Colors.YELLOW}⚠️  Funds exist but are USED/LOCKED{Colors.END}")
            else:
                print(f"  {Colors.RED}❌ No funds found{Colors.END}")
                
        except Exception as e:
            print(f"  {Colors.RED}❌ Error: {str(e)[:60]}...{Colors.END}")
    
    # Summary
    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}📊 SUMMARY & SOLUTION{Colors.END}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
    
    if best_config:
        print(f"{Colors.GREEN}✅ SOLUTION FOUND: {best_config['name']}{Colors.END}")
        print(f"\n{Colors.BOLD}💻 Use this configuration in your trading code:{Colors.END}")
        print(f"{Colors.CYAN}bybit = ccxt.bybit({{")
        print(f"    'apiKey': os.getenv('BYBIT_API_KEY'),")
        print(f"    'secret': os.getenv('BYBIT_API_SECRET'),")
        print(f"    'sandbox': False,")
        print(f"    'enableRateLimit': True,")
        print(f"    'options': {best_config['options']}")
        print(f"}}){Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️  No configuration showed free funds{Colors.END}")
        print(f"\n{Colors.BOLD}🔍 Manual check needed:{Colors.END}")
        print(f"1. Login to Bybit app/web")
        print(f"2. Check Assets → Overview")
        print(f"3. Look for any locked/margin positions")
        print(f"4. Check API permissions")

if __name__ == "__main__":
    main()
