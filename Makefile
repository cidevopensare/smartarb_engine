# SmartArb Engine Makefile - Gestione Automatica Virtual Environment
# Usage: make start, make stop, make status, make test

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

# Paths
VENV := venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip3
ENGINE_PID := .engine.pid
DASHBOARD_PID := .dashboard.pid

# Default target
.DEFAULT_GOAL := help

# Setup virtual environment and dependencies
$(VENV)/bin/python3:
	@echo "$(BLUE)📦 Creating virtual environment...$(NC)"
	python3 -m venv $(VENV)
	@echo "$(BLUE)📦 Installing dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install fastapi uvicorn psutil websockets requests aiofiles
	@echo "$(GREEN)✅ Virtual environment ready$(NC)"

# Install/update dependencies
.PHONY: install
install: $(VENV)/bin/python3 ## Setup virtual environment and install dependencies

# Create required directories
.PHONY: setup-dirs
setup-dirs:
	@mkdir -p logs static/dashboard src/api config

# Start SmartArb Engine
.PHONY: start-engine
start-engine: install setup-dirs
	@if [ -f $(ENGINE_PID) ] && ps -p $$(cat $(ENGINE_PID)) > /dev/null 2>&1; then \
		echo "$(YELLOW)⚠️ Engine already running (PID: $$(cat $(ENGINE_PID)))$(NC)"; \
	else \
		echo "$(GREEN)🤖 Starting SmartArb Engine...$(NC)"; \
		$(PYTHON) src/core/unified_engine.py > logs/engine.log 2>&1 & \
		echo $$! > $(ENGINE_PID); \
		echo "$(GREEN)✅ Engine started (PID: $$(cat $(ENGINE_PID)))$(NC)"; \
	fi

# Start Dashboard
.PHONY: start-dashboard
start-dashboard: install setup-dirs
	@if [ -f $(DASHBOARD_PID) ] && ps -p $$(cat $(DASHBOARD_PID)) > /dev/null 2>&1; then \
		echo "$(YELLOW)⚠️ Dashboard already running (PID: $$(cat $(DASHBOARD_PID)))$(NC)"; \
	else \
		echo "$(GREEN)📊 Starting Dashboard...$(NC)"; \
		# $(PYTHON) src/api/dashboard_server.py # Now integrated in unified engine > logs/dashboard.log 2>&1 & \
		echo $$! > $(DASHBOARD_PID); \
		echo "$(GREEN)✅ Dashboard started (PID: $$(cat $(DASHBOARD_PID)))$(NC)"; \
		echo "$(GREEN)🌐 Dashboard available at: http://localhost:8001$(NC)"; \
	fi

# Start both engine and dashboard
.PHONY: start
start: start-engine start-dashboard ## Start SmartArb Engine and Dashboard
	@sleep 3
	@echo ""
	@echo "$(GREEN)🎉 SmartArb Engine is running!$(NC)"
	@echo "$(GREEN)🌐 Dashboard: http://localhost:8001$(NC)"
	@echo "$(GREEN)📋 Logs: make logs$(NC)"
	@echo "$(GREEN)🛑 Stop: make stop$(NC)"

# Stop Engine
.PHONY: stop-engine
stop-engine:
	@if [ -f $(ENGINE_PID) ]; then \
		if ps -p $$(cat $(ENGINE_PID)) > /dev/null 2>&1; then \
			kill $$(cat $(ENGINE_PID)) 2>/dev/null || true; \
			echo "$(YELLOW)🛑 Engine stopped$(NC)"; \
		fi; \
		rm -f $(ENGINE_PID); \
	fi
	@pkill -f "src.core.engine" 2>/dev/null || true

# Stop Dashboard
.PHONY: stop-dashboard
stop-dashboard:
	@if [ -f $(DASHBOARD_PID) ]; then \
		if ps -p $$(cat $(DASHBOARD_PID)) > /dev/null 2>&1; then \
			kill $$(cat $(DASHBOARD_PID)) 2>/dev/null || true; \
			echo "$(YELLOW)🛑 Dashboard stopped$(NC)"; \
		fi; \
		rm -f $(DASHBOARD_PID); \
	fi
	@pkill -f "dashboard_server.py" 2>/dev/null || true

# Stop both services
.PHONY: stop
stop: stop-engine stop-dashboard ## Stop SmartArb Engine and Dashboard
	@echo "$(GREEN)✅ All SmartArb services stopped$(NC)"

# Restart both services
.PHONY: restart
restart: stop start ## Restart SmartArb Engine and Dashboard

# Check status of services
.PHONY: status
status: ## Check status of SmartArb services
	@echo "$(BLUE)📊 SmartArb Engine Status:$(NC)"
	@if [ -f $(ENGINE_PID) ] && ps -p $$(cat $(ENGINE_PID)) > /dev/null 2>&1; then \
		echo "$(GREEN)  ✅ Engine: Running (PID: $$(cat $(ENGINE_PID)))$(NC)"; \
	else \
		echo "$(RED)  ❌ Engine: Not running$(NC)"; \
	fi
	@if [ -f $(DASHBOARD_PID) ] && ps -p $$(cat $(DASHBOARD_PID)) > /dev/null 2>&1; then \
		echo "$(GREEN)  ✅ Dashboard: Running (PID: $$(cat $(DASHBOARD_PID)))$(NC)"; \
	else \
		echo "$(RED)  ❌ Dashboard: Not running$(NC)"; \
	fi
	@echo ""
	@echo "$(BLUE)🔌 Port Status:$(NC)"
	@if curl -s http://localhost:8001/api/metrics > /dev/null; then \
		echo "$(GREEN)  ✅ Port 8001: Dashboard responding$(NC)"; \
	else \
		echo "$(RED)  ❌ Port 8001: No response$(NC)"; \
	fi
	@echo ""
	@echo "$(BLUE)💻 System Resources:$(NC)"
	@$(PYTHON) -c "import psutil; print('  🖥️  CPU: {:.1f}%'.format(psutil.cpu_percent())); print('  🧠 RAM: {:.1f}%'.format(psutil.virtual_memory().percent)); print('  💾 Disk: {:.1f}%'.format(psutil.disk_usage('.').percent))" 2>/dev/null || echo "  ⚠️ psutil not available for system stats"

# Show recent logs
.PHONY: logs
logs: ## Show recent logs from engine and dashboard
	@echo "$(BLUE)📋 Recent SmartArb Logs:$(NC)"
	@echo ""
	@echo "$(YELLOW)--- Engine Logs (last 10 lines) ---$(NC)"
	@tail -10 logs/engine.log 2>/dev/null || tail -10 logs/smartarb.log 2>/dev/null || echo "No engine logs found"
	@echo ""
	@echo "$(YELLOW)--- Dashboard Logs (last 10 lines) ---$(NC)"
	@tail -10 logs/dashboard.log 2>/dev/null || echo "No dashboard logs found"

# Follow logs in real-time
.PHONY: logs-live
logs-live: ## Follow logs in real-time
	@echo "$(BLUE)📋 Following SmartArb logs in real-time (Ctrl+C to stop)...$(NC)"
	@tail -f logs/engine.log logs/dashboard.log logs/smartarb.log 2>/dev/null || tail -f logs/*.log 2>/dev/null || echo "No log files found"

# Run system tests
.PHONY: test
test: install ## Run complete system tests
	@echo "$(BLUE)🧪 Running SmartArb system tests...$(NC)"
	@$(PYTHON) tests/test_system_complete.py

# Test Telegram notifications
.PHONY: test-telegram
test-telegram: install ## Test Telegram notifications
	@echo "$(BLUE)📱 Testing Telegram notifications...$(NC)"
	@$(PYTHON) test_telegram_direct.py

# Open dashboard in browser
.PHONY: dashboard
dashboard: ## Open dashboard in browser
	@echo "$(BLUE)🌐 Opening dashboard in browser...$(NC)"
	@if command -v firefox > /dev/null; then \
		firefox http://localhost:8001 2>/dev/null & \
	elif command -v chromium-browser > /dev/null; then \
		chromium-browser http://localhost:8001 2>/dev/null & \
	elif command -v google-chrome > /dev/null; then \
		google-chrome http://localhost:8001 2>/dev/null & \
	else \
		echo "$(YELLOW)⚠️ No browser found. Open manually: http://localhost:8001$(NC)"; \
	fi

# Quick API test
.PHONY: api-test
api-test: ## Test dashboard API
	@echo "$(BLUE)📊 Testing Dashboard API...$(NC)"
	@curl -s http://localhost:8001/api/metrics | python3 -m json.tool 2>/dev/null || echo "$(RED)❌ Dashboard API not responding$(NC)"

# Clean up logs and temp files
.PHONY: clean-logs
clean-logs: ## Clean up log files
	@echo "$(YELLOW)🧹 Cleaning up logs...$(NC)"
	@rm -f logs/*.log
	@echo "$(GREEN)✅ Logs cleaned$(NC)"

# Development mode with verbose logging
.PHONY: dev
dev: install setup-dirs ## Start in development mode with verbose logging
	@echo "$(BLUE)🔧 Starting SmartArb in development mode...$(NC)"
	@$(PYTHON) src/core/unified_engine.py &
	@sleep 3
	@# $(PYTHON) src/api/dashboard_server.py # Now integrated in unified engine &
	@echo "$(GREEN)✅ Development mode started$(NC)"
	@echo "$(GREEN)📋 Following logs (Ctrl+C to stop):$(NC)"
	@sleep 2
	@make logs-live

# Paper trading mode (default)
.PHONY: paper
paper: start ## Start in paper trading mode
	@echo "$(GREEN)📝 SmartArb running in PAPER TRADING mode$(NC)"

# Complete system health check
.PHONY: health
health: install ## Complete system health check
	@echo "$(BLUE)🏥 SmartArb Health Check$(NC)"
	@echo "========================"
	@make status
	@echo ""
	@make api-test
	@echo ""
	@$(PYTHON) test_telegram_direct.py > /dev/null 2>&1 && echo "$(GREEN)✅ Telegram: OK$(NC)" || echo "$(RED)❌ Telegram: Failed$(NC)"

# Show system info
.PHONY: info
info: install ## Show system information
	@echo "$(BLUE)ℹ️  SmartArb System Information$(NC)"
	@echo "================================"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Virtual Environment: $(VENV)"
	@echo "Dashboard URL: http://localhost:8001"
	@echo "Engine PID file: $(ENGINE_PID)"
	@echo "Dashboard PID file: $(DASHBOARD_PID)"
	@echo ""
	@echo "$(BLUE)📁 Directory structure:$(NC)"
	@ls -la | head -10
	@echo ""
	@echo "$(BLUE)📋 Log files:$(NC)"
	@ls -la logs/ 2>/dev/null || echo "No logs directory"

# Quick start - stops everything and starts fresh
.PHONY: quick-start
quick-start: stop start ## Quick restart - stop everything and start fresh

# Emergency stop - kill everything forcefully
.PHONY: kill
kill: ## Emergency stop - forcefully kill all SmartArb processes
	@echo "$(RED)🚨 Emergency stop - killing all SmartArb processes...$(NC)"
	@pkill -9 -f "smartarb" 2>/dev/null || true
	@pkill -9 -f "src.core.engine" 2>/dev/null || true
	@pkill -9 -f "dashboard_server" 2>/dev/null || true
	@rm -f $(ENGINE_PID) $(DASHBOARD_PID)
	@echo "$(GREEN)✅ All processes terminated$(NC)"

# Help - show all available commands
.PHONY: help
help: ## Show this help message
	@echo "$(GREEN)🚀 SmartArb Engine - Available Commands$(NC)"
	@echo "========================================"
	@echo ""
	@echo "$(YELLOW)📊 Main Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(start|stop|restart|status)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)  make %-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)🔍 Monitoring & Testing:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(logs|test|dashboard|health)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)  make %-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)🛠️ Utility Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -vE "(start|stop|restart|status|logs|test|dashboard|health)" | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)  make %-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Quick start: make start$(NC)"
	@echo "$(GREEN)Check status: make status$(NC)"
	@echo "$(GREEN)View dashboard: make dashboard$(NC)"
	@echo "$(GREEN)Stop everything: make stop$(NC)"

# Make sure intermediate files aren't deleted
.PRECIOUS: $(VENV)/bin/python3
