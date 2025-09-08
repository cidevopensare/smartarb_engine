#!/bin/bash
# fix_opportunities_and_notifications.sh - Risolve grafico opportunities e notifiche

echo "🔧 Fixing opportunities chart and Telegram notifications..."

# Backup
cp src/core/unified_engine.py src/core/unified_engine.py.before_final_fix

# Apply fixes
cat > /tmp/final_fix.py << 'EOF'
import re

def apply_fixes(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    # 1. Fix opportunities chart - remove problematic 'time' type
    old_opportunities_chart = '''function createOpportunitiesChart(ctx) {{
                            fetch('/api/opportunities-timeline')
                                .then(response => response.json())
                                .then(data => {{
                                    chartInstance = new Chart(ctx, {{
                                        type: 'scatter',
                                        data: {{
                                            datasets: [{{
                                                label: 'Executed',
                                                data: data.filter(d => d.executed).map(d => ({{
                                                    x: new Date(d.timestamp),
                                                    y: d.spread
                                                }})),
                                                backgroundColor: '#00ff88',
                                                borderColor: '#00ff88',
                                                pointRadius: 6
                                            }}, {{
                                                label: 'Missed',
                                                data: data.filter(d => !d.executed).map(d => ({{
                                                    x: new Date(d.timestamp),
                                                    y: d.spread
                                                }})),
                                                backgroundColor: '#ff4444',
                                                borderColor: '#ff4444',
                                                pointRadius: 4
                                            }}]
                                        }},
                                        options: {{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: {{
                                                legend: {{
                                                    labels: {{ color: '#fff' }}
                                                }}
                                            }},
                                            scales: {{
                                                x: {{
                                                    type: 'time',
                                                    time: {{
                                                        unit: 'hour'
                                                    }},
                                                    grid: {{ color: 'rgba(255,255,255,0.1)' }},
                                                    ticks: {{ color: '#999' }}
                                                }},
                                                y: {{
                                                    title: {{
                                                        display: true,
                                                        text: 'Spread %',
                                                        color: '#fff'
                                                    }},
                                                    grid: {{ color: 'rgba(255,255,255,0.1)' }},
                                                    ticks: {{ color: '#999' }}
                                                }}
                                            }}
                                        }}
                                    }});
                                }});
                        }}'''
    
    new_opportunities_chart = '''function createOpportunitiesChart(ctx) {{
                            fetch('/api/opportunities-timeline')
                                .then(response => response.json())
                                .then(data => {{
                                    // Convert to simpler format for chart
                                    const executed = data.filter(d => d.executed);
                                    const missed = data.filter(d => !d.executed);
                                    
                                    // Create labels from timestamps (last 12 hours)
                                    const labels = [];
                                    for(let i = 11; i >= 0; i--) {{
                                        const date = new Date();
                                        date.setHours(date.getHours() - i);
                                        labels.push(date.getHours() + ':00');
                                    }}
                                    
                                    // Count opportunities per hour
                                    const executedData = new Array(12).fill(0);
                                    const missedData = new Array(12).fill(0);
                                    
                                    executed.forEach(opp => {{
                                        const hour = new Date(opp.timestamp).getHours();
                                        const currentHour = new Date().getHours();
                                        const index = 11 - (currentHour - hour + 24) % 24;
                                        if (index >= 0 && index < 12) executedData[index]++;
                                    }});
                                    
                                    missed.forEach(opp => {{
                                        const hour = new Date(opp.timestamp).getHours();
                                        const currentHour = new Date().getHours();
                                        const index = 11 - (currentHour - hour + 24) % 24;
                                        if (index >= 0 && index < 12) missedData[index]++;
                                    }});
                                    
                                    chartInstance = new Chart(ctx, {{
                                        type: 'bar',
                                        data: {{
                                            labels: labels,
                                            datasets: [{{
                                                label: 'Executed',
                                                data: executedData,
                                                backgroundColor: '#00ff88',
                                                borderColor: '#00ff88',
                                                borderWidth: 1
                                            }}, {{
                                                label: 'Missed',
                                                data: missedData,
                                                backgroundColor: '#ff4444',
                                                borderColor: '#ff4444',
                                                borderWidth: 1
                                            }}]
                                        }},
                                        options: {{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: {{
                                                legend: {{
                                                    labels: {{ color: '#fff' }}
                                                }}
                                            }},
                                            scales: {{
                                                x: {{
                                                    grid: {{ color: 'rgba(255,255,255,0.1)' }},
                                                    ticks: {{ color: '#999' }}
                                                }},
                                                y: {{
                                                    title: {{
                                                        display: true,
                                                        text: 'Opportunities Count',
                                                        color: '#fff'
                                                    }},
                                                    grid: {{ color: 'rgba(255,255,255,0.1)' }},
                                                    ticks: {{ color: '#999' }}
                                                }}
                                            }}
                                        }}
                                    }});
                                }});
                        }}'''
    
    content = content.replace(old_opportunities_chart, new_opportunities_chart)
    
    # 2. Fix trading loop - faster trades and notifications
    old_trading_loop = '''async def trading_loop(self):
        """Main trading simulation loop"""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Simulate every 30 seconds
                self.update_trading_data()
                
                if self.stats['trades_executed'] % 10 == 0:
                    mode = "LIVE" if self.is_live_trading else "PAPER"
                    logger.info(f"📈 [{mode}] Trades: {self.stats['trades_executed']}, "
                              f"Profit: ${self.stats['total_profit']:.2f}")
                
            except Exception as e:
                logger.error(f"❌ Trading loop error: {e}")
                await asyncio.sleep(5)'''
    
    new_trading_loop = '''async def trading_loop(self):
        """Main trading simulation loop"""
        notification_counter = 0
        
        while self.is_running:
            try:
                await asyncio.sleep(10)  # Faster: every 10 seconds
                self.update_trading_data()
                notification_counter += 1
                
                # Log every 10 trades
                if self.stats['trades_executed'] % 10 == 0:
                    mode = "LIVE" if self.is_live_trading else "PAPER"
                    logger.info(f"📈 [{mode}] Trades: {self.stats['trades_executed']}, "
                              f"Profit: ${self.stats['total_profit']:.2f}")
                
                # Send Telegram notification every 15 trades (instead of 25)
                if notification_counter >= 15:
                    notification_counter = 0
                    
                    # Get performance stats
                    top_exchange = max(self.exchanges.items(), key=lambda x: x[1]['trades'])
                    top_pair = max(self.trading_pairs.items(), key=lambda x: x[1]['trades'])
                    avg_latency = sum(ex['latency_ms'] for ex in self.exchanges.values()) / len(self.exchanges)
                    mode = "🔴 LIVE" if self.is_live_trading else "📄 PAPER"
                    
                    message = f"""🚀 <b>SmartArb Professional Report</b>

📊 <b>Performance Metrics:</b>
📈 Total Trades: {self.stats['trades_executed']}
💰 Total Profit: ${self.stats['total_profit']:.2f}
📊 Success Rate: {self.stats['success_rate']:.1f}%
🎯 Opportunities: {self.stats['opportunities_found']}

🔄 <b>Trading Mode:</b> {mode}

🧠 <b>AI Intelligence:</b>
Status: {'🟢 Active' if self.ai_status['enabled'] else '🔴 Inactive'}
Analyses: {self.ai_status['analysis_count']}
Recommendations: {self.ai_status['recommendations_active']}

🏆 <b>Top Performers:</b>
{top_exchange[1]['symbol']} Exchange: {top_exchange[0]} ({top_exchange[1]['trades']} trades)
{top_pair[1]['icon']} Pair: {top_pair[0]} ({top_pair[1]['trades']} trades)

⚡ <b>Network Performance:</b>
Average Latency: {avg_latency:.0f}ms

⏱️ <b>Uptime:</b> {datetime.now() - self.start_time}
🌐 <b>Dashboard:</b> http://localhost:8001"""
                    
                    await self.send_telegram_notification(message)
                
            except Exception as e:
                logger.error(f"❌ Trading loop error: {e}")
                await asyncio.sleep(5)'''
    
    content = content.replace(old_trading_loop, new_trading_loop)
    
    # 3. Update trading data function to create more activity
    old_update = '''def update_trading_data(self):
        """Update trading data with simulation"""
        self.stats['trades_executed'] += 1
        trade_profit = random.uniform(10, 30)
        self.stats['total_profit'] += trade_profit
        self.stats['daily_pnl'] += trade_profit
        
        # Update random exchange
        exchange_names = list(self.exchanges.keys())
        selected_exchange = random.choice(exchange_names)
        self.exchanges[selected_exchange]['trades'] += 1
        
        # Update random pair
        pairs = list(self.trading_pairs.keys())
        selected_pair = random.choice(pairs)
        self.trading_pairs[selected_pair]['trades'] += 1
        self.trading_pairs[selected_pair]['profit'] += trade_profit'''
    
    new_update = '''def update_trading_data(self):
        """Update trading data with simulation"""
        self.stats['trades_executed'] += 1
        self.stats['opportunities_found'] += random.randint(1, 3)
        
        trade_profit = random.uniform(8, 35)
        self.stats['total_profit'] += trade_profit
        self.stats['daily_pnl'] += trade_profit
        
        # Update random exchange
        exchange_names = list(self.exchanges.keys())
        selected_exchange = random.choice(exchange_names)
        self.exchanges[selected_exchange]['trades'] += 1
        self.exchanges[selected_exchange]['volume_24h'] += trade_profit
        
        # Update latency simulation
        for name, data in self.exchanges.items():
            base_latency = {'Bybit': 45, 'MEXC': 62, 'Kraken': 78}[name]
            self.exchanges[name]['latency_ms'] = max(20, base_latency + random.randint(-15, 30))
        
        # Update random pair
        pairs = list(self.trading_pairs.keys())
        selected_pair = random.choice(pairs)
        self.trading_pairs[selected_pair]['trades'] += 1
        self.trading_pairs[selected_pair]['profit'] += trade_profit'''
    
    content = content.replace(old_update, new_update)
    
    with open(filename, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    apply_fixes('src/core/unified_engine.py')
    print("✅ Opportunities chart and notifications fixed!")
EOF

# Execute the fix
python3 /tmp/final_fix.py

echo "✅ Applied fixes:"
echo "   • Opportunities chart now works (bar chart instead of scatter)"
echo "   • Faster trading: 10 seconds instead of 30"
echo "   • Telegram notifications every 15 trades instead of 25"
echo "   • More dynamic latency and volume updates"

# Restart system
echo ""
echo "🔄 Restarting system..."
make stop
sleep 2
make start-with-ai

echo ""
echo "🎉 All fixes applied!"
echo "📱 You should receive Telegram notifications every ~2.5 minutes now"
echo "📊 Opportunities chart should work with bars showing executed vs missed"
echo "🌐 Dashboard: http://localhost:8001"
