#!/usr/bin/env python3
“””
AI System Setup Script for SmartArb Engine
Automated setup and configuration of Claude AI integration
“””

import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

# Add src to path

sys.path.insert(0, str(Path(**file**).parent.parent))

from src.utils.config import ConfigManager
from src.utils.logging import setup_logging
from src.ai.claude_integration import ClaudeAnalysisEngine

console = Console()
logger = structlog.get_logger(“ai_setup”)

class AISetupManager:
“”“AI system setup and configuration manager”””

```
def __init__(self, config_path: str = "config/settings.yaml"):
    self.config_path = config_path
    self.config_manager = ConfigManager(config_path)
    self.config = self.config_manager.get_config()
    
    # Setup logging
    setup_logging(self.config)
    
    self.claude_engine = None
    self.logger = structlog.get_logger("ai_setup")

async def run_setup(self, interactive: bool = True) -> bool:
    """Run complete AI setup process"""
    
    console.print(Panel.fit(
        "[bold cyan]SmartArb Engine AI Setup[/bold cyan]\n"
        "Setting up Claude AI integration for automated analysis and optimization",
        title="🧠 AI System Setup"
    ))
    
    if interactive:
        console.print("\n[yellow]This setup will configure Claude AI integration for:[/yellow]")
        console.print("• Automated performance analysis")
        console.print("• Strategy optimization recommendations")
        console.print("• Risk assessment and monitoring")
        console.print("• Code update suggestions")
        console.print("• Market analysis and insights")
        
        if not Confirm.ask("\nProceed with AI setup?"):
            console.print("[yellow]Setup cancelled.[/yellow]")
            return False
    
    # Step 1: API Key Configuration
    if not await self._setup_api_key(interactive):
        return False
    
    # Step 2: Test Connection
    if not await self._test_connection():
        return False
    
    # Step 3: Configure Analysis Settings
    if not await self._configure_analysis_settings(interactive):
        return False
    
    # Step 4: Setup Scheduling
    if not await self._setup_scheduling(interactive):
        return False
    
    # Step 5: Initialize AI Engine
    if not await self._initialize_ai_engine():
        return False
    
    # Step 6: Run Initial Analysis
    if interactive and Confirm.ask("Run initial AI analysis test?"):
        await self._run_initial_analysis()
    
    console.print(Panel.fit(
        "[bold green]✅ AI Setup Completed Successfully![/bold green]\n"
        "Your SmartArb Engine now has AI-powered analysis capabilities.",
        title="🎉 Setup Complete"
    ))
    
    self._print_next_steps()
    return True

async def _setup_api_key(self, interactive: bool) -> bool:
    """Setup Claude API key"""
    
    console.print("\n[bold blue]Step 1: API Key Configuration[/bold blue]")
    
    current_key = self.config.get('ai', {}).get('claude_api_key', '')
    
    if current_key and not any(x in current_key.lower() for x in ['your_', 'example', 'placeholder']):
        if interactive:
            console.print(f"[green]✅ API key already configured[/green]")
            if not Confirm.ask("Update existing API key?"):
                return True
        else:
            console.print("[green]✅ API key already configured[/green]")
            return True
    
    if interactive:
        console.print("\n[yellow]You need a Claude API key from Anthropic:[/yellow]")
        console.print("1. Visit: https://console.anthropic.com/")
        console.print("2. Create an account or sign in")
        console.print("3. Go to API Keys section")
        console.print("4. Create a new API key")
        console.print("5. Copy the key (starts with 'sk-ant-api...')")
        
        api_key = Prompt.ask(
            "\nEnter your Claude API key",
            password=True,
            default="" if not current_key else None
        )
    else:
        # Non-interactive mode - check environment
        api_key = os.environ.get('CLAUDE_API_KEY', '')
        if not api_key:
            console.print("[red]❌ CLAUDE_API_KEY environment variable not set[/red]")
            return False
    
    if not api_key:
        console.print("[red]❌ API key is required for AI functionality[/red]")
        return False
    
    if not api_key.startswith('sk-ant-api'):
        console.print("[yellow]⚠️  API key format seems incorrect (should start with 'sk-ant-api')[/yellow]")
        if interactive and not Confirm.ask("Continue anyway?"):
            return False
    
    # Update configuration
    if 'ai' not in self.config:
        self.config['ai'] = {}
    
    self.config['ai']['claude_api_key'] = api_key
    self.config['ai']['enabled'] = True
    
    console.print("[green]✅ API key configured successfully[/green]")
    return True

async def _test_connection(self) -> bool:
    """Test Claude API connection"""
    
    console.print("\n[bold blue]Step 2: Testing API Connection[/bold blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Testing Claude API connection...", total=None)
        
        try:
            # Initialize Claude engine with current config
            self.claude_engine = ClaudeAnalysisEngine(self.config)
            
            # Test connection
            test_result = await self.claude_engine.test_connection()
            
            progress.update(task, completed=True)
            
            if test_result['success']:
                console.print(f"[green]✅ Connection successful![/green]")
                console.print(f"[dim]Model: {test_result.get('model', 'Unknown')}[/dim]")
                return True
            else:
                console.print(f"[red]❌ Connection failed: {test_result.get('error', 'Unknown error')}[/red]")
                return False
                
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]❌ Connection test failed: {str(e)}[/red]")
            return False

async def _configure_analysis_settings(self, interactive: bool) -> bool:
    """Configure AI analysis settings"""
    
    console.print("\n[bold blue]Step 3: Analysis Configuration[/bold blue]")
    
    ai_config = self.config.get('ai', {})
    
    # Default settings
    defaults = {
        'model': 'claude-3-sonnet-20240229',
        'max_tokens': 4000,
        'temperature': 0.3,
        'rate_limit_per_minute': 50,
        'auto_optimization': False
    }
    
    if interactive:
        console.print("\n[cyan]AI Model Configuration:[/cyan]")
        
        # Model selection
        models = [
            'claude-3-sonnet-20240229',
            'claude-3-opus-20240229',
            'claude-3-haiku-20240307'
        ]
        
        current_model = ai_config.get('model', defaults['model'])
        console.print(f"Available models: {', '.join(models)}")
        
        model = Prompt.ask(
            "Select AI model",
            choices=models,
            default=current_model
        )
        
        # Temperature setting
        temperature = float(Prompt.ask(
            "Temperature (0.0-1.0, lower = more focused)",
            default=str(ai_config.get('temperature', defaults['temperature']))
        ))
        
        # Rate limiting
        rate_limit = int(Prompt.ask(
            "Rate limit (requests per minute)",
            default=str(ai_config.get('rate_limit_per_minute', defaults['rate_limit_per_minute']))
        ))
        
        # Auto-optimization
        auto_opt = Confirm.ask(
            "Enable automatic optimization recommendations?",
            default=ai_config.get('auto_optimization', defaults['auto_optimization'])
        )
        
        # Update configuration
        ai_config.update({
            'model': model,
            'max_tokens': ai_config.get('max_tokens', defaults['max_tokens']),
            'temperature': temperature,
            'rate_limit_per_minute': rate_limit,
            'auto_optimization': auto_opt
        })
    
    else:
        # Non-interactive mode - use defaults
        for key, value in defaults.items():
            if key not in ai_config:
                ai_config[key] = value
    
    self.config['ai'] = ai_config
    console.print("[green]✅ Analysis settings configured[/green]")
    return True

async def _setup_scheduling(self, interactive: bool) -> bool:
    """Setup analysis scheduling"""
    
    console.print("\n[bold blue]Step 4: Analysis Scheduling[/bold blue]")
    
    ai_config = self.config.get('ai', {})
    
    # Default schedule
    default_schedule = {
        'performance_review': '0 8 * * *',      # Daily at 8 AM
        'strategy_optimization': '0 12 * * 1',  # Weekly on Monday at noon
        'risk_assessment': '0 */4 * * *'        # Every 4 hours
    }
    
    if interactive:
        console.print("\n[cyan]Analysis Schedule (cron format):[/cyan]")
        
        schedule = {}
        
        schedule['performance_review'] = Prompt.ask(
            "Performance review schedule",
            default=ai_config.get('analysis_schedule', {}).get('performance_review', default_schedule['performance_review'])
        )
        
        schedule['strategy_optimization'] = Prompt.ask(
            "Strategy optimization schedule", 
            default=ai_config.get('analysis_schedule', {}).get('strategy_optimization', default_schedule['strategy_optimization'])
        )
        
        schedule['risk_assessment'] = Prompt.ask(
            "Risk assessment schedule",
            default=ai_config.get('analysis_schedule', {}).get('risk_assessment', default_schedule['risk_assessment'])
        )
        
        ai_config['analysis_schedule'] = schedule
    
    else:
        # Non-interactive mode
        if 'analysis_schedule' not in ai_config:
            ai_config['analysis_schedule'] = default_schedule
    
    self.config['ai'] = ai_config
    console.print("[green]✅ Analysis scheduling configured[/green]")
    return True

async def _initialize_ai_engine(self) -> bool:
    """Initialize AI engine with final configuration"""
    
    console.print("\n[bold blue]Step 5: Initializing AI Engine[/bold blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Initializing AI engine...", total=None)
        
        try:
            # Reinitialize with updated config
            self.claude_engine = ClaudeAnalysisEngine(self.config)
            
            # Save configuration
            success = self.config_manager.save_config()
            
            progress.update(task, completed=True)
            
            if success:
                console.print("[green]✅ AI engine initialized and configuration saved[/green]")
                return True
            else:
                console.print("[yellow]⚠️  AI engine initialized but config save failed[/yellow]")
                return True
                
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]❌ AI engine initialization failed: {str(e)}[/red]")
            return False

async def _run_initial_analysis(self) -> bool:
    """Run initial AI analysis test"""
    
    console.print("\n[bold blue]Step 6: Initial Analysis Test[/bold blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running initial analysis...", total=None)
        
        try:
            # Create test performance data
            test_data = {
                'total_trades': 0,
                'successful_trades': 0,
                'total_profit': 0.0,
                'average_profit_per_trade': 0.0,
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'test_mode': True
            }
            
            # Run analysis
            result = await self.claude_engine.analyze_performance(
                test_data, 
                focus="initial_setup_test"
            )
            
            progress.update(task, completed=True)
            
            console.print("[green]✅ Initial analysis completed successfully![/green]")
            
            # Show analysis summary
            console.print(f"\n[dim]Analysis Summary:[/dim]")
            console.print(f"[dim]• {result.summary}[/dim]")
            console.print(f"[dim]• Confidence: {result.confidence_score:.1%}[/dim]")
            console.print(f"[dim]• Processing time: {result.processing_time:.2f}s[/dim]")
            console.print(f"[dim]• Recommendations: {len(result.recommendations)}[/dim]")
            
            return True
            
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[yellow]⚠️  Initial analysis test failed: {str(e)}[/yellow]")
            console.print("[dim]This is normal for a fresh setup with no trading data[/dim]")
            return True

def _print_next_steps(self):
    """Print next steps after setup"""
    
    console.print("\n[bold green]🎯 Next Steps:[/bold green]")
    console.print("\n1. Start SmartArb Engine:")
    console.print("   [cyan]python -m src.core.engine[/cyan]")
    console.print("\n2. Test AI system:")
    console.print("   [cyan]python -m src.cli.main ai-test[/cyan]")
    console.print("\n3. Run manual analysis:")
    console.print("   [cyan]python -m src.cli.main ai-analyze[/cyan]")
    console.print("\n4. Monitor via CLI:")
    console.print("   [cyan]python -m src.cli.main status[/cyan]")
    console.print("\n5. View logs:")
    console.print("   [cyan]python -m src.cli.main logs --type ai[/cyan]")
    
    console.print(f"\n[bold cyan]📚 Configuration saved to: {self.config_path}[/bold cyan]")
```

async def quick_setup() -> bool:
“”“Quick non-interactive setup”””

```
console.print("[blue]🚀 Quick AI Setup (Non-interactive)[/blue]")

# Check for environment variables
required_env_vars = ['CLAUDE_API_KEY']
missing_vars = []

for var in required_env_vars:
    if not os.environ.get(var):
        missing_vars.append(var)

if missing_vars:
    console.print(f"[red]❌ Missing environment variables: {', '.join(missing_vars)}[/red]")
    console.print("[yellow]Set environment variables and try again[/yellow]")
    return False

setup_manager = AISetupManager()
return await setup_manager.run_setup(interactive=False)
```

async def interactive_setup() -> bool:
“”“Interactive setup with user prompts”””

```
console.print("[blue]🎯 Interactive AI Setup[/blue]")

setup_manager = AISetupManager()
return await setup_manager.run_setup(interactive=True)
```

async def test_ai_system() -> bool:
“”“Test existing AI system configuration”””

```
console.print("[blue]🔍 Testing AI System[/blue]")

try:
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    ai_config = config.get('ai', {})
    
    if not ai_config.get('enabled', False):
        console.print("[yellow]⚠️  AI system is disabled[/yellow]")
        return False
    
    api_key = ai_config.get('claude_api_key', '')
    if not api_key:
        console.print("[red]❌ No API key configured[/red]")
        return False
    
    # Test connection
    claude_engine = ClaudeAnalysisEngine(config)
    test_result = await claude_engine.test_connection()
    
    if test_result['success']:
        console.print("[green]✅ AI system is working correctly![/green]")
        
        # Show configuration
        config_table = Table(title="AI Configuration")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="white")
        
        config_table.add_row("Model", ai_config.get('model', 'N/A'))
        config_table.add_row("Temperature", str(ai_config.get('temperature', 'N/A')))
        config_table.add_row("Rate Limit", f"{ai_config.get('rate_limit_per_minute', 'N/A')}/min")
        config_table.add_row("Auto Optimization", "✅" if ai_config.get('auto_optimization') else "❌")
        
        console.print(config_table)
        return True
    
    else:
        console.print(f"[red]❌ AI system test failed: {test_result.get('error')}[/red]")
        return False
        
except Exception as e:
    console.print(f"[red]❌ AI system test error: {str(e)}[/red]")
    return False
```

async def main():
“”“Main setup function”””
import argparse

```
parser = argparse.ArgumentParser(description='Setup SmartArb Engine AI system')
parser.add_argument('--non-interactive', action='store_true',
                   help='Run setup without user prompts')
parser.add_argument('--quick', action='store_true',
                   help='Quick setup with defaults')
parser.add_argument('--test', action='store_true',
                   help='Test existing AI configuration')

args = parser.parse_args()

try:
    if args.test:
        success = await test_ai_system()
    elif args.quick or args.non_interactive:
        success = await quick_setup()
    else:
        success = await interactive_setup()
    
    return 0 if success else 1
    
except KeyboardInterrupt:
    console.print("\n[yellow]⚠️  Setup cancelled by user[/yellow]")
    return 1
except Exception as e:
    console.print(f"\n[red]❌ Setup failed: {str(e)}[/red]")
    return 1
```

if **name** == “**main**”:
exit(asyncio.run(main()))