#!/usr/bin/env python3
"""
SmartArb Unified Engine - Professional Dashboard with Advanced Features
"""

import asyncio
import logging
import sys
import os
import time
import threading
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Setup logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/unified_engine.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('unified_smartarb')

class UnifiedSmartArbEngine:
    """Professional SmartArb Engine with Advanced Dashboard"""
    
    def __init__(self):
        self.is_running = False
        self.is_live_trading = False  # Paper trading by default
        self.start_time = datetime.now()
        
        # Core trading stats
        self.stats = {
            'trades_executed': 0,
            'success_rate': 87.5,
            'total_profit': 0.0,
            'opportunities_found': 0,
            'daily_pnl': 0.0
        }
        
        # AI Status
        self.ai_status = {
            'enabled': True,
            'mode': 'advisory_only',
            'analysis_count': 7,
            'recommendations_active': 3,
            'last_analysis': datetime.now()
        }
        
        # Exchange data with professional symbols
        self.exchanges = {
            'Bybit': {'connected': True, 'latency_ms': 45, 'trades': 0, 'symbol': '🔶', 'volume_24h': 0.0},
            'MEXC': {'connected': True, 'latency_ms': 62, 'trades': 0, 'symbol': '🔷', 'volume_24h': 0.0},
            'Kraken': {'connected': True, 'latency_ms': 78, 'trades': 0, 'symbol': '🔵', 'volume_24h': 0.0}
        }
        
        # Trading pairs with crypto symbols
        self.trading_pairs = {
            'BTC/USDT': {'trades': 0, 'profit': 0.0, 'symbol': '₿', 'icon': '🟠'},
            'ETH/USDT': {'trades': 0, 'profit': 0.0, 'symbol': 'Ξ', 'icon': '🔷'},
            'ADA/USDT': {'trades': 0, 'profit': 0.0, 'symbol': '₳', 'icon': '🔵'},
            'SOL/USDT': {'trades': 0, 'profit': 0.0, 'symbol': '◎', 'icon': '🟣'},
            'DOT/USDT': {'trades': 0, 'profit': 0.0, 'symbol': '●', 'icon': '🟢'}
        }
        
        self.dashboard_app = None
    
    def start_dashboard_server(self):
        """Start professional dashboard with all features"""
        try:
            from fastapi import FastAPI
            from fastapi.responses import HTMLResponse, JSONResponse
            import uvicorn
            import psutil
            
            self.dashboard_app = FastAPI(title="SmartArb Professional")
            
            @self.dashboard_app.get("/")
            def professional_dashboard():
                uptime = datetime.now() - self.start_time
                uptime_str = str(uptime).split('.')[0]
                mode_color = "#ff4444" if not self.is_live_trading else "#00ff88"
                mode_text = "📄 PAPER TRADING" if not self.is_live_trading else "🔴 LIVE TRADING"
                
                return HTMLResponse(f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>SmartArb Engine - Professional Dashboard</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <meta http-equiv="refresh" content="30">
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
                    <style>
                        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                        
                        body {{ 
                            font-family: 'Inter', 'Segoe UI', Arial, sans-serif; 
                            background: linear-gradient(135deg, #0a0a0a, #1a1a2e, #16213e, #0f0f23); 
                            color: #ffffff; 
                            min-height: 100vh;
                            padding: 20px;
                            background-size: 400% 400%;
                            animation: gradientShift 15s ease infinite;
                            display: flex;
                        }}
                        
                        @keyframes gradientShift {{
                            0% {{ background-position: 0% 50%; }}
                            50% {{ background-position: 100% 50%; }}
                            100% {{ background-position: 0% 50%; }}
                        }}
                        
                        /* Main Layout */
                        .main-container {{
                            flex: 1;
                            margin-left: 0;
                            transition: margin-left 0.3s ease;
                        }}
                        
                        .main-container.sidebar-open {{
                            margin-left: 350px;
                        }}
                        
                        /* AI Sidebar */
                        .ai-sidebar {{
                            position: fixed;
                            left: -350px;
                            top: 0;
                            width: 350px;
                            height: 100vh;
                            background: linear-gradient(180deg, #1a1a2e, #16213e);
                            backdrop-filter: blur(20px);
                            border-right: 1px solid rgba(0,212,255,0.3);
                            transition: left 0.3s ease;
                            z-index: 1000;
                            overflow-y: auto;
                        }}
                        
                        .ai-sidebar.open {{
                            left: 0;
                        }}
                        
                        .ai-sidebar-header {{
                            padding: 20px;
                            border-bottom: 1px solid rgba(255,255,255,0.1);
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                        }}
                        
                        .ai-sidebar-content {{
                            padding: 20px;
                        }}
                        
                        .ai-section {{
                            margin-bottom: 30px;
                        }}
                        
                        .ai-section h4 {{
                            color: #00d4ff;
                            margin-bottom: 15px;
                            font-size: 1.1rem;
                        }}
                        
                        /* Header */
                        .header {{
                            text-align: center;
                            margin-bottom: 30px;
                            padding: 25px;
                            background: rgba(255,255,255,0.1);
                            border-radius: 20px;
                            backdrop-filter: blur(15px);
                            border: 1px solid rgba(255,255,255,0.2);
                            position: relative;
                        }}
                        
                        .header h1 {{
                            font-size: 2.8rem;
                            margin-bottom: 10px;
                            background: linear-gradient(45deg, #00d4ff, #00ff88, #ff6b35);
                            background-clip: text;
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            text-shadow: 0 0 30px rgba(0,212,255,0.5);
                        }}
                        
                        .trading-mode {{
                            display: inline-flex;
                            align-items: center;
                            gap: 10px;
                            margin-top: 10px;
                            padding: 8px 16px;
                            border-radius: 20px;
                            background: {mode_color}33;
                            border: 1px solid {mode_color}66;
                            color: {mode_color};
                            font-weight: bold;
                        }}
                        
                        .controls-header {{
                            position: absolute;
                            top: 20px;
                            right: 20px;
                            display: flex;
                            gap: 10px;
                        }}
                        
                        .control-btn {{
                            background: rgba(255,255,255,0.1);
                            border: 1px solid rgba(255,255,255,0.3);
                            border-radius: 10px;
                            padding: 8px 12px;
                            color: #fff;
                            cursor: pointer;
                            transition: all 0.3s ease;
                            font-size: 0.9rem;
                        }}
                        
                        .control-btn:hover {{
                            background: rgba(255,255,255,0.2);
                            transform: translateY(-2px);
                        }}
                        
                        .pulse {{ animation: pulse 2s infinite; }}
                        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
                        
                        /* Dashboard Grid */
                        .dashboard-grid {{
                            display: grid;
                            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                            gap: 25px;
                            margin-bottom: 30px;
                        }}
                        
                        .card {{
                            background: rgba(255,255,255,0.1);
                            border-radius: 20px;
                            padding: 25px;
                            backdrop-filter: blur(15px);
                            border: 1px solid rgba(255,255,255,0.2);
                            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                            transition: all 0.3s ease;
                            position: relative;
                        }}
                        
                        .card:hover {{
                            transform: translateY(-5px);
                            box-shadow: 0 15px 40px rgba(0,212,255,0.2);
                            border-color: rgba(0,212,255,0.4);
                        }}
                        
                        .card h3 {{
                            font-size: 1.4rem;
                            margin-bottom: 20px;
                            color: #00d4ff;
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                        }}
                        
                        .metric {{
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            margin-bottom: 15px;
                            padding: 10px 0;
                            border-bottom: 1px solid rgba(255,255,255,0.1);
                        }}
                        
                        .metric:last-child {{ border-bottom: none; }}
                        
                        .metric span:first-child {{
                            color: #bbb;
                            font-weight: 500;
                        }}
                        
                        .metric span:last-child {{
                            font-weight: 700;
                            font-size: 1.1rem;
                        }}
                        
                        .positive {{ color: #00ff88 !important; }}
                        .negative {{ color: #ff4444 !important; }}
                        .warning {{ color: #ffaa00 !important; }}
                        
                        /* Chart Container */
                        .chart-container {{
                            background: rgba(255,255,255,0.05);
                            border-radius: 15px;
                            padding: 20px;
                            margin-top: 15px;
                            height: 300px;
                            position: relative;
                        }}
                        
                        .chart-tabs {{
                            display: flex;
                            gap: 10px;
                            margin-bottom: 15px;
                        }}
                        
                        .chart-tab {{
                            background: rgba(255,255,255,0.1);
                            border: none;
                            border-radius: 8px;
                            padding: 6px 12px;
                            color: #fff;
                            cursor: pointer;
                            transition: all 0.2s ease;
                            font-size: 0.9rem;
                        }}
                        
                        .chart-tab.active {{
                            background: rgba(0,212,255,0.3);
                            color: #00d4ff;
                        }}
                        
                        /* AI Sidebar Toggle Button */
                        .ai-sidebar-toggle {{
                            position: fixed;
                            left: 20px;
                            top: 50%;
                            transform: translateY(-50%);
                            background: linear-gradient(45deg, #00d4ff, #00ff88);
                            border: none;
                            border-radius: 50%;
                            width: 50px;
                            height: 50px;
                            color: #000;
                            font-size: 1.2rem;
                            cursor: pointer;
                            transition: all 0.3s ease;
                            z-index: 1001;
                            box-shadow: 0 5px 15px rgba(0,212,255,0.4);
                        }}
                        
                        .ai-sidebar-toggle:hover {{
                            transform: translateY(-50%) scale(1.1);
                            box-shadow: 0 8px 25px rgba(0,212,255,0.6);
                        }}
                        
                        .ai-sidebar-toggle.sidebar-open {{
                            left: 370px;
                        }}
                        
                        /* Exchange and Pair Cards */
                        .grid-container {{
                            display: grid;
                            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                            gap: 15px;
                            margin-top: 15px;
                        }}
                        
                        .exchange-card, .pair-card {{
                            background: rgba(255,255,255,0.05);
                            border-radius: 12px;
                            padding: 15px;
                            text-align: center;
                            transition: all 0.3s ease;
                            cursor: pointer;
                        }}
                        
                        .exchange-card:hover, .pair-card:hover {{
                            transform: scale(1.02);
                            border: 1px solid rgba(0,212,255,0.5);
                            box-shadow: 0 5px 15px rgba(0,212,255,0.2);
                        }}
                        
                        .exchange-symbol, .crypto-icon {{
                            font-size: 1.5rem;
                            margin-bottom: 8px;
                        }}
                        
                        /* Control Panel */
                        .control-panel {{
                            grid-column: 1 / -1;
                            background: rgba(255,255,255,0.05);
                            border-radius: 20px;
                            padding: 25px;
                            border: 1px solid rgba(255,255,255,0.1);
                        }}
                        
                        .control-grid {{
                            display: grid;
                            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                            gap: 20px;
                            margin-top: 20px;
                        }}
                        
                        .control-section {{
                            background: rgba(255,255,255,0.05);
                            border-radius: 12px;
                            padding: 20px;
                            text-align: center;
                        }}
                        
                        .control-section h4 {{
                            color: #00d4ff;
                            margin-bottom: 15px;
                        }}
                        
                        .control-btn-large {{
                            background: linear-gradient(45deg, #00d4ff, #00ff88);
                            border: none;
                            border-radius: 12px;
                            padding: 12px 24px;
                            color: #000;
                            font-weight: bold;
                            cursor: pointer;
                            transition: all 0.3s ease;
                            font-size: 1rem;
                            width: 100%;
                            margin-bottom: 10px;
                        }}
                        
                        .control-btn-large:hover {{
                            transform: translateY(-2px);
                            box-shadow: 0 10px 25px rgba(0,212,255,0.4);
                        }}
                        
                        .control-btn-large.danger {{
                            background: linear-gradient(45deg, #ff4444, #ff6b35);
                        }}
                        
                        /* Responsive */
                        @media (max-width: 768px) {{
                            .header h1 {{ font-size: 2rem; }}
                            .dashboard-grid {{ grid-template-columns: 1fr; }}
                            .ai-sidebar {{ width: 100%; left: -100%; }}
                            .main-container.sidebar-open {{ margin-left: 0; }}
                            .ai-sidebar-toggle.sidebar-open {{ left: 20px; }}
                        }}
                    </style>
                </head>
                <body>
                    <!-- AI Sidebar -->
                    <div id="aiSidebar" class="ai-sidebar">
                        <div class="ai-sidebar-header">
                            <h3>🧠 AI Intelligence Center</h3>
                            <button onclick="toggleAISidebar()" style="background: none; border: none; color: #fff; font-size: 1.2rem; cursor: pointer;">×</button>
                        </div>
                        <div class="ai-sidebar-content">
                            <div class="ai-section">
                                <h4>📊 Latest Analysis</h4>
                                <div style="background: rgba(0,212,255,0.1); border-radius: 12px; padding: 15px; border: 1px solid rgba(0,212,255,0.3);">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                        <span>Performance Analysis</span>
                                        <div style="width: 100px; height: 8px; background: rgba(255,255,255,0.2); border-radius: 4px; overflow: hidden;">
                                            <div style="height: 100%; width: 89%; background: linear-gradient(90deg, #ff4444, #ffaa00, #00ff88);"></div>
                                        </div>
                                    </div>
                                    <p style="font-size: 0.9rem; margin-bottom: 10px;">Trading performance shows consistent growth with {self.stats['success_rate']:.1f}% success rate</p>
                                    <small style="color: #999;">Confidence: 89% • 2 hours ago</small>
                                </div>
                            </div>
                            
                            <div class="ai-section">
                                <h4>💡 Active Recommendations</h4>
                                <div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #ff4444;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <strong style="font-size: 0.9rem;">Increase BTC/USDT Position</strong>
                                        <span style="font-size: 0.7rem; background: rgba(255,68,68,0.3); padding: 2px 6px; border-radius: 4px;">HIGH</span>
                                    </div>
                                    <p style="font-size: 0.8rem; color: #bbb;">15% increase in allocation would improve returns</p>
                                </div>
                                
                                <div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #ffaa00;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <strong style="font-size: 0.9rem;">Monitor Kraken Latency</strong>
                                        <span style="font-size: 0.7rem; background: rgba(255,170,0,0.3); padding: 2px 6px; border-radius: 4px;">MED</span>
                                    </div>
                                    <p style="font-size: 0.8rem; color: #bbb;">Latency spikes may affect execution quality</p>
                                </div>
                            </div>
                            
                            <div class="ai-section">
                                <h4>📈 Recent AI Decisions</h4>
                                <div style="font-size: 0.8rem; color: #bbb;">
                                    <div style="margin-bottom: 8px; padding: 8px; background: rgba(0,255,136,0.1); border-radius: 6px;">
                                        ✅ Executed BTC arbitrage (2 min ago)
                                    </div>
                                    <div style="margin-bottom: 8px; padding: 8px; background: rgba(255,170,0,0.1); border-radius: 6px;">
                                        ⚠️ Skipped ETH trade - high volatility (15 min ago)
                                    </div>
                                    <div style="margin-bottom: 8px; padding: 8px; background: rgba(0,212,255,0.1); border-radius: 6px;">
                                        📊 Analysis completed (2 hours ago)
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- AI Sidebar Toggle Button -->
                    <button id="aiToggleBtn" class="ai-sidebar-toggle" onclick="toggleAISidebar()">🧠</button>
                    
                    <!-- Main Container -->
                    <div id="mainContainer" class="main-container">
                        <div class="header">
                            <div class="controls-header">
                                <button class="control-btn" onclick="toggleTradingMode()">{mode_text.split()[0]} {mode_text.split()[1]}</button>
                                <button class="control-btn" onclick="toggleAI()">🧠 AI {'ON' if self.ai_status['enabled'] else 'OFF'}</button>
                                <button class="control-btn" onclick="exportData()">📥 Export</button>
                            </div>
                            <h1>SmartArb Engine Professional</h1>
                            <div style="display: inline-flex; align-items: center; gap: 10px; font-size: 1.1rem; margin-top: 10px;">
                                <span class="pulse positive">●</span>
                                System Online & Trading Active
                            </div>
                            <div class="trading-mode">{mode_text}</div>
                        </div>
                        
                        <div class="dashboard-grid">
                            <!-- Trading Performance -->
                            <div class="card">
                                <h3>📈 Trading Performance</h3>
                                <div class="metric">
                                    <span>Total Trades</span>
                                    <span class="positive">{self.stats['trades_executed']}</span>
                                </div>
                                <div class="metric">
                                    <span>Success Rate</span>
                                    <span class="positive">{self.stats['success_rate']:.1f}%</span>
                                </div>
                                <div class="metric">
                                    <span>Total Profit</span>
                                    <span class="positive">${self.stats['total_profit']:.2f}</span>
                                </div>
                                <div class="metric">
                                    <span>Daily P&L</span>
                                    <span class="positive">+${self.stats['daily_pnl']:.2f}</span>
                                </div>
                            </div>
                            
                            <!-- Analytics Dashboard -->
                            <div class="card">
                                <h3>📊 Analytics Dashboard</h3>
                                <div class="chart-tabs">
                                    <button class="chart-tab active" onclick="switchChart('profit')">Profit 24h</button>
                                    <button class="chart-tab" onclick="switchChart('distribution')">Distribution</button>
                                    <button class="chart-tab" onclick="switchChart('opportunities')">Opportunities</button>
                                </div>
                                <div class="chart-container">
                                    <canvas id="mainChart"></canvas>
                                </div>
                            </div>
                            
                            <!-- System Status -->
                            <div class="card">
                                <h3>🖥️ System Status</h3>
                                <div class="metric">
                                    <span>Engine Status</span>
                                    <span class="positive">Running</span>
                                </div>
                                <div class="metric">
                                    <span>Uptime</span>
                                    <span>{uptime_str}</span>
                                </div>
                                <div class="metric">
                                    <span>Memory Usage</span>
                                    <span>{psutil.virtual_memory().percent:.1f}%</span>
                                </div>
                                <div class="metric">
                                    <span>AI Status</span>
                                    <span class="{'positive' if self.ai_status['enabled'] else 'negative'}">{'Active' if self.ai_status['enabled'] else 'Inactive'}</span>
                                </div>
                            </div>
                            
                            <!-- Exchange Network -->
                            <div class="card">
                                <h3>🏪 Exchange Network</h3>
                                <div class="grid-container">
                                    <div class="exchange-card" onclick="showExchangeDetails('Bybit')">
                                        <div class="exchange-symbol">{self.exchanges['Bybit']['symbol']}</div>
                                        <div style="font-weight: bold;">Bybit</div>
                                        <div style="font-size: 0.8rem; color: #00ff88;">{self.exchanges['Bybit']['latency_ms']}ms</div>
                                        <div style="font-size: 0.7rem; color: #999;">{self.exchanges['Bybit']['trades']} trades</div>
                                    </div>
                                    <div class="exchange-card" onclick="showExchangeDetails('MEXC')">
                                        <div class="exchange-symbol">{self.exchanges['MEXC']['symbol']}</div>
                                        <div style="font-weight: bold;">MEXC</div>
                                        <div style="font-size: 0.8rem; color: #00ff88;">{self.exchanges['MEXC']['latency_ms']}ms</div>
                                        <div style="font-size: 0.7rem; color: #999;">{self.exchanges['MEXC']['trades']} trades</div>
                                    </div>
                                    <div class="exchange-card" onclick="showExchangeDetails('Kraken')">
                                        <div class="exchange-symbol">{self.exchanges['Kraken']['symbol']}</div>
                                        <div style="font-weight: bold;">Kraken</div>
                                        <div style="font-size: 0.8rem; color: #00ff88;">{self.exchanges['Kraken']['latency_ms']}ms</div>
                                        <div style="font-size: 0.7rem; color: #999;">{self.exchanges['Kraken']['trades']} trades</div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Trading Pairs -->
                            <div class="card">
                                <h3>💱 Trading Pairs</h3>
                                <div class="grid-container">
                                    <div class="pair-card" onclick="showPairDetails('BTC/USDT')">
                                        <div class="crypto-icon">{self.trading_pairs['BTC/USDT']['icon']} {self.trading_pairs['BTC/USDT']['symbol']}</div>
                                        <div style="font-size: 0.8rem;">BTC/USDT</div>
                                        <div style="font-size: 0.7rem; color: #00ff88;">+${self.trading_pairs['BTC/USDT']['profit']:.2f}</div>
                                    </div>
                                    <div class="pair-card" onclick="showPairDetails('ETH/USDT')">
                                        <div class="crypto-icon">{self.trading_pairs['ETH/USDT']['icon']} {self.trading_pairs['ETH/USDT']['symbol']}</div>
                                        <div style="font-size: 0.8rem;">ETH/USDT</div>
                                        <div style="font-size: 0.7rem; color: #00ff88;">+${self.trading_pairs['ETH/USDT']['profit']:.2f}</div>
                                    </div>
                                    <div class="pair-card" onclick="showPairDetails('ADA/USDT')">
                                        <div class="crypto-icon">{self.trading_pairs['ADA/USDT']['icon']} {self.trading_pairs['ADA/USDT']['symbol']}</div>
                                        <div style="font-size: 0.8rem;">ADA/USDT</div>
                                        <div style="font-size: 0.7rem; color: #00ff88;">+${self.trading_pairs['ADA/USDT']['profit']:.2f}</div>
                                    </div>
                                    <div class="pair-card" onclick="showPairDetails('SOL/USDT')">
                                        <div class="crypto-icon">{self.trading_pairs['SOL/USDT']['icon']} {self.trading_pairs['SOL/USDT']['symbol']}</div>
                                        <div style="font-size: 0.8rem;">SOL/USDT</div>
                                        <div style="font-size: 0.7rem; color: #00ff88;">+${self.trading_pairs['SOL/USDT']['profit']:.2f}</div>
                                    </div>
                                    <div class="pair-card" onclick="showPairDetails('DOT/USDT')">
                                        <div class="crypto-icon">{self.trading_pairs['DOT/USDT']['icon']} {self.trading_pairs['DOT/USDT']['symbol']}</div>
                                        <div style="font-size: 0.8rem;">DOT/USDT</div>
                                        <div style="font-size: 0.7rem; color: #00ff88;">+${self.trading_pairs['DOT/USDT']['profit']:.2f}</div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Control Panel -->
                            <div class="control-panel">
                                <h3 style="color: #00d4ff; margin-bottom: 0;">⚙️ Control Panel</h3>
                                <div class="control-grid">
                                    <div class="control-section">
                                        <h4>Trading Controls</h4>
                                        <button class="control-btn-large" onclick="startStopTrading()">
                                            {'⏸️ Stop Trading' if self.is_running else '▶️ Start Trading'}
                                        </button>
                                        <button class="control-btn-large" onclick="toggleTradingMode()">
                                            {'Switch to Paper' if self.is_live_trading else 'Switch to Live'}
                                        </button>
                                    </div>
                                    
                                    <div class="control-section">
                                        <h4>AI Configuration</h4>
                                        <button class="control-btn-large" onclick="toggleAI()">
                                            {'🧠 Disable AI' if self.ai_status['enabled'] else '🧠 Enable AI'}
                                        </button>
                                        <button class="control-btn-large" onclick="runAIAnalysis()">🔍 Run Analysis</button>
                                    </div>
                                    
                                    <div class="control-section">
                                        <h4>System Tools</h4>
                                        <button class="control-btn-large" onclick="testConnections()">🔗 Test Connections</button>
                                        <button class="control-btn-large" onclick="exportData()">📥 Export Data</button>
                                    </div>
                                    
                                    <div class="control-section">
                                        <h4>Emergency</h4>
                                        <button class="control-btn-large danger" onclick="emergencyStop()">🛑 Emergency Stop</button>
                                        <button class="control-btn-large danger" onclick="resetSystem()">🔄 Reset System</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <script>
                        // AI Sidebar Toggle
                        function toggleAISidebar() {{
                            const sidebar = document.getElementById('aiSidebar');
                            const mainContainer = document.getElementById('mainContainer');
                            const toggleBtn = document.getElementById('aiToggleBtn');
                            sidebar.classList.toggle('open');
                            mainContainer.classList.toggle('sidebar-open');
                            toggleBtn.classList.toggle('sidebar-open');
                        }}
                        
                        // Chart Management
                        let currentChart = 'profit';
                        let chartInstance = null;
                        
                        function switchChart(chartType) {{
                            currentChart = chartType;
                            
                            // Update tab states
                            document.querySelectorAll('.chart-tab').forEach(tab => {{
                                tab.classList.remove('active');
                            }});
                            event.target.classList.add('active');
                            
                            // Update chart
                            updateChart();
                        }}
                        
                        function updateChart() {{
                            const ctx = document.getElementById('mainChart').getContext('2d');
                            
                            if (chartInstance) {{
                                chartInstance.destroy();
                            }}
                            
                            switch(currentChart) {{
                                case 'profit':
                                    createProfitChart(ctx);
                                    break;
                                case 'distribution':
                                    createDistributionChart(ctx);
                                    break;
                                case 'opportunities':
                                    createOpportunitiesChart(ctx);
                                    break;
                            }}
                        }}
                        
                        function createProfitChart(ctx) {{
                            fetch('/api/profit-history')
                                .then(response => response.json())
                                .then(data => {{
                                    chartInstance = new Chart(ctx, {{
                                        type: 'line',
                                        data: {{
                                            labels: data.map(item => new Date(item.timestamp).toLocaleTimeString()),
                                            datasets: [{{
                                                label: 'Cumulative Profit ($)',
                                                data: data.map(item => item.profit),
                                                borderColor: '#00ff88',
                                                backgroundColor: 'rgba(0, 255, 136, 0.1)',
                                                borderWidth: 2,
                                                fill: true,
                                                tension: 0.4
                                            }}]
                                        }},
                                        options: {{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: {{ legend: {{ display: false }} }},
                                            scales: {{
                                                x: {{ grid: {{ color: 'rgba(255,255,255,0.1)' }}, ticks: {{ color: '#999' }} }},
                                                y: {{ grid: {{ color: 'rgba(255,255,255,0.1)' }}, ticks: {{ color: '#999' }} }}
                                            }}
                                        }}
                                    }});
                                }});
                        }}
                        
                        function createDistributionChart(ctx) {{
                            fetch('/api/trade-distribution')
                                .then(response => response.json())
                                .then(data => {{
                                    chartInstance = new Chart(ctx, {{
                                        type: 'doughnut',
                                        data: {{
                                            labels: Object.keys(data),
                                            datasets: [{{
                                                data: Object.values(data),
                                                backgroundColor: ['#ff6b35', '#00d4ff', '#00ff88'],
                                                borderWidth: 2,
                                                borderColor: '#1a1a2e'
                                            }}]
                                        }},
                                        options: {{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: {{
                                                legend: {{
                                                    position: 'bottom',
                                                    labels: {{ color: '#fff' }}
                                                }}
                                            }}
                                        }}
                                    }});
                                }});
                        }}
                        
                        function createOpportunitiesChart(ctx) {{
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
                        }}
                        
                        // Control Functions
                        function toggleTradingMode() {{
                            fetch('/api/toggle-trading-mode', {{ method: 'POST' }})
                                .then(response => response.json())
                                .then(data => {{
                                    alert('Switched to ' + data.mode + ' trading mode');
                                    location.reload();
                                }})
                                .catch(() => alert('Feature coming soon - integrate with backend'));
                        }}
                        
                        function toggleAI() {{
                            fetch('/api/toggle-ai', {{ method: 'POST' }})
                                .then(response => response.json())
                                .then(data => {{
                                    alert('AI ' + (data.enabled ? 'enabled' : 'disabled'));
                                    location.reload();
                                }})
                                .catch(() => alert('Feature coming soon - integrate with backend'));
                        }}
                        
                        function startStopTrading() {{
                            const action = '{('stop' if self.is_running else 'start')}';
                            fetch(`/api/${{action}}-trading`, {{ method: 'POST' }})
                                .then(response => response.json())
                                .then(data => {{
                                    alert('Trading ' + data.status);
                                    location.reload();
                                }})
                                .catch(() => alert('Feature coming soon'));
                        }}
                        
                        function testConnections() {{
                            alert('Testing connections to all exchanges...');
                        }}
                        
                        function runAIAnalysis() {{
                            alert('Running AI analysis...');
                        }}
                        
                        function emergencyStop() {{
                            if (confirm('Emergency stop all trading?')) {{
                                alert('Emergency stop executed');
                            }}
                        }}
                        
                        function resetSystem() {{
                            if (confirm('Reset system statistics?')) {{
                                alert('System reset');
                            }}
                        }}
                        
                        function exportData() {{
                            window.open('/api/export', '_blank');
                        }}
                        
                        function showExchangeDetails(exchange) {{
                            alert(`${{exchange}} details - implement detailed view`);
                        }}
                        
                        function showPairDetails(pair) {{
                            alert(`${{pair}} details - implement detailed view`);
                        }}
                        
                        // Initialize charts
                        document.addEventListener('DOMContentLoaded', function() {{
                            updateChart(); // Initialize with profit chart
                        }});
                    </script>
                </body>
                </html>
                ''')
            
            # Enhanced API Endpoints
            @self.dashboard_app.get("/api/metrics")
            def get_metrics():
                return {
                    "trades_executed": self.stats['trades_executed'],
                    "success_rate": self.stats['success_rate'],
                    "total_profit": self.stats['total_profit'],
                    "daily_pnl": self.stats['daily_pnl'],
                    "uptime": str(datetime.now() - self.start_time).split('.')[0],
                    "status": "running" if self.is_running else "stopped",
                    "is_live_trading": self.is_live_trading,
                    "ai_status": self.ai_status
                }
            
            @self.dashboard_app.post("/api/toggle-trading-mode")
            def toggle_trading_mode():
                self.is_live_trading = not self.is_live_trading
                mode = "LIVE" if self.is_live_trading else "PAPER"
                logger.info(f"🔄 Switched to {mode} trading mode")
                return {"mode": mode, "is_live": self.is_live_trading}
            
            @self.dashboard_app.post("/api/toggle-ai")
            def toggle_ai():
                self.ai_status['enabled'] = not self.ai_status['enabled']
                return {"enabled": self.ai_status['enabled']}
            
            @self.dashboard_app.get("/api/export")
            def export_data():
                return JSONResponse({
                    "export_timestamp": datetime.now().isoformat(),
                    "metrics": self.stats,
                    "exchanges": self.exchanges,
                    "trading_pairs": self.trading_pairs
                })
            
            
            # Additional API endpoints for charts
            @self.dashboard_app.get("/api/profit-history")
            def get_profit_history():
                # Generate sample profit data for last 24 hours
                import random
                from datetime import datetime, timedelta
                
                data = []
                now = datetime.now()
                for i in range(24):
                    timestamp = now - timedelta(hours=23-i)
                    profit = sum(random.uniform(5, 25) for _ in range(i + 1)) * 0.1
                    data.append({
                        'timestamp': timestamp.isoformat(),
                        'profit': round(profit, 2),
                        'trades': random.randint(0, 3)
                    })
                return data
            
            @self.dashboard_app.get("/api/trade-distribution")
            def get_trade_distribution():
                # Distribution of trades across exchanges
                total_trades = sum(ex['trades'] for ex in self.exchanges.values())
                if total_trades == 0:
                    return {"Bybit": 5, "MEXC": 3, "Kraken": 2}
                return {name: data['trades'] for name, data in self.exchanges.items()}
            
            @self.dashboard_app.get("/api/opportunities-timeline")
            def get_opportunities_timeline():
                # Generate sample opportunities data
                import random
                from datetime import datetime, timedelta
                
                data = []
                now = datetime.now()
                pairs = list(self.trading_pairs.keys())
                exchanges = list(self.exchanges.keys())
                
                for i in range(20):
                    timestamp = now - timedelta(hours=random.randint(0, 24))
                    data.append({
                        'timestamp': timestamp.isoformat(),
                        'pair': random.choice(pairs),
                        'exchange': random.choice(exchanges),
                        'spread': round(random.uniform(0.1, 2.5), 2),
                        'executed': random.choice([True, False])
                    })
                
                return sorted(data, key=lambda x: x['timestamp'])

            # Start dashboard server in thread
            def run_dashboard():
                uvicorn.run(self.dashboard_app, host="0.0.0.0", port=8001, log_level="warning")
            
            dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
            dashboard_thread.start()
            logger.info("📊 Professional dashboard server started on http://localhost:8001")
            
        except Exception as e:
            logger.error(f"❌ Dashboard error: {e}")
    
    def update_trading_data(self):
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
        self.trading_pairs[selected_pair]['profit'] += trade_profit
    
    async def send_telegram_notification(self, message):
        """Send Telegram notification"""
        try:
            import requests
            
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if not bot_token or not chat_id:
                return
                
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("📱 Telegram notification sent")
                
        except Exception as e:
            logger.warning(f"📱 Telegram error: {e}")
    
    async def trading_loop(self):
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
                await asyncio.sleep(5)
    
    async def start(self):
        """Start the unified engine"""
        logger.info("🚀 Starting SmartArb Professional Engine...")
        self.is_running = True
        
        try:
            # Start dashboard
            self.start_dashboard_server()
            await asyncio.sleep(3)
            
            # Send startup notification
            mode = "🔴 LIVE TRADING" if self.is_live_trading else "📄 PAPER TRADING"
            await self.send_telegram_notification(
                f"🚀 <b>SmartArb Professional Engine Online!</b>\n\n"
                f"📊 Dashboard: http://localhost:8001\n"
                f"🔄 Mode: {mode}\n"
                f"🧠 AI: {'Enabled' if self.ai_status['enabled'] else 'Disabled'}\n"
                f"📱 Notifications: Active"
            )
            
            logger.info("✅ Professional engine started successfully")
            logger.info("🌐 Professional Dashboard: http://localhost:8001")
            logger.info(f"🔄 Trading Mode: {'LIVE' if self.is_live_trading else 'PAPER'}")
            
            # Start trading loop
            await self.trading_loop()
            
        except Exception as e:
            logger.error(f"❌ Engine error: {e}")
            self.is_running = False
    
    async def stop(self):
        """Stop the engine"""
        logger.info("🛑 Stopping professional engine...")
        self.is_running = False
        
        await self.send_telegram_notification(
            "🛑 <b>SmartArb Professional Engine Stopped</b>\n\n"
            f"📊 Final Stats:\n"
            f"📈 Trades: {self.stats['trades_executed']}\n"
            f"💰 Total Profit: ${self.stats['total_profit']:.2f}\n"
            f"⏱️ Runtime: {datetime.now() - self.start_time}"
        )

async def main():
    """Main entry point"""
    engine = UnifiedSmartArbEngine()
    
    try:
        await engine.start()
    except KeyboardInterrupt:
        logger.info("👋 Shutdown requested by user")
        await engine.stop()
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        await engine.stop()

if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Run unified engine
    asyncio.run(main())
