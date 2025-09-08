#!/usr/bin/env python3
“””
Database Setup Script for SmartArb Engine
Handles PostgreSQL and Redis database initialization, migration, and management
“””

import asyncio
import asyncpg
import redis
import sys
import os
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime

# Add src to path

sys.path.insert(0, str(Path(**file**).parent.parent))

from src.utils.config import ConfigManager
from src.utils.logging import setup_logging

logger = structlog.get_logger(“database_setup”)

class DatabaseSetupManager:
“”“Database setup and management”””

```
def __init__(self, config_path: str = "config/settings.yaml"):
    self.config_manager = ConfigManager(config_path)
    self.config = self.config_manager.get_config()
    
    # Setup logging
    setup_logging(self.config)
    
    # Database configurations
    self.postgres_config = self.config.get('database', {}).get('postgresql', {})
    self.redis_config = self.config.get('database', {}).get('redis', {})
    
    # Connection pools
    self.postgres_pool = None
    self.redis_client = None
    
    self.logger = structlog.get_logger("db_setup")

async def initialize_all(self) -> bool:
    """Initialize all databases"""
    
    success = True
    
    # Initialize PostgreSQL
    if self.postgres_config.get('enabled', False):
        postgres_success = await self.initialize_postgresql()
        success = success and postgres_success
    else:
        self.logger.info("postgresql_disabled")
    
    # Initialize Redis
    if self.redis_config.get('enabled', False):
        redis_success = await self.initialize_redis()
        success = success and redis_success
    else:
        self.logger.info("redis_disabled")
    
    return success

async def initialize_postgresql(self) -> bool:
    """Initialize PostgreSQL database"""
    
    try:
        self.logger.info("initializing_postgresql")
        
        # Create database if it doesn't exist
        await self._create_database_if_not_exists()
        
        # Create connection pool
        await self._create_postgres_pool()
        
        # Create tables
        await self._create_tables()
        
        # Create indexes
        await self._create_indexes()
        
        # Insert initial data
        await self._insert_initial_data()
        
        self.logger.info("postgresql_initialization_completed")
        return True
        
    except Exception as e:
        self.logger.error("postgresql_initialization_failed", error=str(e))
        return False

async def initialize_redis(self) -> bool:
    """Initialize Redis"""
    
    try:
        self.logger.info("initializing_redis")
        
        # Create Redis client
        self.redis_client = redis.Redis(
            host=self.redis_config.get('host', 'localhost'),
            port=self.redis_config.get('port', 6379),
            db=self.redis_config.get('db', 0),
            password=self.redis_config.get('password', None),
            decode_responses=True,
            socket_timeout=self.redis_config.get('connection_timeout', 5)
        )
        
        # Test connection
        self.redis_client.ping()
        
        # Initialize Redis schema
        await self._setup_redis_schema()
        
        self.logger.info("redis_initialization_completed")
        return True
        
    except Exception as e:
        self.logger.error("redis_initialization_failed", error=str(e))
        return False

async def _create_database_if_not_exists(self):
    """Create PostgreSQL database if it doesn't exist"""
    
    # Connect to default postgres database to create our database
    conn = await asyncpg.connect(
        host=self.postgres_config.get('host', 'localhost'),
        port=self.postgres_config.get('port', 5432),
        user=self.postgres_config.get('username', 'postgres'),
        password=self.postgres_config.get('password', ''),
        database='postgres'
    )
    
    try:
        database_name = self.postgres_config.get('database', 'smartarb')
        
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_name
        )
        
        if not exists:
            # Create database
            await conn.execute(f'CREATE DATABASE "{database_name}"')
            self.logger.info("database_created", database=database_name)
        else:
            self.logger.info("database_exists", database=database_name)
            
    finally:
        await conn.close()

async def _create_postgres_pool(self):
    """Create PostgreSQL connection pool"""
    
    self.postgres_pool = await asyncpg.create_pool(
        host=self.postgres_config.get('host', 'localhost'),
        port=self.postgres_config.get('port', 5432),
        user=self.postgres_config.get('username', 'smartarb_user'),
        password=self.postgres_config.get('password', ''),
        database=self.postgres_config.get('database', 'smartarb'),
        min_size=self.postgres_config.get('min_connections', 2),
        max_size=self.postgres_config.get('max_connections', 8),
        command_timeout=self.postgres_config.get('connection_timeout', 30)
    )
    
    self.logger.info("postgres_pool_created")

async def _create_tables(self):
    """Create database tables"""
    
    async with self.postgres_pool.acquire() as conn:
        
        # Exchanges table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS exchanges (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                display_name VARCHAR(100) NOT NULL,
                enabled BOOLEAN DEFAULT FALSE,
                api_status VARCHAR(20) DEFAULT 'unknown',
                last_health_check TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Trading pairs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trading_pairs (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                base_asset VARCHAR(10) NOT NULL,
                quote_asset VARCHAR(10) NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Arbitrage opportunities table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                id UUID PRIMARY KEY,
                strategy_type VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                buy_exchange VARCHAR(50) NOT NULL,
                sell_exchange VARCHAR(50) NOT NULL,
                buy_price DECIMAL(20, 8) NOT NULL,
                sell_price DECIMAL(20, 8) NOT NULL,
                spread DECIMAL(20, 8) NOT NULL,
                spread_percentage DECIMAL(10, 6) NOT NULL,
                potential_profit DECIMAL(20, 8) NOT NULL,
                required_capital DECIMAL(20, 8) NOT NULL,
                confidence DECIMAL(3, 2) NOT NULL,
                risk_score DECIMAL(3, 2) NOT NULL,
                status VARCHAR(20) NOT NULL,
                detected_time TIMESTAMP NOT NULL,
                expiry_time TIMESTAMP NOT NULL,
                executed_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Orders table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id VARCHAR(100) PRIMARY KEY,
                exchange VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                order_type VARCHAR(20) NOT NULL,
                amount DECIMAL(20, 8) NOT NULL,
                price DECIMAL(20, 8),
                status VARCHAR(20) NOT NULL,
                filled DECIMAL(20, 8) DEFAULT 0,
                remaining DECIMAL(20, 8) DEFAULT 0,
                cost DECIMAL(20, 8) DEFAULT 0,
                fee DECIMAL(20, 8) DEFAULT 0,
                fee_currency VARCHAR(10),
                opportunity_id UUID,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (opportunity_id) REFERENCES arbitrage_opportunities(id)
            )
        """)
        
        # Trades table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id VARCHAR(100) PRIMARY KEY,
                exchange VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                amount DECIMAL(20, 8) NOT NULL,
                price DECIMAL(20, 8) NOT NULL,
                cost DECIMAL(20, 8) NOT NULL,
                fee DECIMAL(20, 8) DEFAULT 0,
                fee_currency VARCHAR(10),
                order_id VARCHAR(100),
                opportunity_id UUID,
                executed_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (opportunity_id) REFERENCES arbitrage_opportunities(id)
            )
        """)
        
        # Portfolio snapshots table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id SERIAL PRIMARY KEY,
                total_value_usd DECIMAL(20, 8) NOT NULL,
                pnl_24h DECIMAL(20, 8) DEFAULT 0,
                pnl_percentage_24h DECIMAL(10, 6) DEFAULT 0,
                asset_count INTEGER DEFAULT 0,
                exchange_count INTEGER DEFAULT 0,
                snapshot_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Risk events table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                id SERIAL PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                description TEXT NOT NULL,
                risk_score DECIMAL(3, 2),
                triggered_by VARCHAR(100),
                metadata JSONB,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # AI analysis table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_analyses (
                id VARCHAR(100) PRIMARY KEY,
                analysis_type VARCHAR(50) NOT NULL,
                focus VARCHAR(100) NOT NULL,
                summary TEXT NOT NULL,
                key_findings JSONB,
                recommendations JSONB,
                confidence_score DECIMAL(3, 2) NOT NULL,
                processing_time DECIMAL(10, 6) NOT NULL,
                status VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # System metrics table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id SERIAL PRIMARY KEY,
                metric_name VARCHAR(100) NOT NULL,
                metric_value DECIMAL(20, 8) NOT NULL,
                metric_unit VARCHAR(20),
                component VARCHAR(50) NOT NULL,
                metadata JSONB,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.logger.info("database_tables_created")

async def _create_indexes(self):
    """Create database indexes for performance"""
    
    async with self.postgres_pool.acquire() as conn:
        
        # Arbitrage opportunities indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_opportunities_symbol_status 
            ON arbitrage_opportunities(symbol, status)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_opportunities_detected_time 
            ON arbitrage_opportunities(detected_time)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_opportunities_strategy_type 
            ON arbitrage_opportunities(strategy_type)
        """)
        
        # Orders indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_exchange_symbol 
            ON orders(exchange, symbol)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_status 
            ON orders(status)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_created_at 
            ON orders(created_at)
        """)
        
        # Trades indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_exchange_symbol 
            ON trades(exchange, symbol)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_executed_at 
            ON trades(executed_at)
        """)
        
        # Portfolio snapshots indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_portfolio_created_at 
            ON portfolio_snapshots(created_at)
        """)
        
        # Risk events indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_risk_events_type_severity 
            ON risk_events(event_type, severity)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_risk_events_created_at 
            ON risk_events(created_at)
        """)
        
        # AI analyses indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_analyses_type 
            ON ai_analyses(analysis_type)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_analyses_created_at 
            ON ai_analyses(created_at)
        """)
        
        # System metrics indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_name_component 
            ON system_metrics(metric_name, component)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at 
            ON system_metrics(recorded_at)
        """)
        
        self.logger.info("database_indexes_created")

async def _insert_initial_data(self):
    """Insert initial data"""
    
    async with self.postgres_pool.acquire() as conn:
        
        # Insert supported exchanges
        exchanges = [
            ('kraken', 'Kraken'),
            ('bybit', 'Bybit'),
            ('mexc', 'MEXC')
        ]
        
        for exchange_name, display_name in exchanges:
            await conn.execute("""
                INSERT INTO exchanges (name, display_name, enabled) 
                VALUES ($1, $2, $3)
                ON CONFLICT (name) DO UPDATE SET 
                display_name = EXCLUDED.display_name,
                updated_at = CURRENT_TIMESTAMP
            """, exchange_name, display_name, False)
        
        # Insert supported trading pairs
        trading_pairs = [
            ('BTC/USDT', 'BTC', 'USDT'),
            ('ETH/USDT', 'ETH', 'USDT'),
            ('BNB/USDT', 'BNB', 'USDT'),
            ('ADA/USDT', 'ADA', 'USDT'),
            ('DOT/USDT', 'DOT', 'USDT'),
            ('LINK/USDT', 'LINK', 'USDT'),
            ('MATIC/USDT', 'MATIC', 'USDT')
        ]
        
        for symbol, base, quote in trading_pairs:
            await conn.execute("""
                INSERT INTO trading_pairs (symbol, base_asset, quote_asset) 
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
            """, symbol, base, quote)
        
        self.logger.info("initial_data_inserted")

async def _setup_redis_schema(self):
    """Setup Redis schema and initial data"""
    
    # Redis key patterns used by SmartArb Engine
    key_patterns = {
        'ticker': 'ticker:{exchange}:{symbol}',
        'orderbook': 'orderbook:{exchange}:{symbol}',
        'balance': 'balance:{exchange}',
        'opportunity': 'opportunity:{id}',
        'portfolio': 'portfolio:snapshot',
        'risk': 'risk:metrics',
        'ai': 'ai:analysis:{id}',
        'system': 'system:status'
    }
    
    # Store key patterns for reference
    self.redis_client.hset('smartarb:schema', mapping=key_patterns)
    
    # Set initial system status
    system_status = {
        'engine_status': 'stopped',
        'last_startup': '',
        'version': '1.0.0',
        'initialized_at': datetime.now().isoformat()
    }
    
    self.redis_client.hset('system:status', mapping=system_status)
    
    # Set cache expiration policies
    cache_ttl = {
        'ticker': 10,       # 10 seconds
        'orderbook': 5,     # 5 seconds
        'balance': 30,      # 30 seconds
        'portfolio': 60,    # 1 minute
        'risk': 300,        # 5 minutes
    }
    
    self.redis_client.hset('smartarb:cache_ttl', mapping=cache_ttl)
    
    self.logger.info("redis_schema_setup_completed")

async def migrate_database(self) -> bool:
    """Run database migrations"""
    
    try:
        self.logger.info("running_database_migrations")
        
        # Create migration tracking table
        async with self.postgres_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Run migrations
        migrations_dir = Path(__file__).parent / 'migrations'
        if migrations_dir.exists():
            migration_files = sorted(migrations_dir.glob('*.sql'))
            
            for migration_file in migration_files:
                await self._run_migration(migration_file)
        
        self.logger.info("database_migrations_completed")
        return True
        
    except Exception as e:
        self.logger.error("database_migration_failed", error=str(e))
        return False

async def _run_migration(self, migration_file: Path):
    """Run a single migration file"""
    
    migration_name = migration_file.stem
    
    async with self.postgres_pool.acquire() as conn:
        # Check if migration already applied
        exists = await conn.fetchval(
            "SELECT 1 FROM migrations WHERE migration_name = $1",
            migration_name
        )
        
        if exists:
            self.logger.debug("migration_already_applied", migration=migration_name)
            return
        
        # Read and execute migration
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        await conn.execute(migration_sql)
        
        # Record migration
        await conn.execute(
            "INSERT INTO migrations (migration_name) VALUES ($1)",
            migration_name
        )
        
        self.logger.info("migration_applied", migration=migration_name)

async def reset_database(self) -> bool:
    """Reset database (DROP ALL DATA)"""
    
    try:
        self.logger.warning("resetting_database_all_data_will_be_lost")
        
        if self.postgres_pool:
            async with self.postgres_pool.acquire() as conn:
                # Drop all tables
                tables = [
                    'system_metrics', 'ai_analyses', 'risk_events',
                    'portfolio_snapshots', 'trades', 'orders',
                    'arbitrage_opportunities', 'trading_pairs',
                    'exchanges', 'migrations'
                ]
                
                for table in tables:
                    await conn.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
                
            self.logger.info("postgresql_tables_dropped")
        
        if self.redis_client:
            self.redis_client.flushdb()
            self.logger.info("redis_database_flushed")
        
        # Recreate everything
        await self.initialize_all()
        
        self.logger.info("database_reset_completed")
        return True
        
    except Exception as e:
        self.logger.error("database_reset_failed", error=str(e))
        return False

async def check_database_health(self) -> Dict[str, Any]:
    """Check database health and connectivity"""
    
    health_status = {
        'postgresql': {'status': 'unknown', 'error': None},
        'redis': {'status': 'unknown', 'error': None}
    }
    
    # Check PostgreSQL
    if self.postgres_config.get('enabled', False):
        try:
            if not self.postgres_pool:
                await self._create_postgres_pool()
            
            async with self.postgres_pool.acquire() as conn:
                result = await conn.fetchval('SELECT 1')
                if result == 1:
                    health_status['postgresql']['status'] = 'healthy'
                
        except Exception as e:
            health_status['postgresql']['status'] = 'error'
            health_status['postgresql']['error'] = str(e)
    else:
        health_status['postgresql']['status'] = 'disabled'
    
    # Check Redis
    if self.redis_config.get('enabled', False):
        try:
            if not self.redis_client:
                await self.initialize_redis()
            
            self.redis_client.ping()
            health_status['redis']['status'] = 'healthy'
            
        except Exception as e:
            health_status['redis']['status'] = 'error'
            health_status['redis']['error'] = str(e)
    else:
        health_status['redis']['status'] = 'disabled'
    
    return health_status

async def cleanup(self):
    """Cleanup database connections"""
    
    if self.postgres_pool:
        await self.postgres_pool.close()
        self.logger.info("postgres_pool_closed")
    
    if self.redis_client:
        self.redis_client.close()
        self.logger.info("redis_connection_closed")
```

async def main():
“”“Main setup function”””

```
parser = argparse.ArgumentParser(description='SmartArb Engine Database Setup')
parser.add_argument('--init', action='store_true', 
                   help='Initialize databases')
parser.add_argument('--migrate', action='store_true',
                   help='Run database migrations')
parser.add_argument('--reset', action='store_true',
                   help='Reset databases (WARNING: destroys all data)')
parser.add_argument('--health', action='store_true',
                   help='Check database health')
parser.add_argument('--config', '-c', default='config/settings.yaml',
                   help='Configuration file path')

args = parser.parse_args()

setup_manager = DatabaseSetupManager(args.config)

try:
    if args.init:
        print("🔧 Initializing databases...")
        success = await setup_manager.initialize_all()
        if success:
            print("✅ Database initialization completed successfully!")
            return 0
        else:
            print("❌ Database initialization failed!")
            return 1
    
    elif args.migrate:
        print("🔄 Running database migrations...")
        success = await setup_manager.migrate_database()
        if success:
            print("✅ Database migrations completed successfully!")
            return 0
        else:
            print("❌ Database migrations failed!")
            return 1
    
    elif args.reset:
        print("⚠️  WARNING: This will destroy ALL data!")
        print("Are you sure you want to reset the databases? (y/N): ", end='')
        
        confirmation = input().strip().lower()
        if confirmation == 'y':
            print("🗑️  Resetting databases...")
            success = await setup_manager.reset_database()
            if success:
                print("✅ Database reset completed successfully!")
                return 0
            else:
                print("❌ Database reset failed!")
                return 1
        else:
            print("❌ Reset cancelled.")
            return 0
    
    elif args.health:
        print("🔍 Checking database health...")
        health_status = await setup_manager.check_database_health()
        
        print("\n📊 Database Health Status:")
        for db_name, status in health_status.items():
            status_emoji = {
                'healthy': '✅',
                'error': '❌', 
                'disabled': '⚪',
                'unknown': '❓'
            }.get(status['status'], '❓')
            
            print(f"  {status_emoji} {db_name.upper()}: {status['status']}")
            if status['error']:
                print(f"    Error: {status['error']}")
        
        return 0
    
    else:
        # Default: show help
        parser.print_help()
        return 0
        
except Exception as e:
    print(f"❌ Setup failed: {str(e)}")
    return 1

finally:
    await setup_manager.cleanup()
```

if **name** == “**main**”:
exit(asyncio.run(main()))