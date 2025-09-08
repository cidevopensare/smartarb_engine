#!/usr/bin/env python3
“””
SmartArb Engine CLI - Command Line Interface
Complete CLI for controlling and monitoring the SmartArb trading bot
“””

import click
import asyncio
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.tree import Tree
from rich import box
import structlog

# Add src to path for imports

sys.path.insert(0, str(Path(**file**).parent.parent.parent))

from src.core.engine import SmartArbEngine, EngineStatus
from src.utils.config import ConfigManager
from src.utils.logging import setup_logging

console = Console()
logger = structlog.get_logger(“smartarb.cli”)

class SmartArbCLI:
“”“Main CLI controller”””

```
def __init__(self):
    self.engine = None
    self.config_manager = None
    self.config = {}
    self.engine_task = None
    
async def initialize(self, config_path: str = "config/settings.yaml"):
    """Initialize CLI with configuration"""
    try:
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        
        # Setup logging
        setup_logging(self.config)
        
        # Initialize engine
        self.engine = SmartArbEngine(config_path)
        
        console.print("[green]✅ CLI initialized successfully[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ CLI initialization failed: {str(e)}[/red]")
        return False
```

@click.group()
@click.option(’–config’, ‘-c’, default=‘config/settings.yaml’,
help=‘Configuration file path’)
@click.pass_context
def cli(ctx, config):
“”“SmartArb Engine - Professional Cryptocurrency Arbitrage Bot”””
ctx.ensure_object(dict)
ctx.obj[‘config_path’] = config

```
# ASCII Art Header
header = """
```

╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║  ███████╗███╗   ███╗ █████╗ ██████╗ ████████╗ █████╗ ██████╗  ║
║  ██╔════╝████╗ ████║██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗ ║
║  ███████╗██╔████╔██║███████║██████╔╝   ██║   ███████║██████╔╝ ║
║  ╚════██║██║╚██╔╝██║██╔══██║██╔══██╗   ██║   ██╔══██║██╔══██╗ ║
║  ███████║██║ ╚═╝ ██║██║  ██║██║  ██║   ██║   ██║  ██║██║  ██║ ║
║  ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ║
║                                                              ║
║              Professional Arbitrage Trading Engine          ║
║                    Raspberry Pi Optimized                   ║
╚══════════════════════════════════════════════════════════════╝
“””
console.print(header, style=“cyan”)

@cli.command()
@click.pass_context
async def start(ctx):
“”“Start the SmartArb Engine”””
config_path = ctx.obj[‘config_path’]

```
cli_instance = SmartArbCLI()

if not await cli_instance.initialize(config_path):
    console.print("[red]❌ Failed to initialize CLI[/red]")
    return

console.print("[blue]🚀 Starting SmartArb Engine...[/blue]")

try:
    # Start the engine
    await cli_instance.engine.start()
    
except KeyboardInterrupt:
    console.print("\n[yellow]⚠️  Shutdown signal received[/yellow]")
    
    # Graceful shutdown
    console.print("[blue]🛑 Stopping SmartArb Engine...[/blue]")
    await cli_instance.engine.stop()
    
    console.print("[green]✅ Engine stopped successfully[/green]")

except Exception as e:
    console.print(f"[red]❌ Engine error: {str(e)}[/red]")
```

@cli.command()
@click.pass_context
def status(ctx):
“”“Show SmartArb Engine status”””
config_path = ctx.obj[‘config_path’]

```
# Create a simple status display
console.print("[blue]📊 SmartArb Engine Status[/blue]")

# Check configuration
try:
    config_manager = ConfigManager(config_path)
    config = config_manager.get_config()
    
    # Create status table
    status_table = Table(title="System Status", box=box.ROUNDED)
    status_table.add_column("Component", style="cyan")
    status_table.add_column("Status", style="green")
    status_table.add_column("Details", style="white")
    
    # Configuration status
    status_table.add_row(
        "Configuration",
        "✅ Loaded",
        f"From: {config_path}"
    )
    
    # Exchange status
    exchanges = config.get('exchanges', {})
    enabled_exchanges = [name for name, cfg in exchanges.items() if cfg.get('enabled')]
    
    status_table.add_row(
        "Exchanges",
        f"✅ {len(enabled_exchanges)} enabled" if enabled_exchanges else "⚠️  None enabled",
        f"Available: {', '.join(enabled_exchanges) if enabled_exchanges else 'None'}"
    )
    
    # Strategy status
    strategies = config.get('strategies', {})
    enabled_strategies = [name for name, cfg in strategies.items() if cfg.get('enabled')]
    
    status_table.add_row(
        "Strategies",
        f"✅ {len(enabled_strategies)} enabled" if enabled_strategies else "⚠️  None enabled",
        f"Active: {', '.join(enabled_strategies) if enabled_strategies else 'None'}"
    )
    
    # AI status
    ai_config = config.get('ai', {})
    ai_enabled = ai_config.get('enabled', False)
    ai_key = ai_config.get('claude_api_key', '')
    
    status_table.add_row(
        "AI System",
        "✅ Enabled" if ai_enabled and ai_key else "⚠️  Disabled",
        f"Model: {ai_config.get('model', 'N/A')}" if ai_enabled else "Not configured"
    )
    
    console.print(status_table)
    
except Exception as e:
    console.print(f"[red]❌ Status check failed: {str(e)}[/red]")
```

@cli.command()
@click.pass_context
def config_validate(ctx):
“”“Validate configuration”””
config_path = ctx.obj[‘config_path’]

```
console.print("[blue]🔍 Validating configuration...[/blue]")

try:
    config_manager = ConfigManager(config_path)
    validation_result = config_manager.validate_config()
    
    if validation_result.valid:
        console.print("[green]✅ Configuration is valid![/green]")
        
        if validation_result.warnings:
            console.print("\n[yellow]⚠️  Warnings:[/yellow]")
            for warning in validation_result.warnings:
                console.print(f"  • {warning}")
    else:
        console.print("[red]❌ Configuration validation failed![/red]")
        
        if validation_result.errors:
            console.print("\n[red]🚫 Errors:[/red]")
            for error in validation_result.errors:
                console.print(f"  • {error}")
        
        if validation_result.warnings:
            console.print("\n[yellow]⚠️  Warnings:[/yellow]")
            for warning in validation_result.warnings:
                console.print(f"  • {warning}")

except Exception as e:
    console.print(f"[red]❌ Validation failed: {str(e)}[/red]")
```

@cli.command()
@click.pass_context
def exchanges(ctx):
“”“Show exchange information”””
config_path = ctx.obj[‘config_path’]

```
console.print("[blue]🔗 Exchange Information[/blue]")

try:
    config_manager = ConfigManager(config_path)
    config = config_manager.get_config()
    
    exchanges = config.get('exchanges', {})
    
    if not exchanges:
        console.print("[yellow]⚠️  No exchanges configured[/yellow]")
        return
    
    # Create exchanges table
    exchanges_table = Table(title="Exchanges", box=box.ROUNDED)
    exchanges_table.add_column("Exchange", style="cyan")
    exchanges_table.add_column("Status", style="green")
    exchanges_table.add_column("API Key", style="white")
    exchanges_table.add_column("Sandbox", style="white")
    exchanges_table.add_column("Rate Limit", style="white")
    
    for exchange_name, exchange_config in exchanges.items():
        enabled = exchange_config.get('enabled', False)
        status = "✅ Enabled" if enabled else "⚪ Disabled"
        
        api_key = exchange_config.get('api_key', '')
        api_key_status = "✅ Set" if api_key and not any(x in api_key.lower() for x in ['your_', 'example']) else "❌ Missing"
        
        sandbox = "✅ Yes" if exchange_config.get('sandbox', False) else "⚪ No"
        rate_limit = str(exchange_config.get('rate_limit', 'N/A'))
        
        exchanges_table.add_row(
            exchange_name.upper(),
            status,
            api_key_status,
            sandbox,
            rate_limit
        )
    
    console.print(exchanges_table)
    
except Exception as e:
    console.print(f"[red]❌ Failed to load exchange info: {str(e)}[/red]")
```

@cli.command()
@click.pass_context
def strategies(ctx):
“”“Show strategy information”””
config_path = ctx.obj[‘config_path’]

```
console.print("[blue]🎯 Strategy Information[/blue]")

try:
    config_manager = ConfigManager(config_path)
    config = config_manager.get_config()
    
    strategies = config.get('strategies', {})
    
    if not strategies:
        console.print("[yellow]⚠️  No strategies configured[/yellow]")
        return
    
    # Create strategies table
    strategies_table = Table(title="Strategies", box=box.ROUNDED)
    strategies_table.add_column("Strategy", style="cyan")
    strategies_table.add_column("Status", style="green")
    strategies_table.add_column("Priority", style="white")
    strategies_table.add_column("Min Spread", style="white")
    strategies_table.add_column("Max Position", style="white")
    
    for strategy_name, strategy_config in strategies.items():
        enabled = strategy_config.get('enabled', False)
        status = "✅ Enabled" if enabled else "⚪ Disabled"
        
        priority = str(strategy_config.get('priority', 'N/A'))
        min_spread = f"{strategy_config.get('min_spread_percent', 'N/A')}%"
        max_position = f"${strategy_config.get('max_position_size', 'N/A')}"
        
        strategies_table.add_row(
            strategy_name.replace('_', ' ').title(),
            status,
            priority,
            min_spread,
            max_position
        )
    
    console.print(strategies_table)
    
except Exception as e:
    console.print(f"[red]❌ Failed to load strategy info: {str(e)}[/red]")
```

@cli.command()
@click.option(’–limit’, ‘-l’, default=20, help=‘Number of log lines to show’)
@click.option(’–follow’, ‘-f’, is_flag=True, help=‘Follow log output’)
@click.option(’–type’, ‘-t’, default=‘main’,
type=click.Choice([‘main’, ‘trading’, ‘error’, ‘risk’, ‘ai’]),
help=‘Log file type’)
def logs(limit, follow, type):
“”“Show SmartArb Engine logs”””

```
log_files = {
    'main': 'logs/main.log',
    'trading': 'logs/trading.log', 
    'error': 'logs/error.log',
    'risk': 'logs/risk.log',
    'ai': 'logs/ai.log'
}

log_file = Path(log_files.get(type, 'logs/main.log'))

if not log_file.exists():
    console.print(f"[yellow]⚠️  Log file not found: {log_file}[/yellow]")
    return

console.print(f"[blue]📋 {type.title()} Logs (last {limit} lines)[/blue]")

try:
    # Read last N lines
    with open(log_file, 'r') as f:
        lines = f.readlines()
        recent_lines = lines[-limit:] if len(lines) > limit else lines
    
    for line in recent_lines:
        line = line.strip()
        if line:
            # Color code log levels
            if 'ERROR' in line:
                console.print(f"[red]{line}[/red]")
            elif 'WARNING' in line:
                console.print(f"[yellow]{line}[/yellow]")
            elif 'INFO' in line:
                console.print(f"[green]{line}[/green]")
            else:
                console.print(line)
    
    if follow:
        console.print("\n[blue]📡 Following logs... (Press Ctrl+C to stop)[/blue]")
        
        # Simple tail -f implementation
        import subprocess
        try:
            subprocess.run(['tail', '-f', str(log_file)])
        except KeyboardInterrupt:
            console.print("\n[yellow]📋 Log following stopped[/yellow]")

except Exception as e:
    console.print(f"[red]❌ Failed to read logs: {str(e)}[/red]")
```

@cli.command()
@click.pass_context
def test_connections(ctx):
“”“Test exchange connections”””
config_path = ctx.obj[‘config_path’]

```
console.print("[blue]🔍 Testing exchange connections...[/blue]")

cli_instance = SmartArbCLI()

async def run_connection_tests():
    if not await cli_instance.initialize(config_path):
        console.print("[red]❌ Failed to initialize CLI[/red]")
        return
    
    # Initialize engine
    success = await cli_instance.engine.initialize()
    
    if not success:
        console.print("[red]❌ Failed to initialize engine[/red]")
        return
    
    # Test each exchange
    for exchange_name, exchange in cli_instance.engine.exchanges.items():
        console.print(f"\n[cyan]Testing {exchange_name.upper()}...[/cyan]")
        
        try:
            health_check = await exchange.health_check()
            
            if health_check['status'] == 'ok':
                console.print(f"[green]✅ {exchange_name.upper()}: Connected successfully[/green]")
            else:
                console.print(f"[red]❌ {exchange_name.upper()}: {health_check.get('error', 'Connection failed')}[/red]")
                
        except Exception as e:
            console.print(f"[red]❌ {exchange_name.upper()}: {str(e)}[/red]")
    
    # Cleanup
    await cli_instance.engine.shutdown()

try:
    asyncio.run(run_connection_tests())
except Exception as e:
    console.print(f"[red]❌ Connection test failed: {str(e)}[/red]")
```

@cli.command()
@click.option(’–output’, ‘-o’, type=click.Choice([‘table’, ‘json’]),
default=‘table’, help=‘Output format’)
@click.pass_context  
def info(ctx, output):
“”“Show system information”””
config_path = ctx.obj[‘config_path’]

```
try:
    config_manager = ConfigManager(config_path)
    summary = config_manager.get_config_summary()
    
    if output == 'json':
        console.print(json.dumps(summary, indent=2))
        return
    
    # Table format
    info_table = Table(title="System Information", box=box.ROUNDED)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="white")
    
    info_table.add_row("Config Path", str(summary['config_path']))
    info_table.add_row("Config Loaded", "✅ Yes" if summary['config_loaded'] else "❌ No")
    info_table.add_row("Enabled Exchanges", ", ".join(summary['enabled_exchanges']) or "None")
    info_table.add_row("Enabled Strategies", ", ".join(summary['enabled_strategies']) or "None")
    info_table.add_row("AI Enabled", "✅ Yes" if summary['ai_enabled'] else "⚪ No")
    info_table.add_row("Debug Mode", "✅ Yes" if summary['debug_mode'] else "⚪ No")
    info_table.add_row("Environment", summary['environment'])
    info_table.add_row("Last Loaded", summary['last_loaded'])
    
    console.print(info_table)
    
except Exception as e:
    console.print(f"[red]❌ Failed to get system info: {str(e)}[/red]")
```

@cli.command()
def version():
“”“Show version information”””
try:
# Import version info
from src import **version**, PROJECT_NAME, get_package_info

```
    info = get_package_info()
    
    version_table = Table(title="Version Information", box=box.ROUNDED)
    version_table.add_column("Property", style="cyan")
    version_table.add_column("Value", style="white")
    
    version_table.add_row("Project", info['name'])
    version_table.add_row("Version", info['version'])
    version_table.add_row("Author", info['author'])
    version_table.add_row("License", info['license'])
    version_table.add_row("Python Required", info['python_requires'])
    
    console.print(version_table)
    
    # Show supported exchanges
    console.print("\n[blue]📊 Supported Exchanges:[/blue]")
    exchanges_info = info['supported_exchanges']
    
    exchanges_table = Table(box=box.SIMPLE)
    exchanges_table.add_column("Exchange", style="cyan")
    exchanges_table.add_column("Spot", style="green")
    exchanges_table.add_column("Futures", style="yellow")
    exchanges_table.add_column("WebSocket", style="blue")
    
    for exchange_name, exchange_info in exchanges_info.items():
        exchanges_table.add_row(
            exchange_info['name'],
            "✅" if exchange_info['spot'] else "❌",
            "✅" if exchange_info['futures'] else "❌", 
            "✅" if exchange_info['websocket'] else "❌"
        )
    
    console.print(exchanges_table)
    
except Exception as e:
    console.print(f"[red]❌ Failed to get version info: {str(e)}[/red]")
```

# Async wrapper for click commands

def async_command(f):
“”“Decorator to make click commands async”””
def wrapper(*args, **kwargs):
return asyncio.run(f(*args, **kwargs))
return wrapper

# Apply async wrapper to async commands

start = async_command(start)

def main():
“”“Main CLI entry point”””
try:
cli()
except KeyboardInterrupt:
console.print(”\n[yellow]👋 Goodbye![/yellow]”)
except Exception as e:
console.print(f”[red]❌ CLI error: {str(e)}[/red]”)
sys.exit(1)

if **name** == “**main**”:
main()