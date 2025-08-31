#!/usr/bin/env python3
"""
SmartArb Engine - Comprehensive Health Check Script
Robust health checking for all system components
Optimized for Raspberry Pi 5 deployment
"""

import asyncio
import aiohttp
import asyncpg
import redis.asyncio as redis
import structlog
import psutil
import json
import time
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = structlog.get_logger(__name__)


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning" 
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class ComponentHealth:
    """Individual component health status"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    details: Dict[str, Any]
    timestamp: float

@dataclass
class SystemHealth:
    """Overall system health status"""
    status: HealthStatus
    components: List[ComponentHealth]
    summary: Dict[str, Any]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'status': self.status.value,
            'components': [asdict(comp) for comp in self.components],
            'summary': self.summary,
            'timestamp': self.timestamp
        }

class HealthChecker:
    """Comprehensive health checker for SmartArb Engine"""
    
    def __init__(self):
        self.start_time = time.time()
        self.config = self._load_config()
        self.timeout = 10.0  # Default timeout for checks
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            'postgres': {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', '5432')),
                'database': os.getenv('POSTGRES_DATABASE', 'smartarb'),
                'username': os.getenv('POSTGRES_USERNAME', 'smartarb_user'),
                'password': os.getenv('POSTGRES_PASSWORD', ''),
            },
            'redis': {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', '6379')),
                'db': int(os.getenv('REDIS_DB', '0')),
                'password': os.getenv('REDIS_PASSWORD', ''),
            },
            'api': {
                'host': 'localhost',
                'port': int(os.getenv('API_PORT', '8000')),
                'health_endpoint': '/health'
            },
            'thresholds': {
                'cpu_warning': float(os.getenv('CPU_WARNING_THRESHOLD', '70.0')),
                'cpu_critical': float(os.getenv('CPU_CRITICAL_THRESHOLD', '90.0')),
                'memory_warning': float(os.getenv('MEMORY_WARNING_THRESHOLD', '80.0')),
                'memory_critical': float(os.getenv('MEMORY_CRITICAL_THRESHOLD', '95.0')),
                'disk_warning': float(os.getenv('DISK_WARNING_THRESHOLD', '80.0')),
                'disk_critical': float(os.getenv('DISK_CRITICAL_THRESHOLD', '95.0')),
                'temperature_warning': float(os.getenv('TEMP_WARNING_THRESHOLD', '65.0')),
                'temperature_critical': float(os.getenv('TEMP_CRITICAL_THRESHOLD', '80.0')),
            }
        }
    
    async def check_postgresql(self) -> ComponentHealth:
        """Check PostgreSQL database health"""
        start_time = time.time()
        
        try:
            # Connection string
            dsn = (
                f"postgresql://{self.config['postgres']['username']}:"
                f"{self.config['postgres']['password']}@"
                f"{self.config['postgres']['host']}:"
                f"{self.config['postgres']['port']}/"
                f"{self.config['postgres']['database']}"
            )
            
            # Test connection with timeout
            conn = await asyncio.wait_for(
                asyncpg.connect(dsn),
                timeout=self.timeout
            )
            
            try:
                # Test query
                result = await conn.fetchval('SELECT 1')
                
                # Get database stats
                stats = await conn.fetchrow("""
                    SELECT 
                        pg_database_size(current_database()) as db_size,
                        (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                        (SELECT setting FROM pg_settings WHERE name = 'max_connections') as max_connections
                """)
                
                # Get table counts (if tables exist)
                try:
                    table_count = await conn.fetchval("""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                except:
                    table_count = 0
                
                response_time = (time.time() - start_time) * 1000
                
                details = {
                    'connection_successful': True,
                    'query_successful': result == 1,
                    'database_size_bytes': stats['db_size'],
                    'active_connections': stats['active_connections'],
                    'max_connections': int(stats['max_connections']),
                    'table_count': table_count,
                    'response_time_ms': response_time
                }
                
                # Determine status
                connection_usage = stats['active_connections'] / int(stats['max_connections'])
                if connection_usage > 0.9:
                    status = HealthStatus.CRITICAL
                    message = f"Database connection usage critical: {connection_usage:.1%}"
                elif connection_usage > 0.7:
                    status = HealthStatus.WARNING
                    message = f"Database connection usage high: {connection_usage:.1%}"
                elif response_time > 1000:
                    status = HealthStatus.WARNING
                    message = f"Database response time slow: {response_time:.1f}ms"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Database connection healthy"
                
                return ComponentHealth(
                    name="postgresql",
                    status=status,
                    message=message,
                    response_time_ms=response_time,
                    details=details,
                    timestamp=time.time()
                )
                
            finally:
                await conn.close()
                
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="postgresql",
                status=HealthStatus.CRITICAL,
                message="Database connection timeout",
                response_time_ms=(time.time() - start_time) * 1000,
                details={'error': 'Connection timeout', 'timeout_seconds': self.timeout},
                timestamp=time.time()
            )
            
        except Exception as e:
            return ComponentHealth(
                name="postgresql",
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                details={'error': str(e), 'error_type': type(e).__name__},
                timestamp=time.time()
            )
    
    async def check_redis(self) -> ComponentHealth:
        """Check Redis cache health"""
        start_time = time.time()
        
        try:
            # Create Redis connection
            redis_client = redis.Redis(
                host=self.config['redis']['host'],
                port=self.config['redis']['port'],
                db=self.config['redis']['db'],
                password=self.config['redis']['password'] or None,
                socket_timeout=self.timeout,
                socket_connect_timeout=self.timeout
            )
            
            # Test connection
            await redis_client.ping()
            
            # Get Redis info
            info = await redis_client.info()
            
            # Test set/get operations
            test_key = f"healthcheck_{int(time.time())}"
            await redis_client.set(test_key, "test_value", ex=60)  # Expire in 60 seconds
            test_result = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            details = {
                'connection_successful': True,
                'ping_successful': True,
                'set_get_successful': test_result == b"test_value",
                'redis_version': info.get('redis_version', 'unknown'),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'response_time_ms': response_time
            }
            
            # Calculate hit rate
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total_ops = hits + misses
            hit_rate = (hits / total_ops) if total_ops > 0 else 1.0
            
            # Determine status
            memory_usage = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            
            if max_memory > 0:
                memory_percentage = memory_usage / max_memory
                if memory_percentage > 0.9:
                    status = HealthStatus.CRITICAL
                    message = f"Redis memory usage critical: {memory_percentage:.1%}"
                elif memory_percentage > 0.8:
                    status = HealthStatus.WARNING
                    message = f"Redis memory usage high: {memory_percentage:.1%}"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Redis healthy (hit rate: {hit_rate:.1%})"
            elif response_time > 100:
                status = HealthStatus.WARNING
                message = f"Redis response time slow: {response_time:.1f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = f"Redis healthy (hit rate: {hit_rate:.1%})"
            
            await redis_client.close()
            
            return ComponentHealth(
                name="redis",
                status=status,
                message=message,
                response_time_ms=response_time,
                details=details,
                timestamp=time.time()
            )
            
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.CRITICAL,
                message=f"Redis connection failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                details={'error': str(e), 'error_type': type(e).__name__},
                timestamp=time.time()
            )
    
    async def check_system_resources(self) -> ComponentHealth:
        """Check system resource usage"""
        start_time = time.time()
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # System load
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
            
            # Process count
            process_count = len(psutil.pids())
            
            # Network stats (if available)
            try:
                network = psutil.net_io_counters()
                network_details = {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                }
            except:
                network_details = {}
            
            details = {
                'cpu': {
                    'usage_percent': cpu_percent,
                    'count': cpu_count,
                    'frequency_mhz': cpu_freq.current if cpu_freq else 0
                },
                'memory': {
                    'total_bytes': memory.total,
                    'available_bytes': memory.available,
                    'used_bytes': memory.used,
                    'usage_percent': memory.percent
                },
                'disk': {
                    'total_bytes': disk.total,
                    'free_bytes': disk.free,
                    'used_bytes': disk.used,
                    'usage_percent': (disk.used / disk.total) * 100
                },
                'system': {
                    'load_average_1m': load_avg[0],
                    'load_average_5m': load_avg[1],
                    'load_average_15m': load_avg[2],
                    'process_count': process_count
                },
                'network': network_details
            }
            
            # Determine status based on thresholds
            issues = []
            status = HealthStatus.HEALTHY
            
            # Check CPU
            if cpu_percent >= self.config['thresholds']['cpu_critical']:
                status = HealthStatus.CRITICAL
                issues.append(f"CPU usage critical: {cpu_percent:.1f}%")
            elif cpu_percent >= self.config['thresholds']['cpu_warning']:
                status = HealthStatus.WARNING
                issues.append(f"CPU usage high: {cpu_percent:.1f}%")
            
            # Check memory
            if memory.percent >= self.config['thresholds']['memory_critical']:
                status = HealthStatus.CRITICAL
                issues.append(f"Memory usage critical: {memory.percent:.1f}%")
            elif memory.percent >= self.config['thresholds']['memory_warning']:
                if status != HealthStatus.CRITICAL:
                    status = HealthStatus.WARNING
                issues.append(f"Memory usage high: {memory.percent:.1f}%")
            
            # Check disk
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent >= self.config['thresholds']['disk_critical']:
                status = HealthStatus.CRITICAL
                issues.append(f"Disk usage critical: {disk_percent:.1f}%")
            elif disk_percent >= self.config['thresholds']['disk_warning']:
                if status not in [HealthStatus.CRITICAL]:
                    status = HealthStatus.WARNING
                issues.append(f"Disk usage high: {disk_percent:.1f}%")
            
            # Check load average (relative to CPU count)
            if load_avg[0] > cpu_count * 2:
                status = HealthStatus.CRITICAL
                issues.append(f"System load critical: {load_avg[0]:.2f}")
            elif load_avg[0] > cpu_count * 1.5:
                if status not in [HealthStatus.CRITICAL]:
                    status = HealthStatus.WARNING
                issues.append(f"System load high: {load_avg[0]:.2f}")
            
            message = "; ".join(issues) if issues else "System resources healthy"
            
            return ComponentHealth(
                name="system_resources",
                status=status,
                message=message,
                response_time_ms=(time.time() - start_time) * 1000,
                details=details,
                timestamp=time.time()
            )
            
        except Exception as e:
            return ComponentHealth(
                name="system_resources",
                status=HealthStatus.CRITICAL,
                message=f"System resource check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                details={'error': str(e), 'error_type': type(e).__name__},
                timestamp=time.time()
            )
    
    async def check_raspberry_pi_specific(self) -> ComponentHealth:
        """Check Raspberry Pi specific health metrics"""
        start_time = time.time()
        
        try:
            details = {}
            issues = []
            status = HealthStatus.HEALTHY
            
            # Check CPU temperature
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_raw = int(f.read().strip())
                    cpu_temp = temp_raw / 1000.0  # Convert from millidegrees
                    
                details['cpu_temperature_celsius'] = cpu_temp
                
                if cpu_temp >= self.config['thresholds']['temperature_critical']:
                    status = HealthStatus.CRITICAL
                    issues.append(f"CPU temperature critical: {cpu_temp:.1f}°C")
                elif cpu_temp >= self.config['thresholds']['temperature_warning']:
                    status = HealthStatus.WARNING
                    issues.append(f"CPU temperature high: {cpu_temp:.1f}°C")
                    
            except FileNotFoundError:
                details['cpu_temperature_celsius'] = None
                issues.append("CPU temperature sensor not available")
            
            # Check CPU throttling
            try:
                result = subprocess.run(
                    ['vcgencmd', 'get_throttled'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    throttled_value = result.stdout.strip().split('=')[1]
                    throttled_int = int(throttled_value, 16)
                    
                    details['throttled_status'] = {
                        'raw_value': throttled_value,
                        'under_voltage_now': bool(throttled_int & 0x1),
                        'arm_frequency_capped_now': bool(throttled_int & 0x2),
                        'currently_throttled': bool(throttled_int & 0x4),
                        'soft_temperature_limit_active': bool(throttled_int & 0x8),
                        'under_voltage_occurred': bool(throttled_int & 0x10000),
                        'arm_frequency_capping_occurred': bool(throttled_int & 0x20000),
                        'throttling_occurred': bool(throttled_int & 0x40000),
                        'soft_temperature_limit_occurred': bool(throttled_int & 0x80000),
                    }
                    
                    # Check for current issues
                    if throttled_int & 0xF:  # Any current throttling
                        status = HealthStatus.WARNING
                        if throttled_int & 0x1:
                            issues.append("Under-voltage detected")
                        if throttled_int & 0x2:
                            issues.append("ARM frequency capped")
                        if throttled_int & 0x4:
                            issues.append("Currently throttled")
                        if throttled_int & 0x8:
                            issues.append("Soft temperature limit active")
                            
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                details['throttled_status'] = None
            
            # Check GPU memory split
            try:
                result = subprocess.run(
                    ['vcgencmd', 'get_mem', 'gpu'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    gpu_mem = result.stdout.strip().split('=')[1].replace('M', '')
                    details['gpu_memory_mb'] = int(gpu_mem)
                    
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                details['gpu_memory_mb'] = None
            
            # Check power supply voltage
            try:
                result = subprocess.run(
                    ['vcgencmd', 'measure_volts'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    voltage_str = result.stdout.strip().split('=')[1].replace('V', '')
                    voltage = float(voltage_str)
                    details['core_voltage_v'] = voltage
                    
                    # Check for undervoltage (RPi should be around 1.2V for core)
                    if voltage < 1.1:
                        status = HealthStatus.CRITICAL
                        issues.append(f"Core voltage low: {voltage:.2f}V")
                    elif voltage < 1.15:
                        if status != HealthStatus.CRITICAL:
                            status = HealthStatus.WARNING
                        issues.append(f"Core voltage low: {voltage:.2f}V")
                        
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                details['core_voltage_v'] = None
            
            # Check SD card health (if root filesystem is on SD card)
            try:
                disk_usage = psutil.disk_usage('/')
                # Check if we're likely on SD card (look for mmcblk device)
                with open('/proc/mounts', 'r') as f:
                    mounts = f.read()
                    
                if 'mmcblk' in mounts:
                    details['storage_type'] = 'sd_card'
                    # SD cards can have issues with high I/O
                    disk_io = psutil.disk_io_counters(perdisk=True)
                    if disk_io:
                        total_io = sum(disk.read_bytes + disk.write_bytes for disk in disk_io.values())
                        details['total_disk_io_bytes'] = total_io
                elif 'sda' in mounts or 'sdb' in mounts:
                    details['storage_type'] = 'external_drive'
                else:
                    details['storage_type'] = 'unknown'
                    
            except Exception:
                details['storage_type'] = 'unknown'
            
            message = "; ".join(issues) if issues else "Raspberry Pi hardware healthy"
            
            return ComponentHealth(
                name="raspberry_pi",
                status=status,
                message=message,
                response_time_ms=(time.time() - start_time) * 1000,
                details=details,
                timestamp=time.time()
            )
            
        except Exception as e:
            return ComponentHealth(
                name="raspberry_pi",
                status=HealthStatus.WARNING,
                message=f"RPi health check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                details={'error': str(e), 'error_type': type(e).__name__},
                timestamp=time.time()
            )
    
    async def check_application_api(self) -> ComponentHealth:
        """Check application API health"""
        start_time = time.time()
        
        try:
            url = f"http://{self.config['api']['host']}:{self.config['api']['port']}{self.config['api']['health_endpoint']}"
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            
                            details = {
                                'status_code': response.status,
                                'response_data': data,
                                'response_time_ms': response_time,
                                'content_type': response.headers.get('content-type', '')
                            }
                            
                            # Analyze response data
                            app_status = data.get('status', 'unknown')
                            if app_status == 'healthy':
                                status = HealthStatus.HEALTHY
                                message = "Application API healthy"
                            elif app_status == 'warning':
                                status = HealthStatus.WARNING
                                message = f"Application API warning: {data.get('message', '')}"
                            else:
                                status = HealthStatus.UNHEALTHY
                                message = f"Application API unhealthy: {data.get('message', '')}"
                                
                        except json.JSONDecodeError:
                            status = HealthStatus.WARNING
                            message = "Application API returned invalid JSON"
                            details = {
                                'status_code': response.status,
                                'response_time_ms': response_time,
                                'error': 'Invalid JSON response'
                            }
                    else:
                        status = HealthStatus.UNHEALTHY
                        message = f"Application API returned HTTP {response.status}"
                        details = {
                            'status_code': response.status,
                            'response_time_ms': response_time,
                            'error': f'HTTP {response.status}'
                        }
                    
                    return ComponentHealth(
                        name="application_api",
                        status=status,
                        message=message,
                        response_time_ms=response_time,
                        details=details,
                        timestamp=time.time()
                    )
                    
        except aiohttp.ClientConnectorError:
            return ComponentHealth(
                name="application_api",
                status=HealthStatus.CRITICAL,
                message="Application API connection refused",
                response_time_ms=(time.time() - start_time) * 1000,
                details={'error': 'Connection refused', 'url': url},
                timestamp=time.time()
            )
            
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="application_api",
                status=HealthStatus.CRITICAL,
                message="Application API timeout",
                response_time_ms=(time.time() - start_time) * 1000,
                details={'error': 'Timeout', 'timeout_seconds': self.timeout},
                timestamp=time.time()
            )
            
        except Exception as e:
            return ComponentHealth(
                name="application_api",
                status=HealthStatus.CRITICAL,
                message=f"Application API check failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                details={'error': str(e), 'error_type': type(e).__name__},
                timestamp=time.time()
            )
    
    async def run_all_checks(self) -> SystemHealth:
        """Run all health checks and return overall system health"""
        logger.info("Starting comprehensive health check...")
        
        # Define all health checks
        checks = [
            ("PostgreSQL Database", self.check_postgresql()),
            ("Redis Cache", self.check_redis()),
            ("System Resources", self.check_system_resources()),
            ("Raspberry Pi Hardware", self.check_raspberry_pi_specific()),
            ("Application API", self.check_application_api()),
        ]
        
        # Run all checks concurrently
        components = []
        
        for check_name, check_coro in checks:
            try:
                logger.info(f"Running {check_name} health check...")
                result = await check_coro
                components.append(result)
                logger.info(f"{check_name}: {result.status.value} - {result.message}")
            except Exception as e:
                logger.error(f"{check_name} health check failed: {e}")
                components.append(ComponentHealth(
                    name=check_name.lower().replace(' ', '_'),
                    status=HealthStatus.CRITICAL,
                    message=f"Health check exception: {str(e)}",
                    response_time_ms=0,
                    details={'error': str(e), 'error_type': type(e).__name__},
                    timestamp=time.time()
                ))
        
        # Determine overall system status
        statuses = [comp.status for comp in components]
        
        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Create summary
        summary = {
            'total_components': len(components),
            'healthy_components': len([c for c in components if c.status == HealthStatus.HEALTHY]),
            'warning_components': len([c for c in components if c.status == HealthStatus.WARNING]),
            'unhealthy_components': len([c for c in components if c.status == HealthStatus.UNHEALTHY]),
            'critical_components': len([c for c in components if c.status == HealthStatus.CRITICAL]),
            'average_response_time_ms': sum(c.response_time_ms for c in components) / len(components),
            'uptime_seconds': time.time() - self.start_time,
        }
        
        system_health = SystemHealth(
            status=overall_status,
            components=components,
            summary=summary,
            timestamp=time.time()
        )
        
        logger.info(f"Health check completed. Overall status: {overall_status.value}")
        
        return system_health

async def main():
    """Main entry point for health check script"""
    checker = HealthChecker()
    
    try:
        # Run health checks
        health = await checker.run_all_checks()
        
        # Output results
        health_dict = health.to_dict()
        
        # Pretty print JSON
        print(json.dumps(health_dict, indent=2, default=str))
        
        # Exit with appropriate code
        if health.status == HealthStatus.HEALTHY:
            sys.exit(0)
        elif health.status in [HealthStatus.WARNING, HealthStatus.UNHEALTHY]:
            sys.exit(1)
        else:  # CRITICAL
            sys.exit(2)
            
    except KeyboardInterrupt:
        logger.info("Health check interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        logger.error(f"Health check failed with exception: {e}")
        error_result = {
            'status': 'critical',
            'error': str(e),
            'timestamp': time.time()
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(2)

if __name__ == "__main__":
    # Run the health check
    asyncio.run(main())
