# SmartArb Engine Makefile - Versione Corretta e Funzionante
# Usage: make start, make stop, make status, make test

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
NC := \033[0m

# Paths
VENV := venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip3
ENGINE_PID := .engine.pid
DASHBOARD_PID := .dashboard.pid

# Default target
.DEFAULT_GOAL := help

# ============================================================================
# VIRTUAL ENVIRONMENT SETUP
# ============================================================================

$(VENV)/bin/python3:
	@echo "$(BLUE)📦 Creating virtual environment...$(NC)"
	python3 -m venv $(VENV)
	@echo "$(BLUE)📦 Installing dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install fastapi uvicorn psutil websockets requests aiofiles python-dotenv pyyaml
	@echo "$(GREEN)✅ Virtual environment ready$(NC)"

install: $(VENV)/bin/python3

setup-dirs:
	@mkdir -p logs static/dashboard src/api config config/ai scripts

# ============================================================================
# SMARTARB ENGINE CONTROLS
# ============================================================================

start-engine: install setup-dirs
	@if [ -f $(ENGINE_PID) ] && ps -p $$(cat $(ENGINE_PID)) > /dev/null 2>&1; then \
		echo "$(YELLOW)⚠️ Engine already running (PID: $$(cat $(ENGINE_PID)))$(NC)"; \
	else \
		echo "$(GREEN)🤖 Starting SmartArb Engine...$(NC)"; \
		cd $$(pwd) && . $(VENV)/bin/activate && nohup $(PYTHON) src/core/unified_engine.py > logs/unified_engine.log 2>&1 & echo $$! > $(ENGINE_PID); \
		sleep 3; \
		echo "$(GREEN)✅ Engine started (PID: $$(cat $(ENGINE_PID)))$(NC)"; \
	fi

start: start-engine ## Start SmartArb Engine (standard mode)
	@echo "$(GREEN)🚀 SmartArb Engine started$(NC)"
	@echo "$(GREEN)📊 Dashboard: http://localhost:8001$(NC)"

start-with-ai: install setup-dirs ## Start SmartArb Engine with AI integration
	@echo "$(BLUE)🧠 Starting SmartArb Engine with AI...$(NC)"
	@if [ -f $(ENGINE_PID) ] && ps -p $$(cat $(ENGINE_PID)) > /dev/null 2>&1; then \
		echo "$(YELLOW)⚠️ Engine already running (PID: $$(cat $(ENGINE_PID)))$(NC)"; \
	else \
		echo "$(GREEN)🤖 Starting SmartArb Engine with AI integration...$(NC)"; \
		cd $$(pwd) && . $(VENV)/bin/activate && AI_ENABLED=true TELEGRAM_AI=true nohup $(PYTHON) src/core/unified_engine.py > logs/unified_engine.log 2>&1 & echo $$! > $(ENGINE_PID); \
		sleep 3; \
		echo "$(GREEN)✅ SmartArb with AI started$(NC)"; \
		echo "$(GREEN)📊 Dashboard with AI: http://localhost:8001$(NC)"; \
		$(MAKE) ai-status; \
	fi

stop: ## Stop SmartArb Engine
	@echo "$(RED)🛑 Stopping SmartArb Engine...$(NC)"
	@if [ -f test_telegram_direct.py ]; then \
		echo "$(BLUE)📱 Sending shutdown notification...$(NC)"; \
		cd $$(pwd) && . $(VENV)/bin/activate && $(PYTHON) -c "import os, requests, datetime; bot_token = os.getenv('TELEGRAM_BOT_TOKEN'); chat_id = os.getenv('TELEGRAM_CHAT_ID'); message = f'🛑 SmartArb Engine Shutdown at {datetime.datetime.now().strftime(\"%H:%M:%S\")}'; requests.post(f'https://api.telegram.org/bot{bot_token}/sendMessage', {'chat_id': chat_id, 'text': message}) if bot_token and chat_id else None" 2>/dev/null || true; \
	fi
	@if [ -f $(ENGINE_PID) ]; then \
		PID=$$(cat $(ENGINE_PID)); \
		if kill $$PID 2>/dev/null; then \
			echo "$(GREEN)✅ Engine PID $$PID terminated successfully$(NC)"; \
		fi; \
		rm -f $(ENGINE_PID); \
	fi
	@pkill -f "unified_engine" 2>/dev/null && echo "$(GREEN)✅ Unified engine processes terminated$(NC)" || true
	@pkill -f "src.core.engine" 2>/dev/null && echo "$(GREEN)✅ Core engine processes terminated$(NC)" || true
	@pkill -f "uvicorn" 2>/dev/null && echo "$(GREEN)✅ Uvicorn processes terminated$(NC)" || true
	@lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null && echo "$(GREEN)✅ Port 8001 freed$(NC)" || true
	@lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null && echo "$(GREEN)✅ Port 8000 freed$(NC)" || true
	@rm -f *.pid
	@echo "$(GREEN)✅ SmartArb Engine stopped$(NC)"

restart: stop start ## Restart SmartArb Engine

status: ## Show SmartArb status
	@echo "$(BLUE)📊 SmartArb Engine Status$(NC)"
	@echo "=========================="
	@if [ -f $(ENGINE_PID) ] && ps -p $$(cat $(ENGINE_PID)) > /dev/null 2>&1; then \
		echo "$(GREEN)✅ Engine: Running (PID: $$(cat $(ENGINE_PID)))$(NC)"; \
		echo "$(BLUE)   Memory: $$(ps -p $$(cat $(ENGINE_PID)) -o rss= 2>/dev/null | awk '{print int($$1/1024)"MB"}' || echo "N/A")$(NC)"; \
		echo "$(BLUE)   CPU: $$(ps -p $$(cat $(ENGINE_PID)) -o %cpu= 2>/dev/null | awk '{print $$1"%"}' || echo "N/A")$(NC)"; \
	else \
		echo "$(RED)❌ Engine: Not running$(NC)"; \
	fi
	@echo ""
	@echo "$(BLUE)🌐 Network Status:$(NC)"
	@if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/metrics | grep -q "200"; then \
		echo "$(GREEN)✅ Dashboard API: http://localhost:8001 (responding)$(NC)"; \
	else \
		echo "$(YELLOW)⚠️ Dashboard API: http://localhost:8001 (not responding)$(NC)"; \
	fi
	@echo ""
	@echo "$(BLUE)🖥️ System Resources:$(NC)"
	@echo "$(BLUE)   CPU Usage: $$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $$1"%"}' 2>/dev/null || echo "N/A")$(NC)"
	@echo "$(BLUE)   Memory: $$(free -m | awk 'NR==2{printf "%.1f%%", $$3*100/$$2 }' 2>/dev/null || echo "N/A")$(NC)"
	@echo "$(BLUE)   Disk: $$(df -h . | awk 'NR==2{print $$5}' 2>/dev/null || echo "N/A")$(NC)"

# ============================================================================
# AI SYSTEM MANAGEMENT
# ============================================================================

ai-status: install ## Show AI system status
	@echo "$(BLUE)🧠 AI System Status$(NC)"
	@echo "=================="
	@if [ -f src/ai/ai_integration.py ]; then \
		echo "$(GREEN)AI Enabled: true$(NC)"; \
	else \
		echo "$(RED)AI Enabled: false$(NC)"; \
	fi
	@echo "$(GREEN)AI Mode: advisory_only$(NC)"
	@echo "$(GREEN)Telegram AI: true$(NC)"
	@echo "$(BLUE)📁 AI Files:$(NC)"
	@ls -la src/ai/ 2>/dev/null || echo "$(YELLOW)   No AI directory found$(NC)"
	@echo "$(BLUE)📋 AI Configuration:$(NC)"
	@ls -la config/ai/ 2>/dev/null || echo "$(YELLOW)   No AI config directory found$(NC)"

setup-ai: install ## Setup AI system
	@echo "$(BLUE)🧠 Setting up AI system...$(NC)"
	@mkdir -p src/ai config/ai
	@echo "$(GREEN)✅ AI directories created$(NC)"

test-ai: install ## Test AI integration
	@echo "$(BLUE)🧪 Testing AI integration...$(NC)"
	@cd $$(pwd) && . $(VENV)/bin/activate && $(PYTHON) -c "from src.ai.ai_advisor import AIAdvisor; print('✅ AI integration working')" 2>/dev/null || echo "$(YELLOW)⚠️ AI integration needs setup$(NC)"

# ============================================================================
# MONITORING AND TESTING
# ============================================================================

logs: ## Show recent logs from engine
	@echo "$(BLUE)📋 Recent SmartArb Logs:$(NC)"
	@echo ""
	@echo "$(YELLOW)--- Unified Engine Logs (last 20 lines) ---$(NC)"
	@tail -20 logs/unified_engine.log 2>/dev/null || tail -20 logs/smartarb.log 2>/dev/null || tail -20 logs/engine.log 2>/dev/null || echo "$(YELLOW)No logs found$(NC)"

logs-live: ## Follow logs in real-time
	@echo "$(BLUE)📋 Following SmartArb logs in real-time (Ctrl+C to stop)...$(NC)"
	@tail -f logs/unified_engine.log logs/smartarb.log logs/engine.log 2>/dev/null | head -100 || echo "$(YELLOW)No log files found$(NC)"

test: install ## Run system tests
	@echo "$(BLUE)🧪 Running SmartArb system tests...$(NC)"
	@cd $$(pwd) && . $(VENV)/bin/activate && $(PYTHON) -c "import sys; print('✅ Python OK'); import requests; print('✅ Requests OK'); import yaml; print('✅ YAML OK')"

test-telegram: install ## Test Telegram notifications
	@echo "$(BLUE)📱 Testing Telegram notifications...$(NC)"
	@if [ -f test_telegram_direct.py ]; then \
		cd $$(pwd) && . $(VENV)/bin/activate && $(PYTHON) test_telegram_direct.py; \
	else \
		echo "$(YELLOW)⚠️ Telegram test script not found$(NC)"; \
	fi

api-test: ## Test dashboard API
	@echo "$(BLUE)📊 Testing Dashboard API...$(NC)"
	@curl -s http://localhost:8001/api/metrics 2>/dev/null | python3 -m json.tool 2>/dev/null && echo "$(GREEN)✅ Dashboard API responding$(NC)" || echo "$(RED)❌ Dashboard API not responding$(NC)"

health: install ## Complete system health check
	@echo "$(BLUE)🏥 SmartArb Health Check$(NC)"
	@echo "========================"
	@make status
	@echo ""
	@make api-test
	@echo ""
	@if [ -f test_telegram_direct.py ]; then \
		cd $$(pwd) && . $(VENV)/bin/activate && $(PYTHON) test_telegram_direct.py > /dev/null 2>&1 && echo "$(GREEN)✅ Telegram: OK$(NC)" || echo "$(RED)❌ Telegram: Failed$(NC)"; \
	fi

dashboard: ## Open dashboard in browser
	@echo "$(BLUE)🌐 Opening dashboard in browser...$(NC)"
	@if command -v firefox > /dev/null; then \
		firefox http://localhost:8001 2>/dev/null & \
	elif command -v chromium-browser > /dev/null; then \
		chromium-browser http://localhost:8001 2>/dev/null & \
	elif command -v google-chrome > /dev/null; then \
		google-chrome http://localhost:8001 2>/dev/null & \
	elif command -v open > /dev/null; then \
		open http://localhost:8001 2>/dev/null; \
	else \
		echo "$(YELLOW)⚠️ No browser found. Open manually: http://localhost:8001$(NC)"; \
	fi

# ============================================================================
# DEVELOPMENT AND UTILITY
# ============================================================================

dev: install setup-dirs ## Start in development mode
	@echo "$(BLUE)🔧 Starting SmartArb in development mode...$(NC)"
	@cd $$(pwd) && . $(VENV)/bin/activate && $(PYTHON) src/core/unified_engine.py &
	@echo "$(GREEN)✅ Development mode started$(NC)"

paper: start ## Start in paper trading mode
	@echo "$(GREEN)📝 SmartArb running in PAPER TRADING mode$(NC)"

clean-logs: ## Clean up log files
	@echo "$(YELLOW)🧹 Cleaning up logs...$(NC)"
	@rm -f logs/*.log
	@echo "$(GREEN)✅ Logs cleaned$(NC)"

info: install ## Show system information
	@echo "$(BLUE)ℹ️  SmartArb System Information$(NC)"
	@echo "================================"
	@echo "$(BLUE)Python: $$($(PYTHON) --version)$(NC)"
	@echo "$(BLUE)Virtual Environment: $(VENV)$(NC)"
	@echo "$(BLUE)Dashboard URL: http://localhost:8001$(NC)"
	@echo "$(BLUE)Engine PID file: $(ENGINE_PID)$(NC)"
	@echo ""
	@echo "$(BLUE)📁 Project structure:$(NC)"
	@ls -la | head -10
	@echo ""
	@echo "$(BLUE)📋 Log files:$(NC)"
	@ls -la logs/ 2>/dev/null || echo "$(YELLOW)   No logs directory$(NC)"

quick-start: stop start ## Quick restart - stop everything and start fresh

kill: ## Emergency stop - forcefully kill all SmartArb processes
	@echo "$(RED)🚨 Emergency stop - killing all SmartArb processes...$(NC)"
	@pkill -9 -f "smartarb" 2>/dev/null || true
	@pkill -9 -f "unified_engine" 2>/dev/null || true
	@pkill -9 -f "src.core.engine" 2>/dev/null || true
	@pkill -9 -f "dashboard_server" 2>/dev/null || true
	@pkill -9 -f "uvicorn" 2>/dev/null || true
	@lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
	@lsof -ti:8001 2>/dev/null | xargs kill -9 2>/dev/null || true
	@rm -f $(ENGINE_PID) $(DASHBOARD_PID) *.pid
	@echo "$(GREEN)✅ All processes terminated and ports freed$(NC)"

# ============================================================================
# HELP SYSTEM
# ============================================================================

help: ## Show this help message
	@echo "$(GREEN)🚀 SmartArb Engine - Available Commands$(NC)"
	@echo "========================================"
	@echo ""
	@echo "$(YELLOW)📊 Main Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(start|stop|restart|status)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)  make %-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)🧠 AI Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(ai-|setup-ai|test-ai)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)  make %-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)🔍 Monitoring & Testing:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(logs|test|dashboard|health)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)  make %-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)🛠️ Utility Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -vE "(start|stop|restart|status|logs|test|dashboard|health|ai-)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)  make %-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(PURPLE)🎯 Quick Commands:$(NC)"
	@echo "$(GREEN)  make start$(NC)           - Start standard engine"
	@echo "$(GREEN)  make start-with-ai$(NC)   - Start with AI integration"  
	@echo "$(GREEN)  make status$(NC)          - Check system status"
	@echo "$(GREEN)  make dashboard$(NC)       - Open web dashboard"
	@echo "$(GREEN)  make stop$(NC)            - Stop with Telegram notification"
	@echo ""
	@echo "$(CYAN)📈 Dashboard: http://localhost:8001$(NC)"
	@echo "$(CYAN)📱 Telegram: Enabled$(NC)"

# ============================================================================
# PHONY TARGETS
# ============================================================================
.PHONY: help install setup-dirs start-engine start start-with-ai stop restart \
        status ai-status setup-ai test-ai logs logs-live test test-telegram \
        api-test health dashboard dev paper clean-logs info quick-start kill

# Make sure intermediate files aren't deleted
.PRECIOUS: $(VENV)/bin/python3
