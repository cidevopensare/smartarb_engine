#!/usr/bin/env python3
"""
SmartArb Engine - Backup and Recovery System
Comprehensive backup and restore functionality for configurations, database, and logs
"""

import os
import sys
import shutil
import tarfile
import gzip
import json
import yaml
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
import logging
import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SmartArbBackup:
    """SmartArb Engine Backup and Recovery System"""
    
    def __init__(self, smartarb_root: str = "/opt/smartarb/smartarb-engine"):
        self.smartarb_root = Path(smartarb_root)
        self.backup_root = self.smartarb_root / "backups"
        self.config_dir = self.smartarb_root / "config"
        self.logs_dir = self.smartarb_root / "logs"
        self.data_dir = self.smartarb_root / "data"
        
        # Ensure backup directory exists
        self.backup_root.mkdir(exist_ok=True)
        
        # Database configuration
        self.db_config = self._load_db_config()
        
        # Backup retention
        self.retention_days = 30
        self.max_backups = 10
    
    def _load_db_config(self) -> Dict[str, Any]:
        """Load database configuration"""
        try:
            config_file = self.config_dir / "settings.yaml"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    return config.get('database', {}).get('postgresql', {})
        except Exception as e:
            logger.warning(f"Could not load database config: {e}")
        
        # Default configuration
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'smartarb',
            'username': 'smartarb_user',
            'password': os.getenv('POSTGRES_PASSWORD', '')
        }
    
    def create_full_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a complete backup of SmartArb Engine"""
        
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"smartarb_backup_{timestamp}"
        
        backup_dir = self.backup_root / backup_name
        backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"Creating full backup: {backup_name}")
        
        try:
            # 1. Backup configuration files
            self._backup_configuration(backup_dir)
            
            # 2. Backup database
            self._backup_database(backup_dir)
            
            # 3. Backup logs (last 7 days)
            self._backup_logs(backup_dir, days=7)
            
            # 4. Backup trading data
            self._backup_trading_data(backup_dir)
            
            # 5. Create backup manifest
            self._create_backup_manifest(backup_dir, backup_name)
            
            # 6. Compress backup
            archive_path = self._compress_backup(backup_dir)
            
            # 7. Cleanup temporary directory
            shutil.rmtree(backup_dir)
            
            # 8. Cleanup old backups
            self._cleanup_old_backups()
            
            logger.info(f"Backup completed successfully: {archive_path}")
            return str(archive_path)
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Cleanup on failure
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            raise
    
    def _backup_configuration(self, backup_dir: Path):
        """Backup configuration files"""
        logger.info("Backing up configuration files...")
        
        config_backup_dir = backup_dir / "config"
        config_backup_dir.mkdir(exist_ok=True)
        
        # Configuration files to backup
        config_files = [
            "settings.yaml",
            "exchanges.yaml", 
            "strategies.yaml",
            ".env"
        ]
        
        for config_file in config_files:
            source = self.config_dir.parent / config_file
            if source.exists():
                # Sanitize sensitive data for .env file
                if config_file == ".env":
                    self._backup_env_file_sanitized(source, config_backup_dir / config_file)
                else:
                    shutil.copy2(source, config_backup_dir)
                logger.debug(f"Backed up: {config_file}")
        
        # Copy entire config directory
        if self.config_dir.exists():
            for item in self.config_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, config_backup_dir)
    
    def _backup_env_file_sanitized(self, source: Path, dest: Path):
        """Backup .env file with sanitized sensitive data"""
        try:
            with open(source, 'r') as f:
                lines = f.readlines()
            
            sanitized_lines = []
            for line in lines:
                if '=' in line and not line.strip().startswith('#'):
                    key, _ = line.split('=', 1)
                    # Keep structure but mask sensitive values
                    if any(sensitive in key.upper() for sensitive in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
                        sanitized_lines.append(f"{key}=***REDACTED***\n")
                    else:
                        sanitized_lines.append(line)
                else:
                    sanitized_lines.append(line)
            
            with open(dest, 'w') as f:
                f.writelines(sanitized_lines)
                
        except Exception as e:
            logger.warning(f"Could not backup .env file: {e}")
    
    def _backup_database(self, backup_dir: Path):
        """Backup PostgreSQL database"""
        logger.info("Backing up database...")
        
        db_backup_dir = backup_dir / "database"
        db_backup_dir.mkdir(exist_ok=True)
        
        # Set up PostgreSQL environment
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_config.get('password', '')
        
        # Database dump file
        dump_file = db_backup_dir / "smartarb_database.sql"
        
        try:
            # Create database dump
            cmd = [
                'pg_dump',
                f"--host={self.db_config.get('host', 'localhost')}",
                f"--port={self.db_config.get('port', 5432)}",
                f"--username={self.db_config.get('username', 'smartarb_user')}",
                '--format=custom',
                '--compress=9',
                '--verbose',
                '--no-password',
                f"--file={dump_file}",
                self.db_config.get('database', 'smartarb')
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            logger.info(f"Database backup created: {dump_file}")
            
            # Create schema-only backup for reference
            schema_file = db_backup_dir / "schema.sql"
            cmd_schema = cmd.copy()
            cmd_schema[-2] = f"--file={schema_file}"
            cmd_schema.insert(-3, "--schema-only")
            
            subprocess.run(cmd_schema, env=env, capture_output=True)
            
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            # Create a dummy file to indicate failure
            with open(db_backup_dir / "backup_failed.txt", 'w') as f:
                f.write(f"Database backup failed: {e}\n")
                f.write(f"Timestamp: {datetime.now()}\n")
    
    def _backup_logs(self, backup_dir: Path, days: int = 7):
        """Backup recent log files"""
        logger.info(f"Backing up logs (last {days} days)...")
        
        logs_backup_dir = backup_dir / "logs"
        logs_backup_dir.mkdir(exist_ok=True)
        
        if not self.logs_dir.exists():
            logger.warning("Logs directory not found")
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for log_file in self.logs_dir.iterdir():
            if log_file.is_file() and log_file.suffix in ['.log', '.json']:
                # Check file modification time
                if datetime.fromtimestamp(log_file.stat().st_mtime) >= cutoff_date:
                    # Compress log file
                    compressed_file = logs_backup_dir / f"{log_file.name}.gz"
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    logger.debug(f"Backed up log: {log_file.name}")
    
    def _backup_trading_data(self, backup_dir: Path):
        """Backup trading data and performance metrics"""
        logger.info("Backing up trading data...")
        
        data_backup_dir = backup_dir / "data"
        data_backup_dir.mkdir(exist_ok=True)
        
        if self.data_dir.exists():
            # Copy all files in data directory
            for item in self.data_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, data_backup_dir)
                elif item.is_dir():
                    shutil.copytree(item, data_backup_dir / item.name)
        
        # Export performance metrics from database if available
        self._export_performance_data(data_backup_dir)
    
    def _export_performance_data(self, data_backup_dir: Path):
        """Export performance data from database"""
        try:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config.get('password', '')
            
            # Export key tables as CSV
            tables_to_export = [
                'opportunities',
                'executions', 
                'performance_metrics',
                'balances'
            ]
            
            for table in tables_to_export:
                csv_file = data_backup_dir / f"{table}.csv"
                cmd = [
                    'psql',
                    f"--host={self.db_config.get('host', 'localhost')}",
                    f"--port={self.db_config.get('port', 5432)}",
                    f"--username={self.db_config.get('username', 'smartarb_user')}",
                    '--no-password',
                    '--command',
                    f"\\copy {table} TO '{csv_file}' WITH CSV HEADER;",
                    self.db_config.get('database', 'smartarb')
                ]
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.debug(f"Exported table: {table}")
                    
        except Exception as e:
            logger.warning(f"Could not export performance data: {e}")
    
    def _create_backup_manifest(self, backup_dir: Path, backup_name: str):
        """Create backup manifest with metadata"""
        manifest = {
            'backup_name': backup_name,
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'smartarb_root': str(self.smartarb_root),
            'contents': {
                'configuration': True,
                'database': (backup_dir / "database").exists(),
                'logs': (backup_dir / "logs").exists(),
                'trading_data': (backup_dir / "data").exists()
            },
            'files': [],
            'database_config': {
                'host': self.db_config.get('host'),
                'database': self.db_config.get('database'),
                'username': self.db_config.get('username')
                # Don't include password in manifest
            }
        }
        
        # List all files in backup
        for root, dirs, files in os.walk(backup_dir):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(backup_dir)
                manifest['files'].append({
                    'path': str(relative_path),
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
        
        # Write manifest
        manifest_file = backup_dir / "backup_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Backup manifest created: {len(manifest['files'])} files")
    
    def _compress_backup(self, backup_dir: Path) -> str:
        """Compress backup directory into tar.gz archive"""
        logger.info("Compressing backup...")
        
        archive_name = f"{backup_dir.name}.tar.gz"
        archive_path = self.backup_root / archive_name
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(backup_dir, arcname=backup_dir.name)
        
        logger.info(f"Backup compressed: {archive_path} ({archive_path.stat().st_size // 1024 // 1024} MB)")
        return str(archive_path)
    
    def _cleanup_old_backups(self):
        """Clean up old backup files"""
        logger.info("Cleaning up old backups...")
        
        # Get all backup files
        backup_files = list(self.backup_root.glob("smartarb_backup_*.tar.gz"))
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Remove old backups beyond retention
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        removed_count = 0
        for backup_file in backup_files[self.max_backups:]:
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_date:
                backup_file.unlink()
                removed_count += 1
                logger.debug(f"Removed old backup: {backup_file.name}")
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} old backup(s)")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = []
        
        for backup_file in self.backup_root.glob("smartarb_backup_*.tar.gz"):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'path': str(backup_file),
                'size_mb': stat.st_size // 1024 // 1024,
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'age_days': (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
            })
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def restore_backup(self, backup_path: str, restore_database: bool = True, 
                      restore_config: bool = True, dry_run: bool = False):
        """Restore from backup archive"""
        logger.info(f"Restoring backup: {backup_path}")
        
        if dry_run:
            logger.info("DRY RUN - No changes will be made")
        
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Extract backup to temporary directory
        temp_dir = self.backup_root / f"restore_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Extract archive
            logger.info("Extracting backup archive...")
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            # Find extracted directory
            extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
            if not extracted_dirs:
                raise Exception("No directories found in backup archive")
            
            backup_content_dir = extracted_dirs[0]
            
            # Read manifest
            manifest_file = backup_content_dir / "backup_manifest.json"
            if manifest_file.exists():
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                logger.info(f"Restoring backup from {manifest['timestamp']}")
            
            # Restore configuration
            if restore_config:
                self._restore_configuration(backup_content_dir, dry_run)
            
            # Restore database
            if restore_database:
                self._restore_database(backup_content_dir, dry_run)
            
            # Restore trading data
            self._restore_trading_data(backup_content_dir, dry_run)
            
            logger.info("Backup restoration completed successfully")
            
        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            raise
            
        finally:
            # Cleanup temporary directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def _restore_configuration(self, backup_content_dir: Path, dry_run: bool):
        """Restore configuration files"""
        logger.info("Restoring configuration...")
        
        config_backup_dir = backup_content_dir / "config"
        if not config_backup_dir.exists():
            logger.warning("No configuration backup found")
            return
        
        if not dry_run:
            # Backup current configuration
            current_config_backup = self.backup_root / f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if self.config_dir.exists():
                shutil.copytree(self.config_dir, current_config_backup)
            
            # Restore configuration files
            for config_file in config_backup_dir.iterdir():
                if config_file.is_file():
                    dest = self.smartarb_root / config_file.name
                    if config_file.name == ".env":
                        dest = self.smartarb_root.parent / config_file.name
                    
                    shutil.copy2(config_file, dest)
                    logger.debug(f"Restored: {config_file.name}")
        else:
            logger.info("DRY RUN: Would restore configuration files")
    
    def _restore_database(self, backup_content_dir: Path, dry_run: bool):
        """Restore database from backup"""
        logger.info("Restoring database...")
        
        db_backup_dir = backup_content_dir / "database"
        if not db_backup_dir.exists():
            logger.warning("No database backup found")
            return
        
        dump_file = db_backup_dir / "smartarb_database.sql"
        if not dump_file.exists():
            logger.warning("Database dump file not found")
            return
        
        if not dry_run:
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config.get('password', '')
            
            # Drop and recreate database (be careful!)
            logger.warning("Dropping and recreating database...")
            
            # Restore database
            cmd = [
                'pg_restore',
                f"--host={self.db_config.get('host', 'localhost')}",
                f"--port={self.db_config.get('port', 5432)}",
                f"--username={self.db_config.get('username', 'smartarb_user')}",
                '--clean',
                '--create',
                '--verbose',
                '--no-password',
                f"--dbname={self.db_config.get('database', 'smartarb')}",
                str(dump_file)
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Database restore failed: {result.stderr}")
                raise Exception("Database restore failed")
            
            logger.info("Database restored successfully")
        else:
            logger.info("DRY RUN: Would restore database")
    
    def _restore_trading_data(self, backup_content_dir: Path, dry_run: bool):
        """Restore trading data"""
        logger.info("Restoring trading data...")
        
        data_backup_dir = backup_content_dir / "data"
        if not data_backup_dir.exists():
            logger.warning("No trading data backup found")
            return
        
        if not dry_run:
            # Backup current data
            if self.data_dir.exists():
                current_data_backup = self.backup_root / f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copytree(self.data_dir, current_data_backup)
            
            # Restore data
            self.data_dir.mkdir(exist_ok=True)
            for item in data_backup_dir.iterdir():
                dest = self.data_dir / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
                elif item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                logger.debug(f"Restored: {item.name}")
        else:
            logger.info("DRY RUN: Would restore trading data")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="SmartArb Engine Backup and Recovery")
    parser.add_argument('--smartarb-root', default='/opt/smartarb/smartarb-engine',
                       help='SmartArb Engine root directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create backup')
    backup_parser.add_argument('--name', help='Backup name (optional)')
    
    # List command
    subparsers.add_parser('list', help='List available backups')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('backup_path', help='Path to backup file')
    restore_parser.add_argument('--no-database', action='store_true',
                               help='Skip database restoration')
    restore_parser.add_argument('--no-config', action='store_true',
                               help='Skip configuration restoration')
    restore_parser.add_argument('--dry-run', action='store_true',
                               help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    backup_system = SmartArbBackup(args.smartarb_root)
    
    try:
        if args.command == 'backup':
            archive_path = backup_system.create_full_backup(args.name)
            print(f"Backup created: {archive_path}")
            
        elif args.command == 'list':
            backups = backup_system.list_backups()
            if not backups:
                print("No backups found")
            else:
                print(f"{'Name':<30} {'Size (MB)':<10} {'Age (days)':<12} {'Created'}")
                print("-" * 80)
                for backup in backups:
                    print(f"{backup['name']:<30} {backup['size_mb']:<10} {backup['age_days']:<12} {backup['created']}")
                    
        elif args.command == 'restore':
            backup_system.restore_backup(
                args.backup_path,
                restore_database=not args.no_database,
                restore_config=not args.no_config,
                dry_run=args.dry_run
            )
            print("Restore completed successfully")
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
