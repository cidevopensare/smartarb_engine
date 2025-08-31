#!/usr/bin/env python3
"""
SmartArb Engine - Automated Backup System
Comprehensive backup solution for database, configurations, and application data
Optimized for Raspberry Pi 5 with external storage support
"""

import os
import sys
import subprocess
import shutil
import json
import yaml
import tarfile
import gzip
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import schedule
import time
import psutil
import asyncio
import asyncpg

logger = structlog.get_logger(__name__)


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class BackupConfig:
    """Backup configuration settings"""
    # Backup locations
    local_backup_dir: Path
    external_backup_dir: Optional[Path] = None
    cloud_backup_enabled: bool = False
    
    # Database settings
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "smartarb"
    postgres_username: str = "smartarb_user"
    postgres_password: str = ""
    
    # Backup retention
    keep_daily: int = 7
    keep_weekly: int = 4
    keep_monthly: int = 12
    
    # Compression
    compress_backups: bool = True
    compression_level: int = 6
    
    # Encryption
    encrypt_backups: bool = False
    encryption_key: Optional[str] = None
    
    # Cloud storage
    aws_s3_bucket: Optional[str] = None
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    aws_region: str = "us-east-1"
    
    # Monitoring
    enable_monitoring: bool = True
    max_backup_size_mb: int = 1000  # Alert if backup exceeds this size
    max_backup_time_minutes: int = 30  # Alert if backup takes longer
    
    # Raspberry Pi specific
    check_disk_space: bool = True
    min_free_space_gb: float = 2.0
    use_external_storage: bool = False

@dataclass
class BackupResult:
    """Result of a backup operation"""
    timestamp: str
    backup_type: str
    success: bool
    backup_path: Optional[Path]
    file_size_bytes: int
    duration_seconds: float
    error_message: Optional[str] = None
    checksums: Dict[str, str] = None

class BackupManager:
    """Main backup management system"""
    
    def __init__(self, config: BackupConfig):
        self.config = config
        self.project_root = Path(__file__).parent.parent
        
        # Ensure backup directories exist
        self.config.local_backup_dir.mkdir(parents=True, exist_ok=True)
        if self.config.external_backup_dir:
            self.config.external_backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize cloud storage if enabled
        self.s3_client = None
        if self.config.cloud_backup_enabled and self.config.aws_s3_bucket:
            self._init_s3_client()
    
    def _init_s3_client(self):
        """Initialize AWS S3 client"""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.aws_access_key,
                aws_secret_access_key=self.config.aws_secret_key,
                region_name=self.config.aws_region
            )
            
            # Test connection
            self.s3_client.head_bucket(Bucket=self.config.aws_s3_bucket)
            logger.info(f"S3 client initialized for bucket: {self.config.aws_s3_bucket}")
            
        except (NoCredentialsError, ClientError) as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None
    
    def check_prerequisites(self) -> Dict[str, bool]:
        """Check backup prerequisites"""
        checks = {}
        
        # Check disk space
        if self.config.check_disk_space:
            disk_usage = shutil.disk_usage(self.config.local_backup_dir)
            free_gb = disk_usage.free / (1024**3)
            checks['disk_space'] = free_gb >= self.config.min_free_space_gb
            if not checks['disk_space']:
                logger.warning(f"Low disk space: {free_gb:.2f}GB (need {self.config.min_free_space_gb}GB)")
        
        # Check external storage
        if self.config.external_backup_dir:
            checks['external_storage'] = self.config.external_backup_dir.exists()
            if not checks['external_storage']:
                logger.warning(f"External storage not available: {self.config.external_backup_dir}")
        
        # Check database connection
        try:
            result = subprocess.run(
                ['pg_isready', '-h', self.config.postgres_host, '-p', str(self.config.postgres_port)],
                capture_output=True, text=True, timeout=10
            )
            checks['database'] = result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            checks['database'] = False
            logger.warning("Database connection check failed")
        
        # Check required tools
        required_tools = ['pg_dump', 'tar', 'gzip']
        for tool in required_tools:
            checks[f'tool_{tool}'] = shutil.which(tool) is not None
        
        return checks
    
    async def backup_database(self, backup_type: str = "daily") -> BackupResult:
        """Backup PostgreSQL database"""
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"database_backup_{backup_type}_{timestamp}.sql"
        backup_path = self.config.local_backup_dir / backup_filename
        
        logger.info(f"Starting database backup: {backup_filename}")
        
        try:
            # Create database backup
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config.postgres_password
            
            cmd = [
                'pg_dump',
                '-h', self.config.postgres_host,
                '-p', str(self.config.postgres_port),
                '-U', self.config.postgres_username,
                '-d', self.config.postgres_database,
                '--no-password',
                '--verbose',
                '--clean',
                '--create',
                '--format=custom',
                '--compress=9',
                '--file', str(backup_path)
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
            
            # Verify backup file exists and has content
            if not backup_path.exists() or backup_path.stat().st_size == 0:
                raise RuntimeError("Backup file is empty or doesn't exist")
            
            file_size = backup_path.stat().st_size
            duration = time.time() - start_time
            
            # Calculate checksums
            checksums = self._calculate_checksums(backup_path)
            
            # Compress if requested
            if self.config.compress_backups:
                compressed_path = await self._compress_file(backup_path)
                if compressed_path:
                    backup_path.unlink()  # Remove original
                    backup_path = compressed_path
                    file_size = backup_path.stat().st_size
            
            logger.info(f"Database backup completed: {backup_path} ({file_size / 1024 / 1024:.2f}MB)")
            
            return BackupResult(
                timestamp=timestamp,
                backup_type=f"database_{backup_type}",
                success=True,
                backup_path=backup_path,
                file_size_bytes=file_size,
                duration_seconds=duration,
                checksums=checksums
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Database backup failed: {e}")
            
            return BackupResult(
                timestamp=timestamp,
                backup_type=f"database_{backup_type}",
                success=False,
                backup_path=None,
                file_size_bytes=0,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    async def backup_application_data(self, backup_type: str = "daily") -> BackupResult:
        """Backup application data and configurations"""
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"appdata_backup_{backup_type}_{timestamp}.tar.gz"
        backup_path = self.config.local_backup_dir / backup_filename
        
        logger.info(f"Starting application data backup: {backup_filename}")
        
        try:
            # Define what to backup
            backup_items = [
                ('config', 'config/'),
                ('logs', 'logs/'),
                ('data', 'data/'),
                ('scripts', 'scripts/'),
                ('.env', '.env'),
                ('requirements.txt', 'requirements.txt'),
                ('docker-compose.yml', 'docker-compose.yml'),
                ('Dockerfile', 'Dockerfile'),
            ]
            
            # Create tar archive
            with tarfile.open(backup_path, 'w:gz', compresslevel=self.config.compression_level) as tar:
                for item_name, item_path in backup_items:
                    full_path = self.project_root / item_path
                    if full_path.exists():
                        tar.add(full_path, arcname=item_name)
                        logger.debug(f"Added to backup: {item_path}")
                
                # Add metadata
                metadata = {
                    'backup_type': backup_type,
                    'timestamp': timestamp,
                    'hostname': os.uname().nodename,
                    'python_version': sys.version,
                    'items_backed_up': [item[0] for item in backup_items if (self.project_root / item[1]).exists()]
                }
                
                metadata_json = json.dumps(metadata, indent=2)
                metadata_info = tarfile.TarInfo(name='backup_metadata.json')
                metadata_info.size = len(metadata_json)
                metadata_info.mtime = time.time()
                tar.addfile(metadata_info, fileobj=gzip.compress(metadata_json.encode()))
            
            file_size = backup_path.stat().st_size
            duration = time.time() - start_time
            checksums = self._calculate_checksums(backup_path)
            
            logger.info(f"Application data backup completed: {backup_path} ({file_size / 1024 / 1024:.2f}MB)")
            
            return BackupResult(
                timestamp=timestamp,
                backup_type=f"appdata_{backup_type}",
                success=True,
                backup_path=backup_path,
                file_size_bytes=file_size,
                duration_seconds=duration,
                checksums=checksums
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Application data backup failed: {e}")
            
            return BackupResult(
                timestamp=timestamp,
                backup_type=f"appdata_{backup_type}",
                success=False,
                backup_path=None,
                file_size_bytes=0,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    async def backup_system_info(self) -> BackupResult:
        """Backup system information and health status"""
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"sysinfo_backup_{timestamp}.json"
        backup_path = self.config.local_backup_dir / backup_filename
        
        logger.info(f"Creating system information backup: {backup_filename}")
        
        try:
            # Collect system information
            system_info = {
                'timestamp': timestamp,
                'hostname': os.uname().nodename,
                'platform': {
                    'system': os.uname().sysname,
                    'release': os.uname().release,
                    'version': os.uname().version,
                    'machine': os.uname().machine,
                    'processor': os.uname().machine,
                },
                'resources': {
                    'cpu_count': psutil.cpu_count(),
                    'memory_total': psutil.virtual_memory().total,
                    'disk_usage': {
                        str(path): {
                            'total': shutil.disk_usage(path).total,
                            'used': shutil.disk_usage(path).used,
                            'free': shutil.disk_usage(path).free,
                        }
                        for path in [self.project_root, '/']
                        if Path(path).exists()
                    }
                },
                'network': {
                    'interfaces': list(psutil.net_if_addrs().keys()),
                    'stats': {name: stats._asdict() for name, stats in psutil.net_if_stats().items()},
                },
                'processes': [
                    {
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_percent': proc.info['memory_percent'],
                    }
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent'])
                    if 'smartarb' in proc.info['name'].lower()
                ]
            }
            
            # Add Raspberry Pi specific info if available
            rpi_info = self._get_raspberry_pi_info()
            if rpi_info:
                system_info['raspberry_pi'] = rpi_info
            
            # Save system info
            with open(backup_path, 'w') as f:
                json.dump(system_info, f, indent=2, default=str)
            
            file_size = backup_path.stat().st_size
            duration = time.time() - start_time
            checksums = self._calculate_checksums(backup_path)
            
            logger.info(f"System information backup completed: {backup_path}")
            
            return BackupResult(
                timestamp=timestamp,
                backup_type="system_info",
                success=True,
                backup_path=backup_path,
                file_size_bytes=file_size,
                duration_seconds=duration,
                checksums=checksums
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"System information backup failed: {e}")
            
            return BackupResult(
                timestamp=timestamp,
                backup_type="system_info",
                success=False,
                backup_path=None,
                file_size_bytes=0,
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def _get_raspberry_pi_info(self) -> Optional[Dict[str, Any]]:
        """Get Raspberry Pi specific information"""
        try:
            # Check if this is a Raspberry Pi
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                if 'BCM' not in cpuinfo:
                    return None
            
            rpi_info = {}
            
            # CPU temperature
            try:
                result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True)
                if result.returncode == 0:
                    rpi_info['cpu_temperature'] = result.stdout.strip()
            except:
                pass
            
            # GPU memory
            try:
                result = subprocess.run(['vcgencmd', 'get_mem', 'gpu'], capture_output=True, text=True)
                if result.returncode == 0:
                    rpi_info['gpu_memory'] = result.stdout.strip()
            except:
                pass
            
            # Throttling status
            try:
                result = subprocess.run(['vcgencmd', 'get_throttled'], capture_output=True, text=True)
                if result.returncode == 0:
                    rpi_info['throttled_status'] = result.stdout.strip()
            except:
                pass
            
            # Voltage
            try:
                result = subprocess.run(['vcgencmd', 'measure_volts'], capture_output=True, text=True)
                if result.returncode == 0:
                    rpi_info['core_voltage'] = result.stdout.strip()
            except:
                pass
            
            return rpi_info if rpi_info else None
            
        except:
            return None
    
    async def _compress_file(self, file_path: Path) -> Optional[Path]:
        """Compress a file using gzip"""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb', compresslevel=self.config.compression_level) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            logger.debug(f"Compressed {file_path} to {compressed_path}")
            return compressed_path
            
        except Exception as e:
            logger.error(f"Failed to compress {file_path}: {e}")
            return None
    
    def _calculate_checksums(self, file_path: Path) -> Dict[str, str]:
        """Calculate file checksums"""
        checksums = {}
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                
                # MD5
                checksums['md5'] = hashlib.md5(content).hexdigest()
                
                # SHA256
                checksums['sha256'] = hashlib.sha256(content).hexdigest()
                
        except Exception as e:
            logger.error(f"Failed to calculate checksums for {file_path}: {e}")
        
        return checksums
    
    async def upload_to_cloud(self, backup_path: Path) -> bool:
        """Upload backup to cloud storage"""
        if not self.s3_client or not self.config.aws_s3_bucket:
            logger.warning("Cloud backup not configured")
            return False
        
        try:
            s3_key = f"smartarb-backups/{backup_path.name}"
            
            logger.info(f"Uploading {backup_path} to S3...")
            
            self.s3_client.upload_file(
                str(backup_path),
                self.config.aws_s3_bucket,
                s3_key
            )
            
            logger.info(f"Successfully uploaded to S3: s3://{self.config.aws_s3_bucket}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            return False
    
    def cleanup_old_backups(self, backup_type: str = "daily"):
        """Clean up old backups based on retention policy"""
        logger.info(f"Cleaning up old {backup_type} backups...")
        
        # Determine retention period
        if backup_type == "daily":
            keep_days = self.config.keep_daily
        elif backup_type == "weekly":
            keep_days = self.config.keep_weekly * 7
        elif backup_type == "monthly":
            keep_days = self.config.keep_monthly * 30
        else:
            keep_days = self.config.keep_daily
        
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        # Find and remove old backups
        pattern = f"*backup_{backup_type}_*.tar.gz"
        old_backups = [
            f for f in self.config.local_backup_dir.glob(pattern)
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff_date
        ]
        
        for backup_file in old_backups:
            try:
                backup_file.unlink()
                logger.info(f"Removed old backup: {backup_file}")
            except Exception as e:
                logger.error(f"Failed to remove {backup_file}: {e}")
        
        logger.info(f"Cleanup completed - removed {len(old_backups)} old backups")
    
    async def create_full_backup(self, backup_type: str = "daily") -> List[BackupResult]:
        """Create complete backup (database + application data + system info)"""
        logger.info(f"Starting full backup ({backup_type})...")
        
        results = []
        
        # Check prerequisites
        prereq_results = self.check_prerequisites()
        failed_checks = [k for k, v in prereq_results.items() if not v]
        
        if failed_checks:
            logger.warning(f"Some prerequisite checks failed: {failed_checks}")
        
        # Database backup
        db_result = await self.backup_database(backup_type)
        results.append(db_result)
        
        if db_result.success and db_result.backup_path:
            # Copy to external storage if available
            if self.config.external_backup_dir:
                await self._copy_to_external(db_result.backup_path)
            
            # Upload to cloud if enabled
            if self.config.cloud_backup_enabled:
                await self.upload_to_cloud(db_result.backup_path)
        
        # Application data backup
        app_result = await self.backup_application_data(backup_type)
        results.append(app_result)
        
        if app_result.success and app_result.backup_path:
            if self.config.external_backup_dir:
                await self._copy_to_external(app_result.backup_path)
            
            if self.config.cloud_backup_enabled:
                await self.upload_to_cloud(app_result.backup_path)
        
        # System info backup
        sys_result = await self.backup_system_info()
        results.append(sys_result)
        
        if sys_result.success and sys_result.backup_path:
            if self.config.external_backup_dir:
                await self._copy_to_external(sys_result.backup_path)
        
        # Clean up old backups
        self.cleanup_old_backups(backup_type)
        
        # Generate backup report
        await self._generate_backup_report(results, backup_type)
        
        successful_backups = [r for r in results if r.success]
        logger.info(f"Full backup completed: {len(successful_backups)}/{len(results)} backups successful")
        
        return results
    
    async def _copy_to_external(self, backup_path: Path):
        """Copy backup to external storage"""
        if not self.config.external_backup_dir:
            return
        
        try:
            external_path = self.config.external_backup_dir / backup_path.name
            shutil.copy2(backup_path, external_path)
            logger.info(f"Copied to external storage: {external_path}")
        except Exception as e:
            logger.error(f"Failed to copy to external storage: {e}")
    
    async def _generate_backup_report(self, results: List[BackupResult], backup_type: str):
        """Generate backup report"""
        report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"backup_report_{backup_type}_{report_timestamp}.json"
        report_path = self.config.local_backup_dir / report_filename
        
        try:
            report_data = {
                'backup_session': {
                    'timestamp': report_timestamp,
                    'backup_type': backup_type,
                    'total_backups': len(results),
                    'successful_backups': len([r for r in results if r.success]),
                    'failed_backups': len([r for r in results if not r.success]),
                    'total_size_bytes': sum(r.file_size_bytes for r in results if r.success),
                    'total_duration_seconds': sum(r.duration_seconds for r in results),
                },
                'backup_results': [asdict(result) for result in results],
                'system_info': {
                    'hostname': os.uname().nodename,
                    'disk_usage': shutil.disk_usage(self.config.local_backup_dir)._asdict(),
                    'memory_usage': psutil.virtual_memory().percent,
                    'cpu_usage': psutil.cpu_percent(),
                }
            }
            
            with open(report_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            logger.info(f"Backup report generated: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate backup report: {e}")
    
    def restore_database(self, backup_file: Path) -> bool:
        """Restore database from backup"""
        logger.info(f"Restoring database from: {backup_file}")
        
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config.postgres_password
            
            cmd = [
                'pg_restore',
                '-h', self.config.postgres_host,
                '-p', str(self.config.postgres_port),
                '-U', self.config.postgres_username,
                '-d', self.config.postgres_database,
                '--clean',
                '--create',
                '--verbose',
                str(backup_file)
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes
            )
            
            if result.returncode != 0:
                logger.error(f"Database restore failed: {result.stderr}")
                return False
            
            logger.info("Database restore completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False

def load_config() -> BackupConfig:
    """Load backup configuration"""
    project_root = Path(__file__).parent.parent
    config_file = project_root / 'config' / 'backup.yaml'
    
    # Default configuration
    default_config = {
        'local_backup_dir': project_root / 'backups',
        'external_backup_dir': None,
        'cloud_backup_enabled': False,
        'postgres_host': os.getenv('POSTGRES_HOST', 'localhost'),
        'postgres_port': int(os.getenv('POSTGRES_PORT', '5432')),
        'postgres_database': os.getenv('POSTGRES_DATABASE', 'smartarb'),
        'postgres_username': os.getenv('POSTGRES_USERNAME', 'smartarb_user'),
        'postgres_password': os.getenv('POSTGRES_PASSWORD', ''),
        'keep_daily': 7,
        'keep_weekly': 4,
        'keep_monthly': 12,
        'compress_backups': True,
        'compression_level': 6,
        'encrypt_backups': False,
        'aws_s3_bucket': os.getenv('AWS_S3_BUCKET'),
        'aws_access_key': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'aws_region': os.getenv('AWS_REGION', 'us-east-1'),
        'check_disk_space': True,
        'min_free_space_gb': 2.0,
        'use_external_storage': False,
    }
    
    # Load from config file if exists
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                file_config = yaml.safe_load(f)
                default_config.update(file_config.get('backup', {}))
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
    
    # Convert paths
    default_config['local_backup_dir'] = Path(default_config['local_backup_dir'])
    if default_config['external_backup_dir']:
        default_config['external_backup_dir'] = Path(default_config['external_backup_dir'])
    
    return BackupConfig(**default_config)

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='SmartArb Engine Backup System')
    parser.add_argument('--type', choices=['daily', 'weekly', 'monthly'], 
                       default='daily', help='Backup type')
    parser.add_argument('--database-only', action='store_true', help='Backup database only')
    parser.add_argument('--app-data-only', action='store_true', help='Backup application data only')
    parser.add_argument('--restore-database', metavar='BACKUP_FILE', 
                       help='Restore database from backup file')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old backups')
    parser.add_argument('--list-backups', action='store_true', help='List available backups')
    parser.add_argument('--schedule', action='store_true', help='Run in scheduler mode')
    parser.add_argument('--verify', metavar='BACKUP_FILE', help='Verify backup integrity')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config()
    backup_manager = BackupManager(config)
    
    try:
        if args.restore_database:
            backup_file = Path(args.restore_database)
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return 1
            
            success = backup_manager.restore_database(backup_file)
            return 0 if success else 1
        
        elif args.cleanup:
            for backup_type in ['daily', 'weekly', 'monthly']:
                backup_manager.cleanup_old_backups(backup_type)
            return 0
        
        elif args.list_backups:
            backups = list(config.local_backup_dir.glob("*backup_*.tar.gz"))
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            print(f"Available backups in {config.local_backup_dir}:")
            for backup in backups[:20]:  # Show latest 20
                size_mb = backup.stat().st_size / 1024 / 1024
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"  {backup.name} ({size_mb:.1f}MB, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
            
            return 0
        
        elif args.schedule:
            logger.info("Starting backup scheduler...")
            
            # Schedule backups
            schedule.every().day.at("02:00").do(
                lambda: asyncio.create_task(backup_manager.create_full_backup("daily"))
            )
            schedule.every().sunday.at("03:00").do(
                lambda: asyncio.create_task(backup_manager.create_full_backup("weekly"))
            )
            schedule.every().month.at("04:00").do(
                lambda: asyncio.create_task(backup_manager.create_full_backup("monthly"))
            )
            
            while True:
                schedule.run_pending()
                await asyncio.sleep(60)  # Check every minute
        
        else:
            # Perform backup
            if args.database_only:
                result = await backup_manager.backup_database(args.type)
                results = [result]
            elif args.app_data_only:
                result = await backup_manager.backup_application_data(args.type)
                results = [result]
            else:
                results = await backup_manager.create_full_backup(args.type)
            
            # Report results
            successful = len([r for r in results if r.success])
            total = len(results)
            
            if successful == total:
                logger.info(f"✅ All backups successful ({successful}/{total})")
                return 0
            else:
                logger.error(f"❌ Some backups failed ({successful}/{total})")
                return 1
                
    except KeyboardInterrupt:
        logger.info("Backup interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Backup failed with exception: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))