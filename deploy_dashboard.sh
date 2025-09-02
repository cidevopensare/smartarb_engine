#!/bin/bash
echo "🚀 Creating SmartArb Dashboard files..."

# Create directories
mkdir -p static/dashboard/{js,css,icons}

# Create complete dashboard HTML
cat > static/dashboard/index.html << 'DASHBOARD_HTML'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartArb Engine Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%);
            color: #ffffff;
            min-height: 100vh;
        }

        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(45deg, #00d2ff, #3a47d5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }

        .status-running { background-color: #00ff88; }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #00d2ff, #3a47d5);
        }

        .card h3 {
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #00d2ff;
        }

        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .metric:last-child {
            border-bottom: none;
        }

        .metric-value {
            font-weight: bold;
            font-size: 1.1em;
        }

        .positive { color: #00ff88; }
        .negative { color: #ff4444; }

        .exchanges {
            display: flex;
            gap: 15px;
            margin-top: 15px;
        }

        .exchange {
            flex: 1;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            text-align: center;
            border: 2px solid #00ff88;
        }

        .exchange h4 {
            margin-bottom: 10px;
            color: #ffffff;
        }

        .btn {
            background: linear-gradient(45deg, #00d2ff, #3a47d5);
            border: none;
            border-radius: 25px;
            padding: 12px 30px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 10px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0, 210, 255, 0.3);
        }

        .controls {
            text-align: center;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🚀 SmartArb Engine Dashboard</h1>
            <p>
                <span class="status-indicator status-running"></span>
                <span id="engineStatus">System Online</span>
            </p>
            <p id="lastUpdate">Live Dashboard - Real-time Data</p>
        </div>

        <div class="grid">
            <!-- System Status Card -->
            <div class="card">
                <h3>🔧 System Status</h3>
                <div class="metric">
                    <span>Engine Status</span>
                    <span class="metric-value positive" id="engineState">Running</span>
                </div>
                <div class="metric">
                    <span>Uptime</span>
                    <span class="metric-value" id="uptime">1h 0m</span>
                </div>
                <div class="metric">
                    <span>Memory Usage</span>
                    <span class="metric-value" id="memoryUsage">45.2%</span>
                </div>
                <div class="metric">
                    <span>CPU Usage</span>
                    <span class="metric-value" id="cpuUsage">12.8%</span>
                </div>
            </div>

            <!-- Trading Performance Card -->
            <div class="card">
                <h3>📈 Trading Performance</h3>
                <div class="metric">
                    <span>Total Trades</span>
                    <span class="metric-value" id="totalTrades">23</span>
                </div>
                <div class="metric">
                    <span>Success Rate</span>
                    <span class="metric-value positive" id="successRate">85.2%</span>
                </div>
                <div class="metric">
                    <span>Total Profit</span>
                    <span class="metric-value positive" id="totalProfit">$145.75</span>
                </div>
                <div class="metric">
                    <span>Daily P&L</span>
                    <span class="metric-value positive" id="dailyPnl">+$24.50</span>
                </div>
            </div>

            <!-- AI Analysis Card -->
            <div class="card">
                <h3>🧠 AI Analysis</h3>
                <div class="metric">
                    <span>Claude Status</span>
                    <span class="metric-value positive">Active</span>
                </div>
                <div class="metric">
                    <span>Last Analysis</span>
                    <span class="metric-value">2 min ago</span>
                </div>
                <div class="metric">
                    <span>Recommendations</span>
                    <span class="metric-value">3 pending</span>
                </div>
                <div class="metric">
                    <span>Confidence</span>
                    <span class="metric-value positive">87%</span>
                </div>
            </div>

            <!-- Risk Management Card -->
            <div class="card">
                <h3>⚖️ Risk Management</h3>
                <div class="metric">
                    <span>Risk Level</span>
                    <span class="metric-value positive">Low</span>
                </div>
                <div class="metric">
                    <span>Active Positions</span>
                    <span class="metric-value">2</span>
                </div>
                <div class="metric">
                    <span>Circuit Breaker</span>
                    <span class="metric-value positive">Normal</span>
                </div>
            </div>
        </div>

        <!-- Exchange Status -->
        <div class="card">
            <h3>🏦 Exchange Connections</h3>
            <div class="exchanges">
                <div class="exchange">
                    <h4>Kraken</h4>
                    <div style="color: #00ff88;">Connected</div>
                    <div style="font-size: 0.8em; margin-top: 5px;">
                        <div>Latency: 45ms</div>
                        <div>Balance: $200.00</div>
                    </div>
                </div>
                <div class="exchange">
                    <h4>Bybit</h4>
                    <div style="color: #00ff88;">Connected</div>
                    <div style="font-size: 0.8em; margin-top: 5px;">
                        <div>Latency: 62ms</div>
                        <div>Balance: $200.00</div>
                    </div>
                </div>
                <div class="exchange">
                    <h4>MEXC</h4>
                    <div style="color: #00ff88;">Connected</div>
                    <div style="font-size: 0.8em; margin-top: 5px;">
                        <div>Latency: 78ms</div>
                        <div>Balance: $200.00</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Controls -->
        <div class="controls">
            <button class="btn" onclick="refreshDashboard()">🔄 Refresh</button>
            <button class="btn" onclick="showOpportunities()">💰 View Opportunities</button>
            <button class="btn" onclick="viewLogs()">📋 View Logs</button>
        </div>
    </div>

    <script>
        // Dashboard JavaScript
        const API_BASE = window.location.origin;

        function refreshDashboard() {
            location.reload();
        }

        function showOpportunities() {
            window.open(`${API_BASE}/api/opportunities`, '_blank');
        }

        function viewLogs() {
            alert('🚀 SmartArb Engine Dashboard Active!\n\nLogs available via:\nsudo journalctl -u smartarb -f');
        }

        // Auto-refresh data every 30 seconds
        setInterval(async () => {
            try {
                const response = await fetch(`${API_BASE}/api/metrics`);
                const data = await response.json();
                
                document.getElementById('totalTrades').textContent = data.trades_executed;
                document.getElementById('successRate').textContent = data.success_rate + '%';
                document.getElementById('totalProfit').textContent = '$' + data.total_profit;
                document.getElementById('dailyPnl').textContent = '$' + data.daily_pnl;
                document.getElementById('memoryUsage').textContent = data.memory_usage + '%';
                document.getElementById('cpuUsage').textContent = data.cpu_usage + '%';
                
                document.getElementById('lastUpdate').textContent = 
                    'Last updated: ' + new Date().toLocaleTimeString();
            } catch (error) {
                console.log('Auto-refresh failed:', error);
            }
        }, 30000);

        // Show welcome message
        setTimeout(() => {
            alert('🎉 Welcome to SmartArb Engine Dashboard!\n\n✅ Dashboard is now live\n📱 Add to home screen for mobile app experience\n🔄 Data refreshes automatically every 30 seconds');
        }, 2000);
    </script>
</body>
</html>
DASHBOARD_HTML

echo "✅ Dashboard HTML created!"
echo "📊 Refresh your browser to see the new dashboard!"
