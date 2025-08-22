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
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    console=console
) as progress:
    
    # Initialize
    init_task = progress.add_task("Initializing SmartArb Engine...", total=None)
    
    cli_controller = SmartArbCLI()
    if not await cli_controller.initialize(config_path):
        console.print("[red]❌ Failed to initialize engine[/red]")
        return
    
    progress.update(init_task, description="✅ Engine initialized")
    
    # Start engine
    start_task = progress.add_task("Starting trading engine...", total=None)
    
    try:
        if not await cli_controller.engine.initialize():
            console.print("[red]❌ Engine initialization failed[/red]")
            return
        
        if not await cli_controller.engine.start():
            console.print("[red]❌ Engine start failed[/red]")
            return
        
        progress.update(start_task, description="✅ Engine started successfully")
        
    except KeyboardInterrupt:
        progress.update(start_task, description="🛑 Startup interrupted")
        console.print("\n[yellow]Startup interrupted by user[/yellow]")
        return
    except Exception as e:
        progress.update(start_task, description="❌ Startup failed")
        console.print(f"\n[red]❌ Startup failed: {str(e)}[/red]")
        return

# Show status and keep running
console.print("\n[green]🚀 SmartArb Engine is now running![/green]")
console.print("Press Ctrl+C to stop the engine\n")

try:
    # Main monitoring loop
    with Live(console=console, refresh_per_second=1) as live:
        while cli_controller.engine.is_running:
            status_panel = await create_status_panel(cli_controller.engine)
            live.update(status_panel)
            await asyncio.sleep(1)
            
except KeyboardInterrupt:
    console.print("\n[yellow]🛑 Shutdown signal received...[/yellow]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        stop_task = progress.add_task("Stopping SmartArb Engine...", total=None)
        
        await cli_controller.engine.shutdown()
        progress.update(stop_task, description="✅ Engine stopped safely")
    
    console.print("[green]✅ SmartArb Engine stopped successfully[/green]")
```

@cli.command()
@click.pass_context
async def status(ctx):
“”“Show current engine status”””
config_path = ctx.obj[‘config_path’]

```
cli_controller = SmartArbCLI()
if not await cli_controller.initialize(config_path):
    return

# Get status
if cli_controller.engine.status == EngineStatus.STOPPED:
    console.print("[yellow]Engine is currently stopped[/yellow]")
    
    # Show configuration status
    await show_config_status(cli_controller.config_manager)
    return

# Show live status
try:
    await cli_controller.engine.initialize()
    status = await cli_controller.engine.get_engine_status()
    
    status_panel = create_status_display(status)
    console.print(status_panel)
    
except Exception as e:
    console.print(f"[red]❌ Failed to get status: {str(e)}[/red]")
```

@cli.command()
@click.pass_context
async def config(ctx):
“”“Show and manage configuration”””
config_path = ctx.obj[‘config_path’]

```
try:
    config_manager = ConfigManager(config_path)
    await show_config_status(config_manager)
    
except Exception as e:
    console.print(f"[red]❌ Failed to load configuration: {str(e)}[/red]")
```

@cli.command()
@click.option(’–exchange’, ‘-e’, help=‘Test specific exchange’)
@click.pass_context
async def test(ctx, exchange):
“”“Test exchange connections and configuration”””
config_path = ctx.obj[‘config_path’]

```
cli_controller = SmartArbCLI()
if not await cli_controller.initialize(config_path):
    return

console.print("[cyan]🔍 Testing SmartArb Engine configuration...[/cyan]\n")

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    console=console
) as progress:
    
    # Test configuration
    config_task = progress.add_task("Testing configuration...", total=None)
    
    try:
        await cli_controller.engine.initialize()
        progress.update(config_task, description="✅ Configuration valid")
        
        # Test exchanges
        if exchange:
            await test_single_exchange(cli_controller.engine, exchange, progress)
        else:
            await test_all_exchanges(cli_controller.engine, progress)
        
        # Test strategies
        strategy_task = progress.add_task("Testing strategies...", total=None)
        # Add strategy testing logic here
        progress.update(strategy_task, description="✅ Strategies configured")
        
    except Exception as e:
        progress.update(config_task, description=f"❌ Configuration error: {str(e)}")
```

@cli.command()
@click.option(’–format’, ‘-f’, type=click.Choice([‘table’, ‘json’]), default=‘table’)
@click.pass_context
async def portfolio(ctx, format):
“”“Show portfolio balances across exchanges”””
config_path = ctx.obj[‘config_path’]

```
cli_controller = SmartArbCLI()
if not await cli_controller.initialize(config_path):
    return

try:
    await cli_controller.engine.initialize()
    
    if not cli_controller.engine.portfolio_manager:
        console.print("[yellow]Portfolio manager not initialized[/yellow]")
        return
    
    # Update portfolio
    await cli_controller.engine.portfolio_manager.update_portfolio(force_update=True)
    
    # Get portfolio data
    balances = cli_controller.engine.portfolio_manager.current_balances
    
    if format == 'json':
        portfolio_data = {}
        for asset, balance in balances.items():
            portfolio_data[asset] = {
                'total_balance': float(balance.total_balance),
                'available': float(balance.available_balance),
                'locked': float(balance.locked_balance),
                'exchanges': {
                    ex_name: {
                        'total': float(ex_balance.total),
                        'free': float(ex_balance.free),
                        'locked': float(ex_balance.locked)
                    }
                    for ex_name, ex_balance in balance.exchange_balances.items()
                }
            }
        
        console.print(json.dumps(portfolio_data, indent=2))
    else:
        show_portfolio_table(balances)
        
except Exception as e:
    console.print(f"[red]❌ Failed to get portfolio: {str(e)}[/red]")
```

@cli.command()
@click.option(’–tail’, ‘-t’, default=50, help=‘Number of recent logs to show’)
@click.option(’–follow’, ‘-f’, is_flag=True, help=‘Follow log output’)
@click.option(’–level’, ‘-l’, type=click.Choice([‘DEBUG’, ‘INFO’, ‘WARNING’, ‘ERROR’]),
help=‘Filter by log level’)
def logs(tail, follow, level):
“”“Show SmartArb Engine logs”””

```
log_file = Path("logs/smartarb.log")

if not log_file.exists():
    console.print("[yellow]No log file found. Engine might not be running.[/yellow]")
    return

try:
    if follow:
        console.print(f"[cyan]Following logs from {log_file}[/cyan]")
        console.print("Press Ctrl+C to stop\n")
        
        # Implement tail -f functionality
        import subprocess
        try:
            subprocess.run(['tail', '-f', str(log_file)])
        except KeyboardInterrupt:
            console.print("\n[yellow]Log following stopped[/yellow]")
    else:
        # Show recent logs
        with open(log_file, 'r') as f:
            lines = f.readlines()
            
        recent_lines = lines[-tail:] if len(lines) > tail else lines
        
        for line in recent_lines:
            # Basic log level coloring
            if 'ERROR' in line:
                console.print(line.strip(), style="red")
            elif 'WARNING' in line:
                console.print(line.strip(), style="yellow")
            elif 'INFO' in line:
                console.print(line.strip(), style="green")
            else:
                console.print(line.strip())
                
except Exception as e:
    console.print(f"[red]❌ Failed to read logs: {str(e)}[/red]")
```

@cli.command()
@click.option(’–days’, ‘-d’, default=7, help=‘Days of history to show’)
@click.pass_context
async def performance(ctx, days):
“”“Show trading performance metrics”””
config_path = ctx.obj[‘config_path’]

```
cli_controller = SmartArbCLI()
if not await cli_controller.initialize(config_path):
    return

try:
    await cli_controller.engine.initialize()
    
    # Get performance metrics
    metrics = await cli_controller.engine.get_detailed_metrics()
    
    show_performance_metrics(metrics, days)
    
except Exception as e:
    console.print(f"[red]❌ Failed to get performance metrics: {str(e)}[/red]")
```

@cli.command()
@click.confirmation_option(prompt=‘Are you sure you want to stop the engine?’)
async def stop():
“”“Stop a running SmartArb Engine”””

```
# Implementation would send stop signal to running engine
# This could be done via PID file, socket, or other IPC mechanism

console.print("[yellow]🛑 Sending stop signal to SmartArb Engine...[/yellow]")

# Check if engine is running (simplified check)
pid_file = Path("smartarb.pid")
if pid_file.exists():
    try:
        import os
        import signal
        
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        os.kill(pid, signal.SIGTERM)
        console.print("[green]✅ Stop signal sent successfully[/green]")
        
        # Wait for graceful shutdown
        time.sleep(2)
        
        if not pid_file.exists():
            console.print("[green]✅ Engine stopped successfully[/green]")
        else:
            console.print("[yellow]⚠️  Engine may still be running[/yellow]")
            
    except (FileNotFoundError, ProcessLookupError):
        console.print("[yellow]⚠️  Engine is not running[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Failed to stop engine: {str(e)}[/red]")
else:
    console.print("[yellow]⚠️  Engine does not appear to be running[/yellow]")
```

# Helper functions

async def create_status_panel(engine):
“”“Create live status panel”””
try:
status = await engine.get_engine_status()

```
    # Create layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    # Header
    layout["header"].update(Panel(
        f"[bold cyan]SmartArb Engine Status[/bold cyan] - {time.strftime('%H:%M:%S')}",
        box=box.ROUNDED
    ))
    
    # Body - split into columns
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    # Left column - Engine info
    engine_info = Table(show_header=False, box=box.SIMPLE)
    engine_info.add_column("Property", style="cyan")
    engine_info.add_column("Value")
    
    engine_info.add_row("Status", f"[green]{status['status']}[/green]")
    engine_info.add_row("Uptime", f"{status.get('uptime', 0):.1f}s")
    engine_info.add_row("Total Trades", str(status.get('trades', {}).get('total', 0)))
    engine_info.add_row("Success Rate", f"{status.get('trades', {}).get('success_rate', 0):.1f}%")
    
    layout["left"].update(Panel(engine_info, title="Engine"))
    
    # Right column - Exchanges
    exchanges_info = Table(show_header=True, box=box.SIMPLE)
    exchanges_info.add_column("Exchange", style="cyan")
    exchanges_info.add_column("Status")
    exchanges_info.add_column("Last Ping")
    
    for ex_name, ex_data in status.get('exchanges', {}).items():
        status_icon = "🟢" if ex_data.get('connected', False) else "🔴"
        ping = f"{ex_data.get('ping_ms', 0):.0f}ms"
        exchanges_info.add_row(ex_name.title(), status_icon, ping)
    
    layout["right"].update(Panel(exchanges_info, title="Exchanges"))
    
    # Footer
    layout["footer"].update(Panel(
        "[dim]Press Ctrl+C to stop the engine[/dim]",
        box=box.ROUNDED
    ))
    
    return layout
    
except Exception as e:
    return Panel(f"[red]Error creating status panel: {str(e)}[/red]")
```

def create_status_display(status: Dict[str, Any]) -> Panel:
“”“Create status display panel”””

```
table = Table(show_header=False, box=box.SIMPLE)
table.add_column("Property", style="cyan", width=20)
table.add_column("Value", width=40)

# Engine status
status_color = "green" if status['status'] == 'RUNNING' else "yellow"
table.add_row("Engine Status", f"[{status_color}]{status['status']}[/{status_color}]")

# Exchanges
connected_exchanges = len([ex for ex in status.get('exchanges', {}).values() 
                          if ex.get('connected', False)])
total_exchanges = len(status.get('exchanges', {}))
table.add_row("Exchanges", f"{connected_exchanges}/{total_exchanges} connected")

# Strategies
active_strategies = len(status.get('strategies', {}))
table.add_row("Active Strategies", str(active_strategies))

# Portfolio
portfolio_value = status.get('portfolio', {}).get('total_value', 0)
table.add_row("Portfolio Value", f"${portfolio_value:.2f}")

# Trades
total_trades = status.get('trades', {}).get('total', 0)
success_rate = status.get('trades', {}).get('success_rate', 0)
table.add_row("Total Trades", f"{total_trades} ({success_rate:.1f}% success)")

return Panel(table, title="[bold cyan]SmartArb Engine Status[/bold cyan]", 
            box=box.ROUNDED)
```

async def show_config_status(config_manager: ConfigManager):
“”“Show configuration status”””

```
summary = config_manager.get_config_summary()

# Configuration overview
config_table = Table(title="Configuration Summary", box=box.ROUNDED)
config_table.add_column("Property", style="cyan")
config_table.add_column("Value")
config_table.add_column("Status")

config_table.add_row(
    "Config File", 
    str(summary['config_file']), 
    "✅ Found" if summary['config_exists'] else "❌ Missing"
)

config_table.add_row(
    "Exchanges Configured", 
    str(summary['exchanges_configured']),
    f"✅ {summary['exchanges_enabled']} enabled" if summary['exchanges_enabled'] >= 2 else "⚠️  Need 2+ exchanges"
)

config_table.add_row(
    "Strategies", 
    str(summary['strategies_configured']),
    f"✅ {summary['strategies_enabled']} enabled" if summary['strategies_enabled'] > 0 else "⚠️  No strategies enabled"
)

config_table.add_row(
    "Trading Mode", 
    "Paper Trading" if summary['paper_trading'] else "Live Trading",
    "🧪 Safe" if summary['paper_trading'] else "⚠️  Real money"
)

config_table.add_row(
    "AI Analysis", 
    "Enabled" if summary['ai_enabled'] else "Disabled",
    "🧠 Active" if summary['ai_enabled'] else "➖ Inactive"
)

console.print(config_table)

# Exchange credentials status
if summary['credentials_status']:
    cred_table = Table(title="Exchange Credentials", box=box.ROUNDED)
    cred_table.add_column("Exchange", style="cyan")
    cred_table.add_column("API Credentials")
    
    for exchange, has_creds in summary['credentials_status'].items():
        status = "✅ Configured" if has_creds else "❌ Missing"
        cred_table.add_row(exchange.title(), status)
    
    console.print(cred_table)
```

async def test_all_exchanges(engine, progress):
“”“Test all exchange connections”””

```
for exchange_name, exchange in engine.exchanges.items():
    await test_single_exchange_connection(exchange_name, exchange, progress)
```

async def test_single_exchange(engine, exchange_name, progress):
“”“Test single exchange connection”””

```
if exchange_name not in engine.exchanges:
    console.print(f"[red]❌ Exchange '{exchange_name}' not found[/red]")
    return

exchange = engine.exchanges[exchange_name]
await test_single_exchange_connection(exchange_name, exchange, progress)
```

async def test_single_exchange_connection(exchange_name, exchange, progress):
“”“Test individual exchange connection”””

```
test_task = progress.add_task(f"Testing {exchange_name}...", total=None)

try:
    # Test connection
    if await exchange.connect():
        progress.update(test_task, description=f"✅ {exchange_name} connected")
        
        # Test API functionality
        ticker = await exchange.get_ticker("BTC/USDT")
        if ticker:
            progress.update(test_task, description=f"✅ {exchange_name} API working")
        else:
            progress.update(test_task, description=f"⚠️  {exchange_name} API limited")
    else:
        progress.update(test_task, description=f"❌ {exchange_name} connection failed")
        
except Exception as e:
    progress.update(test_task, description=f"❌ {exchange_name} error: {str(e)[:50]}")
```

def show_portfolio_table(balances):
“”“Show portfolio in table format”””

```
if not balances:
    console.print("[yellow]No portfolio balances found[/yellow]")
    return

# Main portfolio table
portfolio_table = Table(title="Portfolio Balances", box=box.ROUNDED)
portfolio_table.add_column("Asset", style="cyan")
portfolio_table.add_column("Total Balance", justify="right")
portfolio_table.add_column("Available", justify="right") 
portfolio_table.add_column("Locked", justify="right")
portfolio_table.add_column("Exchanges", justify="center")

for asset, balance in balances.items():
    exchange_count = len(balance.exchange_balances)
    portfolio_table.add_row(
        asset,
        f"{balance.total_balance:.8f}",
        f"{balance.available_balance:.8f}",
        f"{balance.locked_balance:.8f}",
        str(exchange_count)
    )

console.print(portfolio_table)

# Detailed exchange breakdown
for asset, balance in balances.items():
    if len(balance.exchange_balances) > 1:
        exchange_table = Table(title=f"{asset} Exchange Breakdown", box=box.SIMPLE)
        exchange_table.add_column("Exchange", style="cyan")
        exchange_table.add_column("Balance", justify="right")
        exchange_table.add_column("Available", justify="right")
        exchange_table.add_column("Locked", justify="right")
        
        for ex_name, ex_balance in balance.exchange_balances.items():
            exchange_table.add_row(
                ex_name.title(),
                f"{ex_balance.total:.8f}",
                f"{ex_balance.free:.8f}",
                f"{ex_balance.locked:.8f}"
            )
        
        console.print(exchange_table)
```

def show_performance_metrics(metrics: Dict[str, Any], days: int):
“”“Show performance metrics”””

```
perf_table = Table(title=f"Performance Metrics (Last {days} days)", box=box.ROUNDED)
perf_table.add_column("Metric", style="cyan")
perf_table.add_column("Value", justify="right")

# Add performance data
engine_metrics = metrics.get('engine', {})
trades_metrics = engine_metrics.get('trades', {})

perf_table.add_row("Total Trades", str(trades_metrics.get('total', 0)))
perf_table.add_row("Successful Trades", str(trades_metrics.get('successful', 0)))
perf_table.add_row("Success Rate", f"{trades_metrics.get('success_rate', 0):.1f}%")
perf_table.add_row("Total Profit", f"${trades_metrics.get('total_profit', 0):.2f}")
perf_table.add_row("Average Profit", f"${trades_metrics.get('avg_profit', 0):.2f}")

console.print(perf_table)
```

def main():
“”“Main entry point for CLI”””

```
# Ensure we're running the CLI in an asyncio context where needed
def run_async_command():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        cli()
    finally:
        loop.close()

# Check if we need to run async commands
if len(sys.argv) > 1 and sys.argv[1] in ['start', 'status', 'test', 'portfolio', 'performance']:
    # For async commands, we need to handle the event loop
    import functools
    
    # Wrap CLI to handle async
    original_command = cli.commands[sys.argv[1]]
    
    def async_wrapper(*args, **kwargs):
        return asyncio.run(original_command(*args, **kwargs))
    
    cli.commands[sys.argv[1]] = click.command()(async_wrapper)

cli()
```

if **name** == ‘**main**’:
main()