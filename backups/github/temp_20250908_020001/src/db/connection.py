"""
Database Connection Manager for SmartArb Engine
Handles PostgreSQL and Redis connections with connection pooling
"""

import asyncio
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import redis.asyncio as redis
import asyncpg
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, AsyncGenerator
import structlog

from .models import Base, create_tables

logger = structlog.get_logger(__name__)


logger = structlog.get_logger(__name__)


class DatabaseManager:
    """
    Database connection and session management
    
    Features:
    - PostgreSQL connection pooling
    - Redis connection management
    - Session lifecycle management
    - Connection health monitoring
    - Automatic reconnection
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # PostgreSQL configuration
        self.pg_config = config.get('database', {}).get('postgresql', {})
        self.postgres_engine = None
        self.session_factory = None
        
        # Redis configuration
        self.redis_config = config.get('database', {}).get('redis', {})
        self.redis_pool = None
        
        # Connection state
        self.is_connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        
    async def initialize(self):
        """Initialize database connections"""
        logger.info("initializing_database_connections")
        
        try:
            # Initialize PostgreSQL
            if self.pg_config:
                await self._initialize_postgresql()
            
            # Initialize Redis
            if self.redis_config:
                await self._initialize_redis()
            
            self.is_connected = True
            logger.info("database_connections_initialized")
            
        except Exception as e:
            logger.error("database_initialization_failed", error=str(e))
            raise
    
    async def _initialize_postgresql(self):
        """Initialize PostgreSQL connection"""
        try:
            # Build connection URL
            pg_url = self._build_postgres_url()
            
            # Create engine with connection pooling
            self.postgres_engine = create_engine(
                pg_url,
                poolclass=QueuePool,
                pool_size=self.pg_config.get('pool_size', 10),
                max_overflow=self.pg_config.get('max_overflow', 20),
                pool_pre_ping=True,  # Validate connections before use
                pool_recycle=3600,   # Recycle connections every hour
                echo=self.config.get('database', {}).get('echo_sql', False)
            )
            
            # Test connection
            with self.postgres_engine.connect() as conn:
                conn.execute("SELECT 1")
            
            # Create session factory
            self.session_factory = sessionmaker(
                bind=self.postgres_engine,
                expire_on_commit=False
            )
            
            # Create tables if they don't exist
            create_tables(self.postgres_engine)
            
            logger.info("postgresql_initialized", 
                       host=self.pg_config.get('host'),
                       database=self.pg_config.get('database'))
            
        except Exception as e:
            logger.error("postgresql_initialization_failed", error=str(e))
            raise
    
    async def _initialize_redis(self):
        """Initialize Redis connection pool"""
        try:
            # Create Redis connection pool
            self.redis_pool = redis.ConnectionPool(
                host=self.redis_config.get('host', 'localhost'),
                port=self.redis_config.get('port', 6379),
                db=self.redis_config.get('db', 0),
                password=self.redis_config.get('password'),
                decode_responses=self.redis_config.get('decode_responses', True),
                max_connections=self.redis_config.get('max_connections', 20),
                retry_on_timeout=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Test connection
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            await redis_client.ping()
            await redis_client.close()
            
            logger.info("redis_initialized",
                       host=self.redis_config.get('host'),
                       db=self.redis_config.get('db'))
            
        except Exception as e:
            logger.error("redis_initialization_failed", error=str(e))
            raise
    
    def _build_postgres_url(self) -> str:
        """Build PostgreSQL connection URL"""
        username = self.pg_config.get('username', 'postgres')
        password = self.pg_config.get('password', '')
        host = self.pg_config.get('host', 'localhost')
        port = self.pg_config.get('port', 5432)
        database = self.pg_config.get('database', 'smartarb')
        
        if password:
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        else:
            return f"postgresql://{username}@{host}:{port}/{database}"
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[Session, None]:
        """
        Get database session with automatic cleanup
        
        Usage:
            async with db_manager.get_session() as session:
                # Use session here
                pass
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("database_session_error", error=str(e))
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_redis(self) -> AsyncGenerator[redis.Redis, None]:
        """
        Get Redis client with automatic cleanup
        
        Usage:
            async with db_manager.get_redis() as redis_client:
                # Use redis_client here
                pass
        """
        if not self.redis_pool:
            raise RuntimeError("Redis not initialized")
        
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        try:
            yield redis_client
        finally:
            await redis_client.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all database connections"""
        health_status = {
            'postgresql': {'healthy': False, 'error': None},
            'redis': {'healthy': False, 'error': None}
        }
        
        # Check PostgreSQL
        if self.postgres_engine:
            try:
                with self.postgres_engine.connect() as conn:
                    conn.execute("SELECT 1")
                health_status['postgresql']['healthy'] = True
            except Exception as e:
                health_status['postgresql']['error'] = str(e)
                logger.warning("postgresql_health_check_failed", error=str(e))
        
        # Check Redis
        if self.redis_pool:
            try:
                async with self.get_redis() as redis_client:
                    await redis_client.ping()
                health_status['redis']['healthy'] = True
            except Exception as e:
                health_status['redis']['error'] = str(e)
                logger.warning("redis_health_check_failed", error=str(e))
        
        return health_status
    
    async def close(self):
        """Close all database connections"""
        logger.info("closing_database_connections")
        
        # Close PostgreSQL
        if self.postgres_engine:
            self.postgres_engine.dispose()
            self.postgres_engine = None
            self.session_factory = None
        
        # Close Redis
        if self.redis_pool:
            await self.redis_pool.disconnect()
            self.redis_pool = None
        
        self.is_connected = False
        logger.info("database_connections_closed")


class RedisCache:
    """
    Redis-based caching utilities for SmartArb Engine
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes
    
    async def set_price(self, exchange: str, symbol: str, price: float, ttl: int = None):
        """Cache current price"""
        key = f"price:{exchange}:{symbol}"
        await self.redis.setex(key, ttl or self.default_ttl, str(price))
    
    async def get_price(self, exchange: str, symbol: str) -> Optional[float]:
        """Get cached price"""
        key = f"price:{exchange}:{symbol}"
        price_str = await self.redis.get(key)
        return float(price_str) if price_str else None
    
    async def set_orderbook(self, exchange: str, symbol: str, orderbook_data: Dict[str, Any], ttl: int = 60):
        """Cache order book data"""
        key = f"orderbook:{exchange}:{symbol}"
        import json
        await self.redis.setex(key, ttl, json.dumps(orderbook_data))
    
    async def get_orderbook(self, exchange: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached order book"""
        key = f"orderbook:{exchange}:{symbol}"
        data = await self.redis.get(key)
        if data:
            import json
            return json.loads(data)
        return None
    
    async def set_spread(self, symbol: str, buy_exchange: str, sell_exchange: str, spread: float, ttl: int = 30):
        """Cache spread data"""
        key = f"spread:{symbol}:{buy_exchange}:{sell_exchange}"
        await self.redis.setex(key, ttl, str(spread))
    
    async def get_spread(self, symbol: str, buy_exchange: str, sell_exchange: str) -> Optional[float]:
        """Get cached spread"""
        key = f"spread:{symbol}:{buy_exchange}:{sell_exchange}"
        spread_str = await self.redis.get(key)
        return float(spread_str) if spread_str else None
    
    async def set_balance(self, exchange: str, asset: str, balance_data: Dict[str, Any], ttl: int = 60):
        """Cache balance data"""
        key = f"balance:{exchange}:{asset}"
        import json
        await self.redis.setex(key, ttl, json.dumps(balance_data))
    
    async def get_balance(self, exchange: str, asset: str) -> Optional[Dict[str, Any]]:
        """Get cached balance"""
        key = f"balance:{exchange}:{asset}"
        data = await self.redis.get(key)
        if data:
            import json
            return json.loads(data)
        return None
    
    async def lock_opportunity(self, opportunity_id: str, ttl: int = 30) -> bool:
        """Create a lock for opportunity execution"""
        key = f"lock:opportunity:{opportunity_id}"
        # Use SET with NX (only if not exists) and EX (expiry)
        result = await self.redis.set(key, "locked", nx=True, ex=ttl)
        return result is not None
    
    async def unlock_opportunity(self, opportunity_id: str):
        """Release opportunity lock"""
        key = f"lock:opportunity:{opportunity_id}"
        await self.redis.delete(key)
    
    async def increment_metric(self, metric_name: str, increment: int = 1):
        """Increment a metric counter"""
        key = f"metric:{metric_name}"
        return await self.redis.incrby(key, increment)
    
    async def get_metric(self, metric_name: str) -> int:
        """Get metric value"""
        key = f"metric:{metric_name}"
        value = await self.redis.get(key)
        return int(value) if value else 0
    
    async def set_health_status(self, component: str, status: str, ttl: int = 120):
        """Set component health status"""
        key = f"health:{component}"
        await self.redis.setex(key, ttl, status)
    
    async def get_health_status(self, component: str) -> Optional[str]:
        """Get component health status"""
        key = f"health:{component}"
        return await self.redis.get(key)
    
    async def clear_cache_pattern(self, pattern: str):
        """Clear all keys matching pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
            return len(keys)
        return 0


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global db_manager
    if db_manager is None:
        raise RuntimeError("Database manager not initialized")
    return db_manager


async def initialize_database(config: Dict[str, Any]) -> DatabaseManager:
    """Initialize global database manager"""
    global db_manager
    db_manager = DatabaseManager(config)
    await db_manager.initialize()
    return db_manager


async def close_database():
    """Close global database manager"""
    global db_manager
    if db_manager:
        await db_manager.close()
        db_manager = None