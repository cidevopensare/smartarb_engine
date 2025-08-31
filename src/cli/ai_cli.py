#!/usr/bin/env python3
"""
SmartArb Engine AI CLI Interface
Command-line interface for interacting with Claude AI system
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import click
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)
from src.utils.config import ConfigManager


# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ai.claude_integration import ClaudeAnalysisEngine
from src.ai.analysis_scheduler import AIAnalysisScheduler
from src.ai.code_updater import CodeUpdateManager
from src.ai.dashboard import AIDashboard
from src.utils.config import ConfigManager
from src.utils.notifications import NotificationManager
from src.db.connection import DatabaseManager, initialize_database

logger = structlog.get_logger(__name__)


class AISystemManager:
    """Manager for AI system components"""
    
    def __init__(self):
        self.config = None
        self.claude_engine = None
        self.scheduler = None
        self.code_updater = None
        self.dashboard = None
        self.notification_manager = None
        self.db_manager = None
    
    async def initialize(self):
        """Initialize AI system components"""
        try:
            # Load configuration
            self.config = ConfigManager()
            
            # Initialize database
            self.db_manager = await initialize_database(self.config.to_dict())
            
            # Initialize notification manager
            self.notification_manager = NotificationManager(
                self.config.get('monitoring', {})
            )
            
            # Initialize AI components
            self.claude_engine = ClaudeAnalysisEngine(self.config, self.db_manager)
            self.code_updater = CodeUpdateManager(self.notification_manager)
            self.scheduler = AIAnalysisScheduler(
                self.config, self.db_manager, self.notification_manager
            )
            self.dashboard = AIDashboard(
                self.claude_engine, self.scheduler, 
                self.code_updater, self.notification_manager
            )
            
            logger.info("ai_system_manager_initialized")
            
        except Exception as e:
            logger.error("ai_system_initialization_failed", error=str(e))
            raise
    
    async def cleanup(self):
        """Cleanup AI system components"""
        if self.scheduler:
            await self.scheduler.stop()
        if self.db_manager:
            await self.db_manager.close()


# Global manager instance
ai_manager = AISystemManager()


@click.group()
@click.option('--config', '-c', default='config/settings.yaml', 
              help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config, verbose):
    """SmartArb Engine AI CLI - Intelligent Trading Analysis"""
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['verbose'] = verbose
    
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.option('--focus', '-f', help='Focus area for analysis')
@click.option('--prompt', '-p', help='Custom analysis prompt')
@click.pass_context
def analyze(ctx, focus, prompt):
    """Request AI analysis of current performance"""
    
    async def run_analysis():
        await ai_manager.initialize()
        
        try:
            if focus and prompt:
                result = await ai_manager.claude_engine.get_manual_analysis(
                    f"Focus: {focus}. Prompt: {prompt}"
                )
            elif focus:
                result = await ai_manager.scheduler.request_manual_analysis(focus)
            else:
                recommendations = await ai_manager.claude_engine.run_automated_analysis()
                if recommendations:
                    result = f"✅ Analysis complete! Found {len(recommendations)} recommendations.\n"
                    for i, rec in enumerate(recommendations[:3], 1):
                        result += f"\n{i}. [{rec.priority.upper()}] {rec.title}\n   {rec.description[:100]}..."
                else:
                    result = "❌ Analysis failed or no recommendations found."
            
            click.echo("\n🧠 AI Analysis Results:")
            click.echo("=" * 50)
            click.echo(result)
            
        finally:
            await ai_manager.cleanup()
    
    asyncio.run(run_analysis())


@cli.command()
@click.option('--all', 'show_all', is_flag=True, help='Show all recommendations')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high', 'critical']),
              help='Filter by priority')
@click.pass_context
def recommendations(ctx, show_all, priority):
    """View current AI recommendations"""
    
    async def show_recommendations():
        await ai_manager.initialize()
        
        try:
            recs = ai_manager.claude_engine.get_latest_recommendations()
            
            if not recs:
                click.echo("❌ No recommendations available. Run analysis first.")
                return
            
            # Filter by priority if specified
            if priority:
                recs = [r for r in recs if r.priority == priority]
            
            if not show_all:
                recs = recs[:5]  # Show top 5
            
            click.echo(f"\n📋 AI Recommendations ({len(recs)} found):")
            click.echo("=" * 60)
            
            for i, rec in enumerate(recs, 1):
                priority_emoji = {
                    'low': '🟢', 'medium': '🟡', 'high': '🟠', 'critical': '🔴'
                }.get(rec.priority, '⚪')
                
                click.echo(f"\n{i}. {priority_emoji} [{rec.priority.upper()}] {rec.title}")
                click.echo(f"   Category: {rec.category}")
                click.echo(f"   Description: {rec.description}")
                
                if rec.code_changes:
                    click.echo(f"   📝 Code Changes: {len(rec.code_changes)} files")
                
                if rec.config_changes:
                    click.echo(f"   ⚙️  Config Changes: {len(rec.config_changes)} parameters")
                
                if rec.expected_impact:
                    click.echo(f"   📈 Expected Impact: {rec.expected_impact}")
                
                if rec.risks:
                    click.echo(f"   ⚠️  Risks: {', '.join(rec.risks)}")
            
        finally:
            await ai_manager.cleanup()
    
    asyncio.run(show_recommendations())


@cli.command()
@click.option('--schedule', '-s', help='Set analysis schedule (cron format)')
@click.option('--start', is_flag=True, help='Start the scheduler')
@click.option('--stop', is_flag=True, help='Stop the scheduler')
@click.option('--status', is_flag=True, help='Show scheduler status')
@click.pass_context
def schedule(ctx, schedule, start, stop, status):
    """Manage AI analysis scheduler"""
    
    async def manage_scheduler():
        await ai_manager.initialize()
        
        try:
            if schedule:
                await ai_manager.scheduler.update_schedule(schedule)
                click.echo(f"✅ Analysis schedule updated: {schedule}")
            
            if start:
                await ai_manager.scheduler.start()
                click.echo("✅ AI scheduler started")
            
            if stop:
                await ai_manager.scheduler.stop()
                click.echo("✅ AI scheduler stopped")
            
            if status or not any([schedule, start, stop]):
                status_data = await ai_manager.scheduler.get_analysis_status()
                
                click.echo("\n📅 AI Scheduler Status:")
                click.echo("=" * 30)
                click.echo(f"Running: {'✅' if status_data['is_running'] else '❌'}")
                click.echo(f"Total Analyses: {status_data['total_analyses']}")
                click.echo(f"Success Rate: {status_data['success_rate']:.1f}%")
                click.echo(f"Queue Size: {status_data['queue_size']}")
                
                if status_data['last_analysis']:
                    last_analysis = datetime.fromisoformat(status_data['last_analysis'])
                    click.echo(f"Last Analysis: {last_analysis.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if status_data['next_scheduled']:
                    next_analysis = datetime.fromisoformat(status_data['next_scheduled'])
                    click.echo(f"Next Analysis: {next_analysis.strftime('%Y-%m-%d %H:%M:%S')}")
        
        finally:
            await ai_manager.cleanup()
    
    asyncio.run(manage_scheduler())


@cli.command()
@click.option('--apply', is_flag=True, help='Apply safe recommendations automatically')
@click.option('--rollback', help='Rollback specific update by ID')
@click.option('--list-updates', is_flag=True, help='List recent code updates')
@click.pass_context
def code(ctx, apply, rollback, list_updates):
    """Manage AI code updates"""
    
    async def manage_code():
        await ai_manager.initialize()
        
        try:
            if apply:
                recs = ai_manager.claude_engine.get_latest_recommendations()
                if recs:
                    results = await ai_manager.code_updater.process_recommendations(recs)
                    
                    click.echo("\n🔧 Code Update Results:")
                    click.echo("=" * 30)
                    click.echo(f"Applied: {results['applied']}")
                    click.echo(f"Skipped: {results['skipped']}")
                    click.echo(f"Failed: {results['failed']}")
                    
                    if results['applied'] > 0:
                        click.echo("\n✅ Successfully applied updates:")
                        for update in results['updates']:
                            if update['status'] == 'applied':
                                click.echo(f"  • {update['recommendation_title']}")
                else:
                    click.echo("❌ No recommendations available for code updates.")
            
            if rollback:
                success = await ai_manager.code_updater.manual_rollback(rollback)
                if success:
                    click.echo(f"✅ Successfully rolled back update: {rollback}")
                else:
                    click.echo(f"❌ Failed to rollback update: {rollback}")
            
            if list_updates or not any([apply, rollback]):
                updates = ai_manager.code_updater.get_update_history()
                rollbacks = ai_manager.code_updater.get_available_rollbacks()
                
                click.echo("\n📝 Recent Code Updates:")
                click.echo("=" * 30)
                
                if updates:
                    for update in updates[-5:]:  # Last 5 updates
                        status_emoji = {'applied': '✅', 'failed': '❌', 'skipped': '⏭️'}.get(update['status'], '❓')
                        click.echo(f"{status_emoji} {update['update_id']}: {update['recommendation_title']}")
                        click.echo(f"    Changes Applied: {update['changes_applied']}")
                        click.echo(f"    Backup Available: {'✅' if update['rollback_available'] else '❌'}")
                else:
                    click.echo("No code updates found.")
                
                click.echo(f"\n🔄 Available Rollbacks: {len(rollbacks)}")
        
        finally:
            await ai_manager.cleanup()
    
    asyncio.run(manage_code())


@cli.command()
@click.option('--export', help='Export dashboard data to file')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml']), 
              default='json', help='Export format')
@click.pass_context
def dashboard(ctx, export, output_format):
    """View AI dashboard data"""
    
    async def show_dashboard():
        await ai_manager.initialize()
        
        try:
            await ai_manager.dashboard.update_dashboard_data()
            dashboard_data = ai_manager.dashboard.get_dashboard_data()
            
            if export:
                if output_format == 'json':
                    with open(export, 'w') as f:
                        json.dump(dashboard_data, f, indent=2, default=str)
                elif output_format == 'yaml':
                    import yaml
                    with open(export, 'w') as f:
                        yaml.dump(dashboard_data, f, default_flow_style=False)
                
                click.echo(f"✅ Dashboard data exported to: {export}")
                return
            
            # Display dashboard summary
            click.echo("\n🎛️  AI Dashboard Summary:")
            click.echo("=" * 40)
            
            system_status = dashboard_data.get('system_status', {})
            analysis_stats = dashboard_data.get('analysis_stats', {})
            
            # System Status
            click.echo("\n📊 System Status:")
            scheduler = system_status.get('ai_scheduler', {})
            click.echo(f"  Scheduler: {'🟢 Running' if scheduler.get('running') else '🔴 Stopped'}")
            click.echo(f"  Queue Size: {scheduler.get('queue_size', 0)}")
            
            # Analysis Statistics
            click.echo("\n📈 Analysis Statistics:")
            click.echo(f"  Total Analyses: {analysis_stats.get('total_analyses', 0)}")
            click.echo(f"  Success Rate: {analysis_stats.get('success_rate', 0):.1f}%")
            click.echo(f"  Recommendations Implemented: {analysis_stats.get('recommendations_implemented', 0)}")
            
            # Recent Recommendations
            rec_overview = dashboard_data.get('recommendation_overview', {})
            if rec_overview.get('total', 0) > 0:
                click.echo("\n💡 Latest Recommendations:")
                for rec in rec_overview.get('latest_recommendations', [])[:3]:
                    priority_emoji = {
                        'low': '🟢', 'medium': '🟡', 'high': '🟠', 'critical': '🔴'
                    }.get(rec['priority'], '⚪')
                    click.echo(f"  {priority_emoji} {rec['title']} ({rec['category']})")
            
            # Alerts
            alerts = dashboard_data.get('alerts', [])
            if alerts:
                click.echo("\n🚨 Current Alerts:")
                for alert in alerts:
                    level_emoji = {'error': '🔴', 'warning': '🟡', 'info': '🔵'}.get(alert['level'], '⚪')
                    click.echo(f"  {level_emoji} {alert['message']}")
        
        finally:
            await ai_manager.cleanup()
    
    asyncio.run(show_dashboard())


@cli.command()
@click.option('--test-claude', is_flag=True, help='Test Claude API connection')
@click.option('--test-scheduler', is_flag=True, help='Test analysis scheduler')
@click.option('--test-all', is_flag=True, help='Test all AI components')
@click.pass_context
def test(ctx, test_claude, test_scheduler, test_all):
    """Test AI system components"""
    
    async def run_tests():
        await ai_manager.initialize()
        
        try:
            if test_claude or test_all:
                click.echo("🧠 Testing Claude API connection...")
                try:
                    result = await ai_manager.claude_engine.get_manual_analysis(
                        "Test connection. Please respond with 'Connection successful!'"
                    )
                    if "Connection successful" in result or len(result) > 10:
                        click.echo("✅ Claude API: Connection successful")
                    else:
                        click.echo("⚠️  Claude API: Unexpected response")
                except Exception as e:
                    click.echo(f"❌ Claude API: {str(e)}")
            
            if test_scheduler or test_all:
                click.echo("📅 Testing analysis scheduler...")
                try:
                    status = await ai_manager.scheduler.get_analysis_status()
                    click.echo(f"✅ Scheduler: {'Running' if status['is_running'] else 'Stopped'}")
                    click.echo(f"   Total analyses: {status['total_analyses']}")
                    click.echo(f"   Success rate: {status['success_rate']:.1f}%")
                except Exception as e:
                    click.echo(f"❌ Scheduler: {str(e)}")
            
            if test_all:
                click.echo("🔧 Testing code updater...")
                try:
                    history = ai_manager.code_updater.get_update_history()
                    rollbacks = ai_manager.code_updater.get_available_rollbacks()
                    click.echo(f"✅ Code Updater: {len(history)} updates, {len(rollbacks)} rollbacks available")
                except Exception as e:
                    click.echo(f"❌ Code Updater: {str(e)}")
                
                click.echo("🎛️  Testing dashboard...")
                try:
                    await ai_manager.dashboard.update_dashboard_data()
                    dashboard_data = ai_manager.dashboard.get_dashboard_data()
                    click.echo(f"✅ Dashboard: Data updated at {dashboard_data['timestamp']}")
                except Exception as e:
                    click.echo(f"❌ Dashboard: {str(e)}")
        
        finally:
            await ai_manager.cleanup()
    
    asyncio.run(run_tests())


@cli.command()
@click.option('--quick', is_flag=True, help='Quick setup with defaults')
@click.pass_context
def setup(ctx, quick):
    """Setup AI system configuration"""
    
    if quick:
        click.echo("🚀 Quick AI Setup:")
        click.echo("=" * 20)
        click.echo("1. Add your Claude API key to .env:")
        click.echo("   CLAUDE_API_KEY=your_api_key_here")
        click.echo("\n2. Enable AI in config/settings.yaml:")
        click.echo("   ai.enabled: true")
        click.echo("\n3. Start the engine:")
        click.echo("   python -m src.core.engine")
        click.echo("\n4. Test AI system:")
        click.echo("   python -m src.cli.ai_cli test --test-all")
        return
    
    # Interactive setup
    click.echo("🧠 SmartArb Engine AI Setup Wizard")
    click.echo("=" * 40)
    
    # Check current configuration
    try:
        config = ConfigManager()
        ai_config = config.get('ai', {})
        
        click.echo(f"\nCurrent AI status: {'✅ Enabled' if ai_config.get('enabled') else '❌ Disabled'}")
        
        if click.confirm("Do you want to enable AI analysis?"):
            ai_config['enabled'] = True
            click.echo("✅ AI analysis enabled")
        
        api_key = click.prompt("Enter your Claude API key", hide_input=True, default="")
        if api_key:
            click.echo("💾 Add this to your .env file:")
            click.echo(f"CLAUDE_API_KEY={api_key}")
        
        if click.confirm("Enable automatic code updates?"):
            click.echo("⚠️  Automatic code updates can modify your source code.")
            if click.confirm("Are you sure?"):
                ai_config['auto_apply_safe_changes'] = True
                click.echo("✅ Automatic code updates enabled")
        
        frequency = click.prompt(
            "Analysis frequency", 
            type=click.Choice(['hourly', 'daily', 'weekly']),
            default='daily'
        )
        ai_config['analysis_frequency'] = frequency
        
        click.echo("\n✅ AI system configured!")
        click.echo("Restart SmartArb Engine to apply changes.")
        
    except Exception as e:
        click.echo(f"❌ Setup failed: {str(e)}")


if __name__ == '__main__':
    cli()