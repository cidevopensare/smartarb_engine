#!/bin/bash
# fix_yaml_config.sh - Risolve il file YAML corrotto

echo "🔧 SmartArb Engine - Fix YAML Configuration"
echo "==========================================="

# Backup del file corrotto
echo "📋 Creating backup of corrupted config..."
cp config/settings.yaml config/settings.yaml.corrupted.bak

# Verifica errore YAML
echo "🔍 Checking YAML syntax error..."
python3 -c "
import yaml
try:
    with open('config/settings.yaml', 'r') as f:
        yaml.safe_load(f)
    print('✅ YAML is valid')
except yaml.YAMLError as e:
    print(f'❌ YAML Error: {e}')
    print('Line:', getattr(e, 'problem_mark', 'Unknown'))
" 2>/dev/null || echo "⚠️ Cannot check YAML, will recreate"

echo ""
echo "🛠️ Creating new valid config/settings.yaml..."

# Crea nuovo file YAML valido basato sui logs
cat > config/settings.yaml << 'EOF'
# SmartArb Engine Configuration
# Auto-generated fixed configuration

app:
  name: "SmartArb Engine"
  version: "1.0.0"
  mode: "paper"  # paper or live
  debug: false

# Exchange Configuration
exchanges:
  kraken:
    enabled: true
    name: "Kraken"
    testnet: false
    
  bybit:
    enabled: true 
    name: "Bybit"
    testnet: false
    
  mexc:
    enabled: true
    name: "MEXC"
    testnet: false

# Strategy Configuration
strategies:
  spatial_arbitrage:
    enabled: true
    name: "Spatial Arbitrage"
    min_profit_threshold: 0.5  # %
    max_position_size: 1000    # USDT
    
# Risk Management
risk_management:
  enabled: true
  max_position_size: 1000      # USDT per trade
  max_daily_loss: 200          # USDT
  max_drawdown: 500            # USDT
  min_profit_threshold: 0.20   # %
  emergency_stop: true

# Telegram Configuration
telegram:
  enabled: true
  min_profit_threshold: 25.0   # USD
  max_notifications_per_hour: 15
  status_report_interval: 1800  # seconds
  error_notifications: true

# Logging Configuration  
logging:
  level: "INFO"
  file_enabled: true
  console_enabled: true
  max_file_size: 10485760  # 10MB
  backup_count: 5

# Database Configuration (if used)
database:
  enabled: false
  
# AI Configuration (if used)
ai:
  enabled: false
  analysis_frequency: "daily"
  auto_apply_safe_changes: false

# System Configuration
system:
  health_check_interval: 60    # seconds
  status_report_interval: 1800 # seconds
  cleanup_interval: 3600       # seconds
EOF

echo "✅ New config/settings.yaml created successfully!"

# Test nuovo file YAML
echo ""
echo "🧪 Testing new YAML configuration..."
python3 -c "
import yaml
try:
    with open('config/settings.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print('✅ New YAML is valid!')
    print(f'📊 Config sections: {list(config.keys())}')
    print(f'🔗 Exchanges: {list(config.get(\"exchanges\", {}).keys())}')
    print(f'🎯 Strategies: {list(config.get(\"strategies\", {}).keys())}')
except Exception as e:
    print(f'❌ YAML still invalid: {e}')
"

echo ""
echo "🎯 Configuration fixed! Now try:"
echo "   make start"
echo ""
echo "📋 Backup of corrupted file: config/settings.yaml.corrupted.bak"
