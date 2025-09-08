#!/usr/bin/env python3
"""
SmartArb Engine - Secure Secrets Generator
Generates and manages secure secrets for production deployment
"""

import os
import sys
import secrets
import string
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import base64
import datetime
import getpass

logger = structlog.get_logger(__name__)


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecretGenerator:
    """Secure secret generation and management"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.secrets_dir = project_root / 'secrets'
        self.secrets_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Master encryption key file
        self.master_key_file = self.secrets_dir / '.master.key'
        
    def generate_password(self, length: int = 32, exclude_ambiguous: bool = True) -> str:
        """Generate a cryptographically secure password"""
        if exclude_ambiguous:
            # Exclude ambiguous characters: 0, O, l, 1, I
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
            alphabet = alphabet.translate(str.maketrans('', '', '0Ol1I'))
        else:
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
        
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_api_key(self, length: int = 64) -> str:
        """Generate an API key"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_secret_key(self, length: int = 64) -> str:
        """Generate a secret key for sessions/JWT"""
        return secrets.token_urlsafe(length)
    
    def generate_encryption_key(self) -> bytes:
        """Generate a Fernet encryption key"""
        return Fernet.generate_key()
    
    def generate_master_key(self, password: Optional[str] = None) -> bytes:
        """Generate or derive master encryption key"""
        if password:
            # Derive key from password
            password_bytes = password.encode('utf-8')
            salt = os.urandom(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
            
            # Save salt for later key derivation
            with open(self.secrets_dir / '.salt', 'wb') as f:
                f.write(salt)
            
            return key
        else:
            # Generate random key
            return Fernet.generate_key()
    
    def get_or_create_master_key(self, password: Optional[str] = None) -> bytes:
        """Get existing master key or create new one"""
        if self.master_key_file.exists():
            with open(self.master_key_file, 'rb') as f:
                return f.read()
        else:
            key = self.generate_master_key(password)
            
            # Save master key with restricted permissions
            with open(self.master_key_file, 'wb') as f:
                f.write(key)
            self.master_key_file.chmod(0o600)
            
            return key
    
    def encrypt_secret(self, data: str, key: bytes) -> bytes:
        """Encrypt a secret with the master key"""
        fernet = Fernet(key)
        return fernet.encrypt(data.encode('utf-8'))
    
    def decrypt_secret(self, encrypted_data: bytes, key: bytes) -> str:
        """Decrypt a secret with the master key"""
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data).decode('utf-8')
    
    def generate_ssl_certificate(self, domain: str, days_valid: int = 365) -> tuple:
        """Generate self-signed SSL certificate for testing"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"SmartArb Engine"),
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Serialize private key
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize certificate
        cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
        
        return private_key_bytes, cert_bytes
    
    def generate_all_secrets(self, environment: str = "development") -> Dict[str, Any]:
        """Generate all required secrets for the application"""
        logger.info(f"Generating secrets for {environment} environment...")
        
        secrets_data = {
            # Database secrets
            'postgres_password': self.generate_password(32),
            'postgres_admin_password': self.generate_password(32),
            
            # Redis secrets
            'redis_password': self.generate_password(32),
            
            # Application secrets
            'app_secret_key': self.generate_secret_key(64),
            'encryption_key': base64.urlsafe_b64encode(self.generate_encryption_key()).decode('ascii'),
            'jwt_secret': self.generate_secret_key(64),
            
            # API Keys (placeholders - user must fill these)
            'kraken_api_key': 'your_kraken_api_key_here',
            'kraken_api_secret': 'your_kraken_api_secret_here',
            'bybit_api_key': 'your_bybit_api_key_here',
            'bybit_api_secret': 'your_bybit_api_secret_here',
            'mexc_api_key': 'your_mexc_api_key_here',
            'mexc_api_secret': 'your_mexc_api_secret_here',
            
            # AI API Keys (placeholders)
            'claude_api_key': 'your_claude_api_key_here',
            'openai_api_key': 'your_openai_api_key_here',
            
            # Notification secrets (placeholders)
            'telegram_bot_token': 'your_telegram_bot_token_here',
            'telegram_chat_id': 'your_telegram_chat_id_here',
            'discord_webhook_url': 'your_discord_webhook_url_here',
            
            # SMTP secrets (placeholders)
            'smtp_password': 'your_smtp_password_here',
            
            # Monitoring secrets
            'grafana_admin_password': self.generate_password(24),
            'prometheus_web_config_password': self.generate_password(32),
            
            # Generate timestamps and metadata
            'generated_at': datetime.datetime.utcnow().isoformat(),
            'environment': environment,
            'version': '1.0.0'
        }
        
        return secrets_data
    
    def save_secrets(self, secrets_data: Dict[str, Any], encrypt: bool = True) -> None:
        """Save secrets to individual files"""
        logger.info("Saving secrets to files...")
        
        # Get master key for encryption
        master_key = None
        if encrypt:
            master_key = self.get_or_create_master_key()
        
        # Create individual secret files
        for key, value in secrets_data.items():
            if key in ['generated_at', 'environment', 'version']:
                continue  # Skip metadata
                
            secret_file = self.secrets_dir / f'{key}.txt'
            
            if encrypt and master_key:
                # Encrypt and save
                encrypted_value = self.encrypt_secret(str(value), master_key)
                with open(secret_file, 'wb') as f:
                    f.write(encrypted_value)
            else:
                # Save as plain text
                with open(secret_file, 'w') as f:
                    f.write(str(value))
            
            # Set restrictive permissions
            secret_file.chmod(0o600)
        
        # Save metadata
        metadata = {
            'generated_at': secrets_data['generated_at'],
            'environment': secrets_data['environment'],
            'version': secrets_data['version'],
            'encrypted': encrypt,
            'files_created': list(secrets_data.keys())
        }
        
        metadata_file = self.secrets_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        metadata_file.chmod(0o600)
        
        logger.info(f"Saved {len(secrets_data)} secrets to {self.secrets_dir}")
    
    def generate_ssl_files(self, domain: str = "localhost") -> None:
        """Generate SSL certificate files"""
        logger.info(f"Generating SSL certificate for {domain}...")
        
        private_key_bytes, cert_bytes = self.generate_ssl_certificate(domain)
        
        # Save private key
        key_file = self.secrets_dir / 'ssl_key.pem'
        with open(key_file, 'wb') as f:
            f.write(private_key_bytes)
        key_file.chmod(0o600)
        
        # Save certificate
        cert_file = self.secrets_dir / 'ssl_cert.pem'
        with open(cert_file, 'wb') as f:
            f.write(cert_bytes)
        cert_file.chmod(0o644)
        
        logger.info(f"SSL certificate generated: {cert_file}")
        logger.info(f"SSL private key generated: {key_file}")
        logger.warning("This is a self-signed certificate for testing only!")
    
    def create_docker_env_file(self, secrets_data: Dict[str, Any]) -> None:
        """Create .env file for Docker Compose"""
        logger.info("Creating Docker environment file...")
        
        env_file = self.project_root / '.env.docker'
        
        env_content = f"""# SmartArb Engine - Docker Environment Variables
# Generated on {secrets_data['generated_at']}
# Environment: {secrets_data['environment']}

# Database Configuration
POSTGRES_PASSWORD={secrets_data['postgres_password']}
POSTGRES_ADMIN_PASSWORD={secrets_data['postgres_admin_password']}

# Redis Configuration
REDIS_PASSWORD={secrets_data['redis_password']}

# Application Configuration
APP_SECRET_KEY={secrets_data['app_secret_key']}
ENCRYPTION_KEY={secrets_data['encryption_key']}
JWT_SECRET={secrets_data['jwt_secret']}

# Exchange API Keys (CHANGE THESE!)
KRAKEN_API_KEY={secrets_data['kraken_api_key']}
KRAKEN_API_SECRET={secrets_data['kraken_api_secret']}
BYBIT_API_KEY={secrets_data['bybit_api_key']}
BYBIT_API_SECRET={secrets_data['bybit_api_secret']}
MEXC_API_KEY={secrets_data['mexc_api_key']}
MEXC_API_SECRET={secrets_data['mexc_api_secret']}

# AI API Keys (CHANGE THESE!)
CLAUDE_API_KEY={secrets_data['claude_api_key']}
OPENAI_API_KEY={secrets_data['openai_api_key']}

# Notification Configuration (CHANGE THESE!)
TELEGRAM_BOT_TOKEN={secrets_data['telegram_bot_token']}
TELEGRAM_CHAT_ID={secrets_data['telegram_chat_id']}
DISCORD_WEBHOOK_URL={secrets_data['discord_webhook_url']}

# Monitoring Configuration
GRAFANA_ADMIN_PASSWORD={secrets_data['grafana_admin_password']}
PROMETHEUS_WEB_CONFIG_PASSWORD={secrets_data['prometheus_web_config_password']}
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        env_file.chmod(0o600)
        
        logger.info(f"Docker environment file created: {env_file}")
    
    def create_kubernetes_secrets(self, secrets_data: Dict[str, Any]) -> None:
        """Create Kubernetes secrets YAML"""
        logger.info("Creating Kubernetes secrets...")
        
        # Encode secrets in base64
        encoded_secrets = {}
        for key, value in secrets_data.items():
            if key not in ['generated_at', 'environment', 'version']:
                encoded_value = base64.b64encode(str(value).encode('utf-8')).decode('ascii')
                encoded_secrets[key.replace('_', '-')] = encoded_value
        
        k8s_secrets = f"""apiVersion: v1
kind: Secret
metadata:
  name: smartarb-secrets
  namespace: default
type: Opaque
data:
  postgres-password: {encoded_secrets.get('postgres-password', '')}
  redis-password: {encoded_secrets.get('redis-password', '')}
  app-secret-key: {encoded_secrets.get('app-secret-key', '')}
  encryption-key: {encoded_secrets.get('encryption-key', '')}
  kraken-api-key: {encoded_secrets.get('kraken-api-key', '')}
  kraken-api-secret: {encoded_secrets.get('kraken-api-secret', '')}
  claude-api-key: {encoded_secrets.get('claude-api-key', '')}
  telegram-bot-token: {encoded_secrets.get('telegram-bot-token', '')}
---
apiVersion: v1
kind: Secret
metadata:
  name: smartarb-ssl
  namespace: default
type: kubernetes.io/tls
data:
  tls.crt: # Add your SSL certificate here (base64 encoded)
  tls.key: # Add your SSL private key here (base64 encoded)
"""
        
        k8s_file = self.project_root / 'k8s-secrets.yaml'
        with open(k8s_file, 'w') as f:
            f.write(k8s_secrets)
        k8s_file.chmod(0o600)
        
        logger.info(f"Kubernetes secrets created: {k8s_file}")
    
    def verify_secrets(self) -> Dict[str, bool]:
        """Verify that all required secrets exist"""
        logger.info("Verifying secrets...")
        
        required_secrets = [
            'postgres_password',
            'redis_password',
            'app_secret_key',
            'encryption_key'
        ]
        
        optional_secrets = [
            'kraken_api_key', 'bybit_api_key', 'mexc_api_key',
            'claude_api_key', 'telegram_bot_token'
        ]
        
        verification_results = {}
        
        for secret in required_secrets:
            secret_file = self.secrets_dir / f'{secret}.txt'
            verification_results[secret] = secret_file.exists()
        
        for secret in optional_secrets:
            secret_file = self.secrets_dir / f'{secret}.txt'
            verification_results[f"{secret}_optional"] = secret_file.exists()
        
        # Check SSL certificates
        ssl_cert = self.secrets_dir / 'ssl_cert.pem'
        ssl_key = self.secrets_dir / 'ssl_key.pem'
        verification_results['ssl_certificate'] = ssl_cert.exists() and ssl_key.exists()
        
        # Report results
        required_passed = sum(1 for k, v in verification_results.items() 
                            if not k.endswith('_optional') and k != 'ssl_certificate' and v)
        required_total = len(required_secrets)
        
        logger.info(f"Required secrets: {required_passed}/{required_total}")
        
        for secret, exists in verification_results.items():
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {secret}")
        
        return verification_results
    
    def rotate_secrets(self, secret_names: List[str]) -> None:
        """Rotate (regenerate) specific secrets"""
        logger.info(f"Rotating secrets: {secret_names}")
        
        # Load existing metadata
        metadata_file = self.secrets_dir / 'metadata.json'
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {'environment': 'development'}
        
        # Generate new secrets
        new_secrets = self.generate_all_secrets(metadata.get('environment', 'development'))
        
        # Only update specified secrets
        for secret_name in secret_names:
            if secret_name in new_secrets:
                secret_file = self.secrets_dir / f'{secret_name}.txt'
                
                # Backup old secret
                if secret_file.exists():
                    backup_file = self.secrets_dir / f'{secret_name}.txt.backup'
                    shutil.copy2(secret_file, backup_file)
                
                # Write new secret
                with open(secret_file, 'w') as f:
                    f.write(str(new_secrets[secret_name]))
                secret_file.chmod(0o600)
                
                logger.info(f"Rotated secret: {secret_name}")
    
    def cleanup_secrets(self) -> None:
        """Securely clean up secret files"""
        logger.info("Cleaning up secrets...")
        
        if not self.secrets_dir.exists():
            logger.info("No secrets directory found")
            return
        
        # Securely delete files
        for secret_file in self.secrets_dir.glob('*.txt'):
            try:
                # Overwrite with random data before deletion
                with open(secret_file, 'r+b') as f:
                    size = f.seek(0, 2)  # Get file size
                    f.seek(0)
                    f.write(os.urandom(size))
                    f.flush()
                    os.fsync(f.fileno())
                
                secret_file.unlink()
                logger.info(f"Securely deleted: {secret_file}")
                
            except Exception as e:
                logger.error(f"Failed to delete {secret_file}: {e}")
        
        # Remove other files
        for file in self.secrets_dir.glob('*'):
            if file.is_file():
                file.unlink()
        
        # Remove directory if empty
        try:
            self.secrets_dir.rmdir()
            logger.info("Secrets directory removed")
        except OSError:
            logger.warning("Secrets directory not empty - some files remain")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Generate secure secrets for SmartArb Engine')
    parser.add_argument('--environment', choices=['development', 'staging', 'production'], 
                       default='development', help='Target environment')
    parser.add_argument('--no-encrypt', action='store_true', help='Don\'t encrypt secrets')
    parser.add_argument('--generate-ssl', action='store_true', help='Generate self-signed SSL certificate')
    parser.add_argument('--domain', default='localhost', help='Domain for SSL certificate')
    parser.add_argument('--docker-env', action='store_true', help='Create Docker .env file')
    parser.add_argument('--k8s-secrets', action='store_true', help='Create Kubernetes secrets YAML')
    parser.add_argument('--verify', action='store_true', help='Verify existing secrets')
    parser.add_argument('--rotate', nargs='+', help='Rotate specific secrets')
    parser.add_argument('--cleanup', action='store_true', help='Securely delete all secrets')
    parser.add_argument('--master-password', action='store_true', 
                       help='Use password-derived master key for encryption')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Find project root
    project_root = Path(__file__).parent.parent
    generator = SecretGenerator(project_root)
    
    try:
        # Handle specific actions
        if args.cleanup:
            if input("Are you sure you want to delete all secrets? (yes/NO): ") == "yes":
                generator.cleanup_secrets()
            else:
                logger.info("Cleanup cancelled")
            return 0
        
        if args.verify:
            generator.verify_secrets()
            return 0
        
        if args.rotate:
            generator.rotate_secrets(args.rotate)
            return 0
        
        # Generate secrets
        encrypt = not args.no_encrypt
        master_password = None
        
        if args.master_password and encrypt:
            master_password = getpass.getpass("Enter master password for encryption: ")
            generator.get_or_create_master_key(master_password)
        
        secrets_data = generator.generate_all_secrets(args.environment)
        generator.save_secrets(secrets_data, encrypt=encrypt)
        
        # Generate SSL certificate if requested
        if args.generate_ssl:
            generator.generate_ssl_files(args.domain)
        
        # Create additional files
        if args.docker_env:
            generator.create_docker_env_file(secrets_data)
        
        if args.k8s_secrets:
            generator.create_kubernetes_secrets(secrets_data)
        
        # Final verification
        verification_results = generator.verify_secrets()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("Secrets generation completed!")
        logger.info("=" * 60)
        logger.info("IMPORTANT: Update the following placeholders with real values:")
        logger.info("- Exchange API keys (Kraken, Bybit, MEXC)")
        logger.info("- Claude AI API key")
        logger.info("- Telegram bot token and chat ID")
        logger.info("- SMTP credentials (if using email notifications)")
        logger.info("")
        logger.info("Secret files are stored in: {}".format(generator.secrets_dir))
        logger.info("Keep these files secure and never commit them to version control!")
        logger.info("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Secret generation failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())