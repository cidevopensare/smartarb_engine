#!/usr/bin/env python3
"""
SmartArb Engine - Bybit Unified Account Integration
Production-ready integration for Bybit balance handling
"""

import ccxt
import asyncio
from typing import Dict, Optional, Tuple
import structlog

logger = structlog.get_logger("smartarb.bybit")

class BybitUnifiedExchange:
    """Production Bybit handler for SmartArb Engine"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        self.exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'sandbox': testnet,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'unified': True,  # Critical for Unified Account
            },
            'timeout': 30000,  # 30 second timeout
        })
        
        logger.info("Bybit Unified Exchange initialized", testnet=testnet)
    
    async def get_available_balance(self, currency: str = 'USDT') -> Optional[float]:
        """Get available balance for trading in Unified Account"""
        
        try:
            balance = await self.exchange.fetch_balance()
            
            # Extract from raw API response (most reliable)
            if 'info' in balance and 'result' in balance['info']:
                result = balance['info']['result']
                if 'list' in result and len(result['list']) > 0:
                    account = result['list'][0]
                    
                    for coin_data in account.get('coin', []):
                        if coin_data['coin'] == currency:
                            wallet_balance = float(coin_data.get('walletBalance', 0))
                            locked = float(coin_data.get('locked', 0))
                            available = wallet_balance - locked
                            
                            logger.debug(
                                "Bybit balance retrieved",
                                currency=currency,
                                wallet_balance=wallet_balance,
                                locked=locked,
                                available=available
                            )
                            
                            return available if available > 0 else 0.0
            
            # Fallback to CCXT parsed data
            total_amount = balance.get('total', {}).get(currency, 0)
            logger.warning("Using fallback balance method", currency=currency, amount=total_amount)
            return total_amount if total_amount else 0.0
            
        except Exception as e:
            logger.error("Failed to get Bybit balance", currency=currency, error=str(e))
            return None
    
    async def get_trading_balance_info(self, currency: str = 'USDT') -> Optional[Dict]:
        """Get comprehensive balance information for trading"""
        
        try:
            balance = await self.exchange.fetch_balance()
            
            if 'info' in balance and 'result' in balance['info']:
                result = balance['info']['result']
                if 'list' in result and len(result['list']) > 0:
                    account = result['list'][0]
                    
                    for coin_data in account.get('coin', []):
                        if coin_data['coin'] == currency:
                            wallet_balance = float(coin_data.get('walletBalance', 0))
                            locked = float(coin_data.get('locked', 0))
                            equity = float(coin_data.get('equity', 0))
                            usd_value = float(coin_data.get('usdValue', 0))
                            
                            return {
                                'exchange': 'bybit',
                                'currency': currency,
                                'available': wallet_balance - locked,
                                'locked': locked,
                                'total': wallet_balance,
                                'equity': equity,
                                'usd_value': usd_value,
                                'can_trade': (wallet_balance - locked) >= 10,
                                'is_unified_account': True,
                                'collateral_enabled': coin_data.get('marginCollateral', False)
                            }
            
            return None
            
        except Exception as e:
            logger.error("Failed to get trading balance info", error=str(e))
            return None
    
    async def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """Fetch ticker for arbitrage price comparison"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'exchange': 'bybit',
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'last': ticker['last'],
                'timestamp': ticker['timestamp'],
                'spread': ticker['ask'] - ticker['bid'],
                'spread_percent': ((ticker['ask'] - ticker['bid']) / ticker['bid']) * 100
            }
        except Exception as e:
            logger.error("Failed to fetch Bybit ticker", symbol=symbol, error=str(e))
            return None
    
    async def fetch_order_book(self, symbol: str, limit: int = 10) -> Optional[Dict]:
        """Fetch order book for arbitrage analysis"""
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit=limit)
            return {
                'symbol': symbol,
                'exchange': 'bybit',
                'bids': orderbook['bids'][:limit],
                'asks': orderbook['asks'][:limit],
                'timestamp': orderbook['timestamp']
            }
        except Exception as e:
            logger.error("Failed to fetch Bybit orderbook", symbol=symbol, error=str(e))
            return None
    
    async def place_limit_order(self, symbol: str, side: str, amount: float, price: float) -> Optional[Dict]:
        """Place limit order for arbitrage execution"""
        try:
            order = await self.exchange.create_limit_order(symbol, side, amount, price)
            
            logger.info(
                "Bybit order placed",
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                order_id=order['id']
            )
            
            return {
                'exchange': 'bybit',
                'order_id': order['id'],
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': price,
                'status': order['status'],
                'timestamp': order['timestamp']
            }
            
        except Exception as e:
            logger.error(
                "Failed to place Bybit order",
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                error=str(e)
            )
            return None
    
    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict]:
        """Check order status for arbitrage monitoring"""
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return {
                'exchange': 'bybit',
                'order_id': order_id,
                'status': order['status'],
                'filled': order['filled'],
                'remaining': order['remaining'],
                'fee': order.get('fee', {}),
                'timestamp': order['timestamp']
            }
        except Exception as e:
            logger.error("Failed to get Bybit order status", order_id=order_id, error=str(e))
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel order if arbitrage opportunity disappears"""
        try:
            result = await self.exchange.cancel_order(order_id, symbol)
            logger.info("Bybit order cancelled", order_id=order_id, symbol=symbol)
            return True
        except Exception as e:
            logger.error("Failed to cancel Bybit order", order_id=order_id, error=str(e))
            return False
    
    async def close(self):
        """Close exchange connection"""
        try:
            await self.exchange.close()
            logger.info("Bybit connection closed")
        except Exception as e:
            logger.error("Error closing Bybit connection", error=str(e))

# Factory function for easy integration
def create_bybit_exchange(api_key: str, api_secret: str, testnet: bool = False) -> BybitUnifiedExchange:
    """Create Bybit exchange instance for SmartArb Engine"""
    return BybitUnifiedExchange(api_key, api_secret, testnet)

# Quick test function
async def test_bybit_integration():
    """Test Bybit integration with SmartArb Engine"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    exchange = create_bybit_exchange(
        api_key=os.getenv('BYBIT_API_KEY'),
        api_secret=os.getenv('BYBIT_API_SECRET'),
        testnet=False
    )
    
    try:
        # Test balance
        balance_info = await exchange.get_trading_balance_info('USDT')
        if balance_info:
            print(f"✅ Bybit USDT Balance: ${balance_info['available']:.2f} available for trading")
            
        # Test market data
        btc_ticker = await exchange.fetch_ticker('BTC/USDT')
        if btc_ticker:
            print(f"✅ Bybit BTC/USDT: ${btc_ticker['bid']:.2f} / ${btc_ticker['ask']:.2f}")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
        
    finally:
        await exchange.close()

if __name__ == "__main__":
    # Run integration test
    import asyncio
    asyncio.run(test_bybit_integration())
