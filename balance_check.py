#!/usr/bin/env python3
"""
SmartArb Engine - Balance Checker
Properly check balances on all exchanges
"""

import os
import sys
import ccxt
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

def test_exchange_balance(exchange_id, exchange):
    """Test balance for a single exchange"""
    
    print(f"  💳 Testing {exchange_id.upper()} balance...", end=" ")
    
    try:
        # Try to fetch balance - this is the core test
        balance = exchange.fetch_balance()
        
        # Extract relevant balances
        free_balance = balance.get('free', {})
        total_balance = balance.get('total', {})
        
        # Look for common stablecoins and major cryptos
        relevant_coins = ['USDT', 'USD', 'BTC', 'ETH', 'USDC']
        found_balances = {}
        
        for coin in relevant_coins:
            free_amount = free_balance.get(coin, 0) or 0
            total_amount = total_balance.get(coin, 0) or 0
            
            if free_amount > 0.01 or total_amount > 0.01:  # Ignore dust
                found_balances[coin] = {
                    'free': free_amount,
                    'total': total_amount
                }
        
        if found_balances:
            print(f"{Colors.GREEN}✅{Colors.END}")
            
            # Show balances
            for coin, amounts in found_balances.items():
                if coin in ['USDT', 'USD', 'USDC']:  # Stablecoins
                    print(f"    💰 {coin}: Free ${amounts['free']:,.2f} | Total ${amounts['total']:,.2f}")
                else:  # Crypto
                    print(f"    ₿ {coin}: Free {amounts['free']:.6f} | Total {amounts['total']:.6f}")
            
            # Calculate approximate total value in USD
            total_usd_value = 0
            usdt_value = found_balances.get('USDT', {}).get('free', 0)
            usd_value = found_balances.get('USD', {}).get('free', 0)
            usdc_value = found_balances.get('USDC', {}).get('free', 0)
            
            total_usd_value = usdt_value + usd_value + usdc_value
            
            # For crypto, we'd need current prices, but let's estimate
            btc_amount = found_balances.get('BTC', {}).get('free', 0)
            eth_amount = found_balances.get('ETH', {}).get('free', 0)
            
            # Rough estimates (would be better to fetch real prices)
            if btc_amount > 0:
                estimated_btc_value = btc_amount * 108000  # Rough BTC price from earlier
                total_usd_value += estimated_btc_value
                print(f"    📊 Estimated BTC value: ~${estimated_btc_value:,.2f}")
            
            if eth_amount > 0:
                estimated_eth_value = eth_amount * 4300  # Rough ETH price from earlier
                total_usd_value += estimated_eth_value
                print(f"    📊 Estimated ETH value: ~${estimated_eth_value:,.2f}")
            
            print(f"    {Colors.CYAN}📊 Estimated Total USD Value: ~${total_usd_value:,.2f}{Colors.END}")
            
            # Check if ready for arbitrage
            min_arbitrage_balance = 50  # Minimum $50 for meaningful arbitrage
            is_ready = total_usd_value >= min_arbitrage_balance
            
            ready_status = f"{Colors.GREEN}✅ Ready for arbitrage{Colors.END}" if is_ready else f"{Colors.YELLOW}⚠️  Low balance for arbitrage{Colors.END}"
            print(f"    {ready_status}")
            
            return {
                'status': 'success',
                'balances': found_balances,
                'estimated_usd_value': total_usd_value,
                'ready_for_arbitrage': is_ready
            }
        
        else:
            print(f"{Colors.YELLOW}⚠️ Empty account{Colors.END}")
            return {
                'status': 'empty',
                'balances': {},
                'estimated_usd_value': 0,
                'ready_for_arbitrage': False
            }
    
    except ccxt.AuthenticationError as e:
        print(f"{Colors.RED}❌ Authentication Error{Colors.END}")
        print(f"    {Colors.RED}Error: {str(e)[:60]}...{Colors.END}")
        return {
            'status': 'auth_error',
            'error': str(e)
        }
    
    except ccxt.NetworkError as e:
        print(f"{Colors.RED}❌ Network Error{Colors.END}")
        print(f"    {Colors.RED}Error: {str(e)[:60]}...{Colors.END}")
        return {
            'status': 'network_error',
            'error': str(e)
        }
    
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {str(e)[:50]}...{Colors.END}")
        return {
            'status': 'error',
            'error': str(e)
        }

def main():
    # Load environment variables
    load_dotenv()
    
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.WHITE}💰 SmartArb Engine - Balance Verification{Colors.END}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
    
    # Exchange configurations
    exchanges_config = {
        'bybit': {
            'class': ccxt.bybit,
            'config': {
                'apiKey': os.getenv('BYBIT_API_KEY'),
                'secret': os.getenv('BYBIT_API_SECRET'),
                'sandbox': os.getenv('BYBIT_SANDBOX', 'true').lower() == 'true',
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                }
            }
        },
        'mexc': {
            'class': ccxt.mexc,
            'config': {
                'apiKey': os.getenv('MEXC_API_KEY'),
                'secret': os.getenv('MEXC_API_SECRET'),
                'sandbox': os.getenv('MEXC_SANDBOX', 'true').lower() == 'true',
                'enableRateLimit': True,
            }
        },
        'kraken': {
            'class': ccxt.kraken,
            'config': {
                'apiKey': os.getenv('KRAKEN_API_KEY'),
                'secret': os.getenv('KRAKEN_API_SECRET'),
                'enableRateLimit': True,
            }
        }
    }
    
    results = {}
    total_balance_across_exchanges = 0
    ready_exchanges = 0
    
    print(f"{Colors.BLUE}🔍 Checking balances on all exchanges...\n{Colors.END}")
    
    for exchange_id, config in exchanges_config.items():
        # Check if API keys are configured
        api_key = config['config'].get('apiKey')
        if not api_key or len(api_key) < 10:
            print(f"  💳 Testing {exchange_id.upper()} balance... {Colors.YELLOW}🔐 No API key configured{Colors.END}")
            results[exchange_id] = {'status': 'no_api_key'}
            continue
        
        try:
            # Initialize exchange
            exchange = config['class'](config['config'])
            
            # Test balance
            result = test_exchange_balance(exchange_id, exchange)
            results[exchange_id] = result
            
            if result['status'] == 'success':
                total_balance_across_exchanges += result['estimated_usd_value']
                if result['ready_for_arbitrage']:
                    ready_exchanges += 1
            
        except Exception as e:
            print(f"  💳 Testing {exchange_id.upper()} balance... {Colors.RED}❌ Initialization failed{Colors.END}")
            results[exchange_id] = {'status': 'init_error', 'error': str(e)}
        
        print()  # Empty line between exchanges
    
    # Summary
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}📊 BALANCE SUMMARY{Colors.END}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
    
    print(f"💰 Total Estimated Balance: ${total_balance_across_exchanges:,.2f}")
    print(f"✅ Exchanges Ready for Arbitrage: {ready_exchanges}/3")
    
    if ready_exchanges >= 2:
        print(f"\n{Colors.GREEN}🚀 EXCELLENT: You have sufficient funds on {ready_exchanges} exchanges for arbitrage!{Colors.END}")
        print(f"{Colors.GREEN}✅ System is ready to start trading{Colors.END}")
    elif ready_exchanges == 1:
        print(f"\n{Colors.YELLOW}⚠️  PARTIAL: You have funds on {ready_exchanges} exchange. Need at least 2 for arbitrage.{Colors.END}")
        print(f"{Colors.YELLOW}💡 Consider transferring funds to additional exchanges{Colors.END}")
    else:
        print(f"\n{Colors.RED}❌ SETUP NEEDED: No exchanges ready for arbitrage{Colors.END}")
        print(f"{Colors.YELLOW}💡 Check API keys and fund accounts with at least $50 each{Colors.END}")
    
    # Detailed breakdown
    print(f"\n{Colors.BOLD}📋 Exchange Status:{Colors.END}")
    for exchange_id, result in results.items():
        status_map = {
            'success': f"{Colors.GREEN}✅ Active{Colors.END}",
            'empty': f"{Colors.YELLOW}⚠️  Empty{Colors.END}",
            'auth_error': f"{Colors.RED}❌ Auth Error{Colors.END}",
            'network_error': f"{Colors.RED}❌ Network Error{Colors.END}",
            'no_api_key': f"{Colors.YELLOW}🔐 No API Key{Colors.END}",
            'error': f"{Colors.RED}❌ Error{Colors.END}",
            'init_error': f"{Colors.RED}❌ Init Error{Colors.END}"
        }
        
        status = status_map.get(result['status'], f"{Colors.RED}❌ Unknown{Colors.END}")
        balance_text = ""
        
        if result['status'] == 'success':
            balance_text = f" (~${result['estimated_usd_value']:,.2f})"
        
        print(f"  {exchange_id.upper():8}: {status}{balance_text}")
    
    print(f"\n{Colors.BOLD}💡 Next Steps:{Colors.END}")
    if ready_exchanges >= 2:
        print("  1. ✅ Start with paper trading mode")
        print("  2. 🎯 Run arbitrage opportunity scanner") 
        print("  3. 📊 Monitor performance metrics")
        print("  4. 💰 Gradually increase position sizes")
    else:
        print("  1. 🔐 Verify all API keys are correct")
        print("  2. 💰 Fund accounts with minimum $50-200 each")
        print("  3. 🔄 Re-run this balance check")
        print("  4. 🚀 Start arbitrage trading")

if __name__ == "__main__":
    # Check virtual environment
    if not (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
        print(f"{Colors.RED}⚠️  Please run in virtual environment: source venv/bin/activate{Colors.END}")
        sys.exit(1)
    
    main()
