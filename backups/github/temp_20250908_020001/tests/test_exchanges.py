#!/usr/bin/env python3
"""
SmartArb Engine - Exchange API Testing Script
Test delle connessioni API per Bybit, MEXC e Kraken
Optimized for Raspberry Pi 5
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

import ccxt.pro as ccxt
import aiohttp
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class ExchangeAPITester:
    """Professional API tester for SmartArb Engine exchanges"""
    
    def __init__(self):
        self.exchanges = {}
        self.test_results = {}
        self.test_symbols = ["BTC/USDT", "ETH/USDT", "ADA/USDT"]
        
        # Performance tracking
        self.latency_data = {}
        
    def print_header(self):
        """Print test header"""
        print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.WHITE}🚀 SmartArb Engine - Exchange API Test Suite{Colors.END}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.END}")
        print(f"{Colors.YELLOW}📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{Colors.YELLOW}🏗️  Platform: Raspberry Pi 5{Colors.END}")
        print(f"{Colors.YELLOW}💰 Budget: $200 per exchange ($600 total){Colors.END}")
        print()
    
    def initialize_exchanges(self) -> bool:
        """Initialize exchange connections with API keys"""
        print(f"{Colors.BLUE}🔧 Initializing Exchange Connections...{Colors.END}")
        
        exchange_configs = {
            'bybit': {
                'class': ccxt.bybit,
                'config': {
                    'apiKey': os.getenv('BYBIT_API_KEY'),
                    'secret': os.getenv('BYBIT_API_SECRET'),
                    'sandbox': os.getenv('BYBIT_SANDBOX', 'true').lower() == 'true',
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot',  # spot, linear, inverse
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
                    'options': {
                        'createMarketBuyOrderRequiresPrice': False,
                    }
                }
            }
        }
        
        success = True
        
        for exchange_id, config in exchange_configs.items():
            try:
                print(f"  📡 Connecting to {exchange_id.upper()}...", end=" ")
                
                exchange = config['class'](config['config'])
                self.exchanges[exchange_id] = exchange
                self.test_results[exchange_id] = {
                    'connection': True,
                    'api_key_configured': bool(config['config'].get('apiKey')),
                    'sandbox_mode': config['config'].get('sandbox', False)
                }
                
                print(f"{Colors.GREEN}✅{Colors.END}")
                
            except Exception as e:
                print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
                self.test_results[exchange_id] = {
                    'connection': False,
                    'error': str(e)
                }
                success = False
        
        return success
    
    async def test_basic_connectivity(self) -> Dict:
        """Test basic API connectivity"""
        print(f"\n{Colors.BLUE}🌐 Testing Basic API Connectivity...{Colors.END}")
        
        connectivity_results = {}
        
        for exchange_id, exchange in self.exchanges.items():
            print(f"  🔗 Testing {exchange_id.upper()}...", end=" ")
            
            try:
                start_time = time.time()
                
                # Test server time or status
                if hasattr(exchange, 'fetch_status'):
                    status = await exchange.fetch_status()
                    server_time = status.get('updated', time.time())
                else:
                    # Fallback: fetch markets which requires connectivity
                    markets = await exchange.load_markets()
                    server_time = time.time()
                
                latency = (time.time() - start_time) * 1000  # ms
                
                connectivity_results[exchange_id] = {
                    'status': 'connected',
                    'latency_ms': round(latency, 2),
                    'server_time': server_time,
                    'markets_count': len(getattr(exchange, 'markets', {}))
                }
                
                # Store latency data
                self.latency_data[exchange_id] = [latency]
                
                print(f"{Colors.GREEN}✅ ({latency:.1f}ms){Colors.END}")
                
            except Exception as e:
                print(f"{Colors.RED}❌ {str(e)[:50]}...{Colors.END}")
                connectivity_results[exchange_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return connectivity_results
    
    async def test_market_data(self) -> Dict:
        """Test market data fetching for arbitrage pairs"""
        print(f"\n{Colors.BLUE}📊 Testing Market Data Fetching...{Colors.END}")
        
        market_data_results = {}
        
        for exchange_id, exchange in self.exchanges.items():
            if exchange_id not in self.test_results or not self.test_results[exchange_id].get('connection'):
                continue
                
            print(f"  📈 Testing {exchange_id.upper()} market data...")
            
            exchange_results = {}
            
            for symbol in self.test_symbols:
                try:
                    print(f"    📊 {symbol}...", end=" ")
                    
                    start_time = time.time()
                    
                    # Fetch ticker (most important for arbitrage)
                    ticker = await exchange.fetch_ticker(symbol)
                    
                    # Fetch orderbook (needed for arbitrage calculations)
                    orderbook = await exchange.fetch_order_book(symbol, limit=5)
                    
                    latency = (time.time() - start_time) * 1000
                    
                    # Add to latency tracking
                    if exchange_id in self.latency_data:
                        self.latency_data[exchange_id].append(latency)
                    
                    exchange_results[symbol] = {
                        'ticker_success': True,
                        'orderbook_success': True,
                        'bid': ticker['bid'],
                        'ask': ticker['ask'],
                        'spread_percent': round(((ticker['ask'] - ticker['bid']) / ticker['bid']) * 100, 4),
                        'volume_24h': ticker['baseVolume'],
                        'latency_ms': round(latency, 2)
                    }
                    
                    print(f"{Colors.GREEN}✅ Bid: ${ticker['bid']:,.2f}, Ask: ${ticker['ask']:,.2f}{Colors.END}")
                    
                except Exception as e:
                    print(f"{Colors.RED}❌ {str(e)[:30]}...{Colors.END}")
                    exchange_results[symbol] = {
                        'ticker_success': False,
                        'orderbook_success': False,
                        'error': str(e)
                    }
            
            market_data_results[exchange_id] = exchange_results
        
        return market_data_results
    
    async def test_account_access(self) -> Dict:
        """Test account access and balance fetching (if API keys provided)"""
        print(f"\n{Colors.BLUE}💰 Testing Account Access...{Colors.END}")
        
        account_results = {}
        
        for exchange_id, exchange in self.exchanges.items():
            if exchange_id not in self.test_results or not self.test_results[exchange_id].get('connection'):
                continue
                
            if not self.test_results[exchange_id].get('api_key_configured'):
                print(f"  🔐 {exchange_id.upper()}: {Colors.YELLOW}No API key configured - skipping account test{Colors.END}")
                account_results[exchange_id] = {'status': 'no_api_key'}
                continue
            
            try:
                print(f"  💳 Testing {exchange_id.upper()} account access...", end=" ")
                
                # Fetch balance
                balance = await exchange.fetch_balance()
                
                # Get trading fees
                if hasattr(exchange, 'fetch_trading_fees'):
                    trading_fees = await exchange.fetch_trading_fees()
                    maker_fee = trading_fees.get('maker', 'N/A')
                    taker_fee = trading_fees.get('taker', 'N/A')
                else:
                    maker_fee = taker_fee = 'N/A'
                
                # Calculate total balance in USDT
                total_usdt = 0
                usdt_balance = balance['free'].get('USDT', 0) or balance['free'].get('USD', 0)
                btc_balance = balance['free'].get('BTC', 0)
                eth_balance = balance['free'].get('ETH', 0)
                
                account_results[exchange_id] = {
                    'status': 'connected',
                    'usdt_balance': usdt_balance,
                    'btc_balance': btc_balance,
                    'eth_balance': eth_balance,
                    'maker_fee': maker_fee,
                    'taker_fee': taker_fee,
                    'can_trade': usdt_balance > 10,  # Minimum for arbitrage
                    'sandbox_mode': self.test_results[exchange_id].get('sandbox_mode', False)
                }
                
                print(f"{Colors.GREEN}✅ USDT: ${usdt_balance:,.2f}{Colors.END}")
                
            except Exception as e:
                print(f"{Colors.RED}❌ {str(e)[:50]}...{Colors.END}")
                account_results[exchange_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return account_results
    
    async def analyze_arbitrage_opportunities(self, market_data: Dict) -> List[Dict]:
        """Analyze potential arbitrage opportunities from test data"""
        print(f"\n{Colors.BLUE}⚡ Analyzing Arbitrage Opportunities...{Colors.END}")
        
        opportunities = []
        
        for symbol in self.test_symbols:
            print(f"  🔍 Analyzing {symbol}...")
            
            # Collect prices from all exchanges
            prices = {}
            for exchange_id, data in market_data.items():
                if symbol in data and data[symbol].get('ticker_success'):
                    prices[exchange_id] = {
                        'bid': data[symbol]['bid'],
                        'ask': data[symbol]['ask']
                    }
            
            if len(prices) < 2:
                continue
            
            # Find arbitrage opportunities
            exchange_pairs = [(ex1, ex2) for ex1 in prices.keys() for ex2 in prices.keys() if ex1 != ex2]
            
            for buy_exchange, sell_exchange in exchange_pairs:
                buy_price = prices[buy_exchange]['ask']  # We buy at ask
                sell_price = prices[sell_exchange]['bid']  # We sell at bid
                
                if sell_price > buy_price:
                    profit_absolute = sell_price - buy_price
                    profit_percent = (profit_absolute / buy_price) * 100
                    
                    # Consider trading fees (estimate 0.1% per trade)
                    estimated_fees_percent = 0.2  # 0.1% per exchange
                    net_profit_percent = profit_percent - estimated_fees_percent
                    
                    if net_profit_percent > 0:
                        opportunity = {
                            'symbol': symbol,
                            'buy_exchange': buy_exchange,
                            'sell_exchange': sell_exchange,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'profit_absolute': profit_absolute,
                            'profit_percent': round(profit_percent, 4),
                            'net_profit_percent': round(net_profit_percent, 4),
                            'potential_profit_200usd': round((net_profit_percent / 100) * 200, 2)
                        }
                        opportunities.append(opportunity)
                        
                        status_color = Colors.GREEN if net_profit_percent > 0.2 else Colors.YELLOW
                        print(f"    {status_color}💰 {buy_exchange.upper()}→{sell_exchange.upper()}: "
                              f"{net_profit_percent:.3f}% (${opportunity['potential_profit_200usd']:.2f} on $200){Colors.END}")
        
        # Sort by profitability
        opportunities.sort(key=lambda x: x['net_profit_percent'], reverse=True)
        
        return opportunities
    
    def generate_performance_report(self) -> Dict:
        """Generate performance analysis report"""
        print(f"\n{Colors.BLUE}📊 Generating Performance Report...{Colors.END}")
        
        performance_data = {}
        
        for exchange_id, latencies in self.latency_data.items():
            if latencies:
                performance_data[exchange_id] = {
                    'avg_latency_ms': round(sum(latencies) / len(latencies), 2),
                    'min_latency_ms': round(min(latencies), 2),
                    'max_latency_ms': round(max(latencies), 2),
                    'total_requests': len(latencies),
                    'performance_score': self._calculate_performance_score(latencies)
                }
        
        return performance_data
    
    def _calculate_performance_score(self, latencies: List[float]) -> str:
        """Calculate performance score based on latency"""
        avg_latency = sum(latencies) / len(latencies)
        
        if avg_latency < 100:
            return "🚀 Excellent"
        elif avg_latency < 200:
            return "✅ Good"
        elif avg_latency < 500:
            return "⚠️ Fair"
        else:
            return "🐌 Poor"
    
    def print_summary_report(self, connectivity: Dict, market_data: Dict, 
                           account_data: Dict, opportunities: List[Dict], 
                           performance: Dict):
        """Print comprehensive test summary"""
        
        print(f"\n{Colors.MAGENTA}{'=' * 60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.WHITE}📋 SMARTARB ENGINE - TEST SUMMARY REPORT{Colors.END}")
        print(f"{Colors.MAGENTA}{'=' * 60}{Colors.END}")
        
        # Connection Status
        print(f"\n{Colors.BOLD}🔗 CONNECTION STATUS:{Colors.END}")
        for exchange_id in ['bybit', 'mexc', 'kraken']:
            status = connectivity.get(exchange_id, {})
            if status.get('status') == 'connected':
                latency = status.get('latency_ms', 0)
                print(f"  {Colors.GREEN}✅ {exchange_id.upper():8}: Connected ({latency}ms){Colors.END}")
            else:
                print(f"  {Colors.RED}❌ {exchange_id.upper():8}: Failed{Colors.END}")
        
        # Performance Analysis
        print(f"\n{Colors.BOLD}⚡ PERFORMANCE ANALYSIS:{Colors.END}")
        for exchange_id, perf in performance.items():
            print(f"  📊 {exchange_id.upper():8}: {perf['performance_score']} "
                  f"(Avg: {perf['avg_latency_ms']}ms, Requests: {perf['total_requests']})")
        
        # Trading Readiness
        print(f"\n{Colors.BOLD}💰 TRADING READINESS:{Colors.END}")
        ready_exchanges = 0
        for exchange_id in ['bybit', 'mexc', 'kraken']:
            acc_data = account_data.get(exchange_id, {})
            if acc_data.get('status') == 'connected':
                balance = acc_data.get('usdt_balance', 0)
                can_trade = acc_data.get('can_trade', False)
                sandbox = " (SANDBOX)" if acc_data.get('sandbox_mode') else ""
                
                if can_trade:
                    print(f"  {Colors.GREEN}✅ {exchange_id.upper():8}: Ready - ${balance:,.2f} USDT{sandbox}{Colors.END}")
                    ready_exchanges += 1
                else:
                    print(f"  {Colors.YELLOW}⚠️  {exchange_id.upper():8}: Low balance - ${balance:,.2f} USDT{sandbox}{Colors.END}")
            elif acc_data.get('status') == 'no_api_key':
                print(f"  {Colors.YELLOW}🔐 {exchange_id.upper():8}: API key not configured{Colors.END}")
            else:
                print(f"  {Colors.RED}❌ {exchange_id.upper():8}: Connection failed{Colors.END}")
        
        # Arbitrage Opportunities
        print(f"\n{Colors.BOLD}🎯 ARBITRAGE OPPORTUNITIES DETECTED:{Colors.END}")
        if opportunities:
            print(f"  {Colors.GREEN}Found {len(opportunities)} opportunities:{Colors.END}")
            
            # Show top 3 opportunities
            for i, opp in enumerate(opportunities[:3], 1):
                profit_color = Colors.GREEN if opp['net_profit_percent'] > 0.2 else Colors.YELLOW
                print(f"    {profit_color}{i}. {opp['symbol']}: {opp['buy_exchange'].upper()}→{opp['sell_exchange'].upper()} "
                      f"({opp['net_profit_percent']:.3f}% = ${opp['potential_profit_200usd']:.2f} on $200){Colors.END}")
        else:
            print(f"  {Colors.YELLOW}⚠️  No profitable opportunities found (normal in current market){Colors.END}")
        
        # System Recommendations  
        print(f"\n{Colors.BOLD}🎛️ SYSTEM RECOMMENDATIONS:{Colors.END}")
        
        if ready_exchanges >= 2:
            print(f"  {Colors.GREEN}✅ Ready to start arbitrage trading!{Colors.END}")
        else:
            print(f"  {Colors.YELLOW}⚠️  Configure API keys for at least 2 exchanges{Colors.END}")
        
        if any(perf.get('avg_latency_ms', 1000) > 300 for perf in performance.values()):
            print(f"  {Colors.YELLOW}⚠️  Consider optimizing network connection (high latency detected){Colors.END}")
        else:
            print(f"  {Colors.GREEN}✅ Network performance is good for arbitrage{Colors.END}")
        
        print(f"\n{Colors.BOLD}💡 NEXT STEPS:{Colors.END}")
        print(f"  1. Configure missing API keys in .env file")
        print(f"  2. Fund accounts with initial $200 per exchange")
        print(f"  3. Start with paper trading mode")
        print(f"  4. Monitor performance and adjust parameters")
        
        print(f"\n{Colors.MAGENTA}{'=' * 60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}🚀 SmartArb Engine API Test Complete!{Colors.END}")
        print(f"{Colors.MAGENTA}{'=' * 60}{Colors.END}")
    
    async def close_connections(self):
        """Close all exchange connections"""
        for exchange in self.exchanges.values():
            if hasattr(exchange, 'close'):
                await exchange.close()

async def main():
    """Main test execution function"""
    
    tester = ExchangeAPITester()
    tester.print_header()
    
    try:
        # Initialize exchanges
        if not tester.initialize_exchanges():
            print(f"{Colors.RED}❌ Failed to initialize exchanges. Check API configuration.{Colors.END}")
            return
        
        # Run tests
        connectivity_results = await tester.test_basic_connectivity()
        market_data_results = await tester.test_market_data()
        account_results = await tester.test_account_access()
        
        # Analyze arbitrage opportunities
        opportunities = await tester.analyze_arbitrage_opportunities(market_data_results)
        
        # Generate performance report
        performance_results = tester.generate_performance_report()
        
        # Print comprehensive summary
        tester.print_summary_report(
            connectivity_results,
            market_data_results, 
            account_results,
            opportunities,
            performance_results
        )
        
        # Save detailed results to JSON
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'connectivity': connectivity_results,
            'market_data': market_data_results,
            'accounts': account_results,
            'opportunities': opportunities,
            'performance': performance_results
        }
        
        with open(f'test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        print(f"\n{Colors.BLUE}💾 Detailed results saved to test_results_*.json{Colors.END}")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Test failed with error: {e}{Colors.END}")
    finally:
        await tester.close_connections()

if __name__ == "__main__":
    # Check if running in virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"{Colors.RED}⚠️  Please run this script in your virtual environment!{Colors.END}")
        print(f"Activate with: source venv/bin/activate")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Program terminated by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Critical error: {e}{Colors.END}")
        sys.exit(1)
