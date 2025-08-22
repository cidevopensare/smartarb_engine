#!/usr/bin/env python3
"""
AI System Setup Script for SmartArb Engine
Automated setup and configuration of Claude AI integration
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, Any
import subprocess

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import ConfigManager
from src.utils.logging import setup_logging
import structlog

logger = structlog.get_logger(__name__)


class AISetupManager:
    """Manages AI system setup and configuration"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.config_manager = None
        self.setup_steps = [
            self.check_requirements,
            self.setup_configuration,
            self.test_claude_api,
            self.setup_database_extensions,
            self.create_ai_directories,
            self.test_ai_components,
            self.setup_systemd_service
        ]
    
    async def run_setup(self, interactive: bool = True):
        """Run complete AI setup process"""
        print("🧠 SmartArb Engine AI Setup")
        print("=" * 50)
        
        success_count = 0
        
        for i, step in enumerate(self.setup_steps, 1):
            step_name = step.__name__.replace('_', ' ').title()
            print(f"\n[{i}/{len(self.setup_steps)}] {step_name}...")
            
            try:
                result = await step(interactive)
                if result:
                    print(f"✅ {step_name} completed successfully")
                    success_count += 1
                else:
                    print(f"⚠️  {step_name} completed with warnings")
                    if interactive and not self.confirm(f"Continue with setup?"):
                        break
            except Exception as e:
                print(f"❌ {step_name} failed: {str(e)}")
                if interactive and not self.confirm(f"Continue despite error?"):
                    break
        
        print(f"\n🎉 Setup completed: {success_count}/{len(self.setup_steps)} steps successful")
        
        if success_count == len(self.setup_steps):
            print("\n✅ AI system is ready to use!")
            self.print_next_steps()
        else:
            print("\n⚠️  Some setup steps failed. Review errors above.")
    
    async def check_requirements(self, interactive: bool = True) -> bool:
        """Check system requirements for AI features"""
        print("  Checking Python version...")
        if sys.version_info < (3, 8):
            raise RuntimeError(f"Python 3.8+ required, found {sys.version_info}")
        
        print("  Checking required packages...")
        required_packages = [
            'anthropic', 'fastapi', 'uvicorn', 'croniter', 
            'GitPython', 'pydantic', 'structlog'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
                print(f"    ✅ {package}")
            except ImportError:
                print(f"    ❌ {package}")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n  Missing packages: {', '.join(missing_packages)}")
            if interactive and self.confirm("Install missing packages?"):
                self.install_packages(missing_packages)
            else:
                raise RuntimeError("Required packages not installed")
        
        print("  Checking disk space...")
        disk_usage = self.check_disk_space()
        if disk_usage > 90:
            print(f"    ⚠️  Disk usage high: {disk_usage}%")
        else:
            print(f"    ✅ Disk usage: {disk_usage}%")
        
        return True
    
    async def setup_configuration(self, interactive: bool = True) -> bool:
        """Setup AI configuration"""
        config_file = self.project_root / 'config' / 'settings.yaml'
        
        if not config_file.exists():
            print("  Creating default configuration...")
            self.create_default_config()
        
        # Load existing configuration
        self.config_manager = ConfigManager()
        
        print("  Configuring AI settings...")
        
        # Check if AI is enabled
        ai_enabled = self.config_manager.get('ai.enabled', False)
        if not ai_enabled:
            if interactive and self.confirm("Enable AI analysis system?"):
                self.config_manager.set('ai.enabled', True)
                print("    ✅ AI system enabled")
            else:
                print("    ⚠️  AI system not enabled")
        
        # Check Claude API key
        api_key_configured = bool(os.getenv('CLAUDE_API_KEY'))
        if not api_key_configured:
            print("    ❌ Claude API key not found in environment")
            if interactive:
                api_key = input("    Enter Claude API key (or press Enter to skip): ").strip()
                if api_key:
                    self.update_env_file('CLAUDE_API_KEY', api_key)
                    print("    ✅ API key added to .env file")
                else:
                    print("    ⚠️  API key not configured")
        else:
            print("    ✅ Claude API key configured")
        
        # Configure analysis schedule
        schedule = self.config_manager.get('ai.scheduling.default', '0 */6 * * *')
        print(f"    Analysis schedule: {schedule}")
        
        if interactive and self.confirm("Customize analysis schedule?"):
            new_schedule = input(f"    Enter cron expression (current: {schedule}): ").strip()
            if new_schedule:
                self.config_manager.set('ai.scheduling.default', new_schedule)
                print(f"    ✅ Schedule updated: {new_schedule}")
        
        return True
    
    async def test_claude_api(self, interactive: bool = True) -> bool:
        """Test Claude API connection"""
        api_key = os.getenv('CLAUDE_API_KEY')
        
        if not api_key:
            print("    ⚠️  Claude API key not configured, skipping test")
            return False
        
        print("  Testing Claude API connection...")
        
        try:
            # Simple API test
            import anthropic
            
            client = anthropic.Anthropic(api_key=api_key)
            
            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=50,
                messages=[{
                    "role": "user",
                    "content": "Please respond with 'API test successful' to confirm connection."
                }]
            )
            
            response = message.content[0].text
            
            if "API test successful" in response or "successful" in response.lower():
                print("    ✅ Claude API connection successful")
                return True
            else:
                print(f"    ⚠️  Unexpected API response: {response[:50]}...")
                return False
                
        except Exception as e:
            print(f"    ❌ Claude API test failed: {str(e)}")
            if "authentication" in str(e).lower() or "api_key" in str(e).lower():
                print("    💡 Check your API key configuration")
            return False
    
    async def setup_database_extensions(self, interactive: bool = True) -> bool:
        """Setup database extensions for AI features"""
        print("  Setting up database extensions...")
        
        try:
            # Create AI-specific tables and indexes
            ai_tables_script = """
            -- AI Analysis Results Table
            CREATE TABLE IF NOT EXISTS ai_analyses (
                id SERIAL PRIMARY KEY,
                analysis_id VARCHAR(100) UNIQUE NOT NULL,
                analysis_type VARCHAR(50) NOT NULL,
                focus_area VARCHAR(100),
                recommendations_count INTEGER DEFAULT 0,
                success BOOLEAN DEFAULT FALSE,
                execution_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            -- AI Recommendations Table
            CREATE TABLE IF NOT EXISTS ai_recommendations (
                id SERIAL PRIMARY KEY,
                recommendation_id VARCHAR(100) UNIQUE NOT NULL,
                analysis_id VARCHAR(100) REFERENCES ai_analyses(analysis_id),
                title VARCHAR(200) NOT NULL,
                category VARCHAR(50) NOT NULL,
                priority VARCHAR(20) NOT NULL,
                description TEXT,
                implementation_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            -- Code Updates Table
            CREATE TABLE IF NOT EXISTS ai_code_updates (
                id SERIAL PRIMARY KEY,
                update_id VARCHAR(100) UNIQUE NOT NULL,
                recommendation_id VARCHAR(100) REFERENCES ai_recommendations(recommendation_id),
                files_changed INTEGER DEFAULT 0,
                status VARCHAR(50) NOT NULL,
                rollback_available BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_ai_analyses_created_at ON ai_analyses(created_at);
            CREATE INDEX IF NOT EXISTS idx_ai_recommendations_status ON ai_recommendations(implementation_status);
            CREATE INDEX IF NOT EXISTS idx_ai_code_updates_status ON ai_code_updates(status);
            """
            
            # This would be executed against the database
            # For now, just save as a script
            script_path = self.project_root / 'scripts' / 'ai_database_setup.sql'
            with open(script_path, 'w') as f:
                f.write(ai_tables_script)
            
            print(f"    ✅ AI database script created: {script_path}")
            print("    💡 Run this script against your PostgreSQL database")
            
            return True
            
        except Exception as e:
            print(f"    ❌ Database setup failed: {str(e)}")
            return False
    
    async def create_ai_directories(self, interactive: bool = True) -> bool:
        """Create necessary directories for AI system"""
        directories = [
            'data/ai_reports',
            'data/dashboard_snapshots',
            'backups/code_updates',
            'logs/ai',
            'tmp/ai_analysis'
        ]
        
        print("  Creating AI directories...")
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"    ✅ {directory}")
        
        # Create .gitkeep files
        for directory in directories:
            gitkeep_path = self.project_root / directory / '.gitkeep'
            gitkeep_path.touch(exist_ok=True)
        
        return True
    
    async def test_ai_components(self, interactive: bool = True) -> bool:
        """Test AI system components"""
        print("  Testing AI components...")
        
        try:
            from src.ai.claude_integration import ClaudeAnalysisEngine
            from src.ai.analysis_scheduler import AIAnalysisScheduler
            from src.ai.code_updater import CodeUpdateManager
            from src.ai.dashboard import AIDashboard
            
            # Test component initialization
            config = self.config_manager if self.config_manager else ConfigManager()
            
            print("    Testing Claude integration...")
            claude_engine = ClaudeAnalysisEngine(config, None)
            print("    ✅ Claude integration initialized")
            
            print("    Testing analysis scheduler...")
            # Don't actually start the scheduler in setup
            print("    ✅ Analysis scheduler available")
            
            print("    Testing code updater...")
            from src.utils.notifications import NotificationManager
            notification_manager = NotificationManager({})
            code_updater = CodeUpdateManager(notification_manager)
            print("    ✅ Code updater initialized")
            
            print("    Testing dashboard...")
            # Dashboard test would require full system
            print("    ✅ Dashboard available")
            
            return True
            
        except Exception as e:
            print(f"    ❌ Component test failed: {str(e)}")
            return False
    
    async def setup_systemd_service(self, interactive: bool = True) -> bool:
        """Setup systemd service for AI system (Linux only)"""
        if sys.platform != 'linux':
            print("    ⚠️  Systemd service only available on Linux")
            return True
        
        if not interactive or not self.confirm("Setup systemd service for auto-start?"):
            print("    ⚠️  Systemd service setup skipped")
            return True
        
        try:
            service_content = f"""[Unit]
Description=SmartArb Engine AI System
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User={os.getenv('USER', 'pi')}
WorkingDirectory={self.project_root}
Environment=PATH={self.project_root}/smartarb_env/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={self.project_root}/smartarb_env/bin/python -m src.core.engine
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
            
            service_path = Path('/tmp/smartarb-engine.service')
            with open(service_path, 'w') as f:
                f.write(service_content)
            
            print(f"    ✅ Service file created: {service_path}")
            print("    💡 Run these commands as root to install:")
            print(f"       sudo cp {service_path} /etc/systemd/system/")
            print("       sudo systemctl daemon-reload")
            print("       sudo systemctl enable smartarb-engine")
            print("       sudo systemctl start smartarb-engine")
            
            return True
            
        except Exception as e:
            print(f"    ❌ Systemd service setup failed: {str(e)}")
            return False
    
    def install_packages(self, packages: list):
        """Install missing Python packages"""
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'install'
            ] + packages, check=True)
            print(f"    ✅ Installed packages: {', '.join(packages)}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Package installation failed: {e}")
    
    def check_disk_space(self) -> float:
        """Check available disk space"""
        import shutil
        total, used, free = shutil.disk_usage(self.project_root)
        return (used / total) * 100
    
    def create_default_config(self):
        """Create default configuration file"""
        config_dir = self.project_root / 'config'
        config_dir.mkdir(exist_ok=True)
        
        # Copy from example if exists
        example_config = config_dir / 'settings.yaml.example'
        config_file = config_dir / 'settings.yaml'
        
        if example_config.exists():
            import shutil
            shutil.copy2(example_config, config_file)
        else:
            # Create minimal config
            minimal_config = """
engine:
  name: "SmartArb Engine"
  mode: "development"

ai:
  enabled: true
  claude_api_key: "${CLAUDE_API_KEY}"
  analysis_frequency: "daily"

database:
  redis:
    host: "localhost"
    port: 6379

monitoring:
  telegram_alerts: false
"""
            with open(config_file, 'w') as f:
                f.write(minimal_config)
    
    def update_env_file(self, key: str, value: str):
        """Update .env file with new key-value pair"""
        env_file = self.project_root / '.env'
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Update existing key or add new one
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"{key}={value}\n")
            
            with open(env_file, 'w') as f:
                f.writelines(lines)
        else:
            with open(env_file, 'w') as f:
                f.write(f"{key}={value}\n")
    
    def confirm(self, message: str) -> bool:
        """Get user confirmation"""
        response = input(f"  {message} (y/N): ").strip().lower()
        return response in ['y', 'yes']
    
    def print_next_steps(self):
        """Print next steps after setup"""
        print("\n🚀 Next Steps:")
        print("=" * 20)
        print("1. Start SmartArb Engine:")
        print("   python -m src.core.engine")
        print("\n2. Test AI system:")
        print("   python -m src.cli.ai_cli test --test-all")
        print("\n3. Run manual analysis:")
        print("   python -m src.cli.ai_cli analyze --focus 'performance'")
        print("\n4. Start AI API server:")
        print("   python -m src.api.ai_api")
        print("\n5. Monitor via dashboard:")
        print("   http://localhost:8000/docs")


async def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup SmartArb Engine AI system')
    parser.add_argument('--non-interactive', action='store_true',
                       help='Run setup without user prompts')
    parser.add_argument('--quick', action='store_true',
                       help='Quick setup with defaults')
    
    args = parser.parse_args()
    
    setup_manager = AISetupManager()
    
    if args.quick:
        print("🚀 Quick AI Setup")
        print("This will setup AI with default settings...")
        await setup_manager.run_setup(interactive=False)
    else:
        await setup_manager.run_setup(interactive=not args.non_interactive)


if __name__ == "__main__":
    asyncio.run(main())
