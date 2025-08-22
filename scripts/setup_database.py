#!/usr/bin/env python3
"""
Database Setup Script for SmartArb Engine
Initializes PostgreSQL database and creates initial data
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from src.db.models import Base, Exchange, TradingPair, create_tables
from src.db.connection import DatabaseManager
from src.utils.config import ConfigManager
from src.utils.logging import setup_logging
import structlog

logger = structlog.get_logger(__name__)


class DatabaseSetup:
    """Database setup and initialization"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.pg_config = config.get('database.postgresql', {})
        
    def create_database_if_not_exists(self):
        """Create database if it doesn't exist"""
        # Connect to PostgreSQL server (not specific database)
        connection_params = {
            'host': self.pg_config.get('host', 'localhost'),
            'port': self.pg_config.get('port', 5432),
            'user': self.pg_config.get('username', 'postgres'),
            'password': self.pg_config.get('password', '')
        }
        
        database_name = self.pg_config.get('database', 'smartarb')
        
        try:
            # Connect to PostgreSQL server
            conn = psycopg2.connect(**connection_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
                (database_name,)
            )
            
            if cursor.fetchone():
                logger.info("database_already_exists", database=database_name)
            else:
                # Create database
                cursor.execute(f'CREATE DATABASE "{database_name}"')
                logger.info("database_created", database=database_name)
            
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            logger.error("database_creation_failed", error=str(e))
            raise
    
    def create_tables(self):
        """Create all database tables"""
        try:
            # Build connection URL
            username = self.pg_config.get('username', 'postgres')
            password = self.pg_config.get('password', '')
            host = self.pg_config.get('host', 'localhost')
            port = self.pg_config.get('port', 5432)
            database = self.pg_config.get('database', 'smartarb')
            
            if password:
                db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            else:
                db_url = f"postgresql://{username}@{host}:{port}/{database}"
            
            # Create engine
            engine = create_engine(db_url)
            
            # Create all tables
            create_tables(engine)
            logger.info("database_tables_created")
            
            # Verify tables
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = [row[0] for row in result]
                logger.info("tables_verified", tables=tables)
            
            engine.dispose()
            
        except Exception as e:
            logger.error("table_creation_failed", error=str(e))
            raise
    
    def seed_initial_data(self):
        """Seed database with initial data"""
        try:
            # Create database manager
            db_manager = DatabaseManager(self.config.to_dict())
            
            # Use synchronous connection for seeding
            username = self.pg_config.get('username', 'postgres')
            password = self.pg_config.get('password', '')
            host = self.pg_config.get('host', 'localhost')
            port = self.pg_config.get('port', 5432)
            database = self.pg_config.get('database', 'smartarb')
            
            if password:
                db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            else:
                db_url = f"postgresql://{username}@{host}:{port}/{database}"
            
            engine = create_engine(db_url)
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # Seed exchanges
            exchanges_data = [
                {'name': 'kraken', 'display_name': 'Kraken', 'api_url': 'https://api.kraken.com'},
                {'name': 'bybit', 'display_name': 'Bybit', 'api_url': 'https://api.bybit.com'},
                {'name': 'mexc', 'display_name': 'MEXC', 'api_url': 'https://api.mexc.com'}
            ]
            
            for exchange_data in exchanges_data:
                existing = session.query(Exchange).filter(
                    Exchange.name == exchange_data['name']
                ).first()
                
                if not existing:
                    exchange = Exchange(**exchange_data)
                    session.add(exchange)
                    logger.info("exchange_seeded", name=exchange_data['name'])
            
            # Seed trading pairs
            trading_pairs_data = [
                {'symbol': 'BTC/USDT', 'base_asset': 'BTC', 'quote_asset': 'USDT'},
                {'symbol': 'ETH/USDT', 'base_asset': 'ETH', 'quote_asset': 'USDT'},
                {'symbol': 'BNB/USDT', 'base_asset': 'BNB', 'quote_asset': 'USDT'},
                {'symbol': 'ADA/USDT', 'base_asset': 'ADA', 'quote_asset': 'USDT'},
                {'symbol': 'DOT/USDT', 'base_asset': 'DOT', 'quote_asset': 'USDT'},
                {'symbol': 'LINK/USDT', 'base_asset': 'LINK', 'quote_asset': 'USDT'},
                {'symbol': 'MATIC/USDT', 'base_asset': 'MATIC', 'quote_asset': 'USDT'}
            ]
            
            for pair_data in trading_pairs_data:
                existing = session.query(TradingPair).filter(
                    TradingPair.symbol == pair_data['symbol']
                ).first()
                
                if not existing:
                    trading_pair = TradingPair(**pair_data)
                    session.add(trading_pair)
                    logger.info("trading_pair_seeded", symbol=pair_data['symbol'])
            
            # Commit changes
            session.commit()
            session.close()
            engine.dispose()
            
            logger.info("initial_data_seeded")
            
        except Exception as e:
            logger.error("data_seeding_failed", error=str(e))
            raise


def verify_requirements():
    """Verify system requirements"""
    logger.info("verifying_system_requirements")
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("python_version_too_old", 
                    required="3.8+", 
                    current=f"{sys.version_info.major}.{sys.version_info.minor}")
        return False
    
    # Check required packages
    required_packages = ['psycopg2', 'sqlalchemy', 'asyncpg', 'redis']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error("missing_packages", packages=missing_packages)
        return False
    
    logger.info("system_requirements_verified")
    return True


def test_database_connection(config: ConfigManager):
    """Test database connection"""
    logger.info("testing_database_connection")
    
    pg_config = config.get('database.postgresql', {})
    
    try:
        # Test PostgreSQL connection
        connection_params = {
            'host': pg_config.get('host', 'localhost'),
            'port': pg_config.get('port', 5432),
            'user': pg_config.get('username', 'postgres'),
            'password': pg_config.get('password', ''),
            'database': pg_config.get('database', 'smartarb')
        }
        
        conn = psycopg2.connect(**connection_params)
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        logger.info("postgresql_connection_successful", version=version)
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        return False


async def test_redis_connection(config: ConfigManager):
    """Test Redis connection"""
    logger.info("testing_redis_connection")
    
    redis_config = config.get('database.redis', {})
    
    try:
        import redis.asyncio as redis
        
        redis_client = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_config.get('password'),
            decode_responses=True
        )
        
        await redis_client.ping()
        server_info = await redis_client.info()
        logger.info("redis_connection_successful", 
                   version=server_info.get('redis_version'))
        
        await redis_client.close()
        return True
        
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        return False


def main():
    """Main setup function"""
    print("🚀 SmartArb Engine Database Setup")
    print("=" * 50)
    
    try:
        # Load configuration
        config = ConfigManager()
        
        # Setup logging
        setup_logging(config.get('logging', {}))
        
        logger.info("database_setup_started")
        
        # Verify requirements
        if not verify_requirements():
            logger.error("requirements_check_failed")
            sys.exit(1)
        
        # Initialize database setup
        db_setup = DatabaseSetup(config)
        
        # Step 1: Create database if needed
        print("\n📦 Creating database...")
        db_setup.create_database_if_not_exists()
        
        # Step 2: Test connection
        print("\n🔌 Testing database connection...")
        if not test_database_connection(config):
            logger.error("database_connection_test_failed")
            sys.exit(1)
        
        # Step 3: Create tables
        print("\n🏗️  Creating tables...")
        db_setup.create_tables()
        
        # Step 4: Seed initial data
        print("\n🌱 Seeding initial data...")
        db_setup.seed_initial_data()
        
        # Step 5: Test Redis (if configured)
        redis_config = config.get('database.redis')
        if redis_config:
            print("\n🔴 Testing Redis connection...")
            redis_success = asyncio.run(test_redis_connection(config))
            if not redis_success:
                logger.warning("redis_connection_test_failed")
        
        print("\n✅ Database setup completed successfully!")
        logger.info("database_setup_completed")
        
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        logger.error("database_setup_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
