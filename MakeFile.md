# SmartArb Engine Makefile
# Automation for development, testing, and deployment tasks

# Configuration
PYTHON := python3.11
PIP := $(PYTHON) -m pip
VENV_DIR := venv
PROJECT_NAME := smartarb-engine
DOCKER_IMAGE := smartarb/engine
VERSION := $(shell grep -E '^__version__' src/__init__.py | cut -d'"' -f2 2>/dev/null || echo "1.0.0")

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

# Help target
.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)SmartArb Engine Development Tasks$(NC)"
	@echo ""
	@echo "$(YELLOW)Usage:$(NC) make [target]"
	@echo ""
	@echo "$(YELLOW)Available targets:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Environment setup
.PHONY: install
install: ## Install project dependencies
	@echo "$(BLUE)Installing SmartArb Engine dependencies...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip setuptools wheel
	$(VENV_DIR)/bin/pip install -r requirements.txt
	$(VENV_DIR)/bin/pip install -e .
	@echo "$(GREEN)Dependencies installed successfully!$(NC)"

.PHONY: install-dev
install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(VENV_DIR)/bin/pip install -r requirements.txt
	$(VENV_DIR)/bin/pip install pytest pytest-asyncio pytest-mock pytest-cov
	$(VENV_DIR)/bin/pip install black flake8 mypy pre-commit
	$(VENV_DIR)/bin/pip install sphinx sphinx-rtd-theme
	$(VENV_DIR)/bin/pip install -e .
	@echo "$(GREEN)Development dependencies installed!$(NC)"

.PHONY: install-rpi
install-rpi: ## Install Raspberry Pi specific dependencies
	@echo "$(BLUE)Installing Raspberry Pi dependencies...$(NC)"
	$(VENV_DIR)/bin/pip install RPi.GPIO gpiozero
	sudo apt-get update
	sudo apt-get install -y python3-dev python3-pip
	@echo "$(GREEN)Raspberry Pi dependencies installed!$(NC)"

# Virtual environment
.PHONY: venv
venv: ## Create virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip
	@echo "$(GREEN)Virtual environment created!$(NC)"

.PHONY: venv-clean
venv-clean: ## Remove virtual environment
	@echo "$(BLUE)Removing virtual environment...$(NC)"
	rm -rf $(VENV_DIR)
	@echo "$(GREEN)Virtual environment removed!$(NC)"

# Code quality
.PHONY: format
format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	$(VENV_DIR)/bin/black --line-length 100 src/ tests/ scripts/
	@echo "$(GREEN)Code formatting completed!$(NC)"

.PHONY: lint
lint: ## Lint code with flake8
	@echo "$(BLUE)Linting code...$(NC)"
	$(VENV_DIR)/bin/flake8 --max-line-length=100 --ignore=E203,W503,E501 src/ tests/ scripts/
	@echo "$(GREEN)Code linting completed!$(NC)"

.PHONY: type-check
type-check: ## Type check with mypy
	@echo "$(BLUE)Type checking...$(NC)"
	$(VENV_DIR)/bin/mypy --ignore-missing-imports src/
	@echo "$(GREEN)Type checking completed!$(NC)"

.PHONY: quality
quality: format lint type-check ## Run all code quality checks
	@echo "$(GREEN)All quality checks completed!$(NC)"

# Testing
.PHONY: test
test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(VENV_DIR)/bin/pytest tests/ -v
	@echo "$(GREEN)Tests completed!$(NC)"

.PHONY: test-cov
test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(VENV_DIR)/bin/pytest tests/ -v --cov=src --cov-report=html --cov-report=term
	@echo "$(GREEN)Tests with coverage completed!$(NC)"
	@echo "$(YELLOW)Coverage report available at htmlcov/index.html$(NC)"

.PHONY: test-fast
test-fast: ## Run fast tests only
	@echo "$(BLUE)Running fast tests...$(NC)"
	$(VENV_DIR)/bin/pytest tests/ -v -m "not slow"
	@echo "$(GREEN)Fast tests completed!$(NC)"

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(VENV_DIR)/bin/pytest tests/integration/ -v
	@echo "$(GREEN)Integration tests completed!$(NC)"

# Security
.PHONY: security-check
security-check: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	$(VENV_DIR)/bin/bandit -r src/ --format json -o security-report.json
	$(VENV_DIR)/bin/safety check --json --output safety-report.json
	@echo "$(GREEN)Security checks completed!$(NC)"

# Documentation
.PHONY: docs
docs: ## Build documentation
	@echo "$(BLUE)Building documentation...$(NC)"
	cd docs && $(VENV_DIR)/bin/sphinx-build -b html . _build/html
	@echo "$(GREEN)Documentation built!$(NC)"
	@echo "$(YELLOW)Documentation available at docs/_build/html/index.html$(NC)"

.PHONY: docs-clean
docs-clean: ## Clean documentation
	@echo "$(BLUE)Cleaning documentation...$(NC)"
	cd docs && rm -rf _build/
	@echo "$(GREEN)Documentation cleaned!$(NC)"

.PHONY: docs-serve
docs-serve: docs ## Serve documentation locally
	@echo "$(BLUE)Serving documentation...$(NC)"
	cd docs/_build/html && $(PYTHON) -m http.server 8080
	@echo "$(YELLOW)Documentation available at http://localhost:8080$(NC)"

# Database
.PHONY: db-init
db-init: ## Initialize database
	@echo "$(BLUE)Initializing database...$(NC)"
	$(VENV_DIR)/bin/python scripts/setup_database.py --init
	@echo "$(GREEN)Database initialized!$(NC)"

.PHONY: db-migrate
db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(VENV_DIR)/bin/python scripts/setup_database.py --migrate
	@echo "$(GREEN)Database migrations completed!$(NC)"

.PHONY: db-reset
db-reset: ## Reset database (WARNING: destroys data)
	@echo "$(RED)WARNING: This will destroy all data!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	$(VENV_DIR)/bin/python scripts/setup_database.py --reset
	@echo "$(GREEN)Database reset completed!$(NC)"

# Configuration
.PHONY: config-check
config-check: ## Validate configuration
	@echo "$(BLUE)Checking configuration...$(NC)"
	$(VENV_DIR)/bin/python -m src.utils.config --validate
	@echo "$(GREEN)Configuration check completed!$(NC)"

.PHONY: config-example
config-example: ## Create example configuration
	@echo "$(BLUE)Creating example configuration...$(NC)"
	cp .env.example .env
	cp config/settings.yaml.example config/settings.yaml 2>/dev/null || true
	@echo "$(GREEN)Example configuration created!$(NC)"
	@echo "$(YELLOW)Edit .env and config/settings.yaml with your settings$(NC)"

# Development server
.PHONY: dev
dev: ## Start development server
	@echo "$(BLUE)Starting SmartArb Engine in development mode...$(NC)"
	$(VENV_DIR)/bin/python -m src.core.engine --debug

.PHONY: dev-api
dev-api: ## Start API development server
	@echo "$(BLUE)Starting API development server...$(NC)"
	$(VENV_DIR)/bin/python -m src.api.rest_api --debug

.PHONY: dev-cli
dev-cli: ## Start CLI interface
	@echo "$(BLUE)Starting CLI interface...$(NC)"
	$(VENV_DIR)/bin/python -m src.cli.main

# Docker
.PHONY: docker-build
docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t $(DOCKER_IMAGE):$(VERSION) .
	docker tag $(DOCKER_IMAGE):$(VERSION) $(DOCKER_IMAGE):latest
	@echo "$(GREEN)Docker image built: $(DOCKER_IMAGE):$(VERSION)$(NC)"

.PHONY: docker-run
docker-run: ## Run Docker container
	@echo "$(BLUE)Running Docker container...$(NC)"
	docker run -it --rm \
		-p 8000:8000 \
		-v $(PWD)/config:/app/config \
		-v $(PWD)/logs:/app/logs \
		-v $(PWD)/data:/app/data \
		--env-file .env \
		$(DOCKER_IMAGE):latest

.PHONY: docker-dev
docker-dev: ## Run Docker container in development mode
	@echo "$(BLUE)Running Docker container (development)...$(NC)"
	docker run -it --rm \
		-p 8000:8000 \
		-v $(PWD):/app \
		--env-file .env \
		-e DEBUG_MODE=true \
		$(DOCKER_IMAGE):latest

.PHONY: docker-compose-up
docker-compose-up: ## Start with docker-compose
	@echo "$(BLUE)Starting with docker-compose...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started!$(NC)"
	@echo "$(YELLOW)Check status: docker-compose ps$(NC)"

.PHONY: docker-compose-down
docker-compose-down: ## Stop docker-compose services
	@echo "$(BLUE)Stopping docker-compose services...$(NC)"
	docker-compose down
	@echo "$(GREEN)Services stopped!$(NC)"

.PHONY: docker-compose-logs
docker-compose-logs: ## Show docker-compose logs
	docker-compose logs -f

# Raspberry Pi deployment
.PHONY: rpi-setup
rpi-setup: ## Setup Raspberry Pi environment
	@echo "$(BLUE)Setting up Raspberry Pi environment...$(NC)"
	bash scripts/raspberry_pi_setup.sh
	@echo "$(GREEN)Raspberry Pi setup completed!$(NC)"

.PHONY: rpi-deploy
rpi-deploy: ## Deploy to Raspberry Pi
	@echo "$(BLUE)Deploying to Raspberry Pi...$(NC)"
	@read -p "Enter Raspberry Pi IP: " rpi_ip; \
	rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' \
		. pi@$$rpi_ip:/home/pi/smartarb-engine/
	@echo "$(GREEN)Deployment completed!$(NC)"

.PHONY: rpi-service-install
rpi-service-install: ## Install systemd service on Raspberry Pi
	@echo "$(BLUE)Installing systemd service...$(NC)"
	sudo cp scripts/smartarb.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable smartarb
	@echo "$(GREEN)Service installed!$(NC)"

.PHONY: rpi-service-start
rpi-service-start: ## Start systemd service
	@echo "$(BLUE)Starting SmartArb service...$(NC)"
	sudo systemctl start smartarb
	sudo systemctl status smartarb
	@echo "$(GREEN)Service started!$(NC)"

.PHONY: rpi-service-stop
rpi-service-stop: ## Stop systemd service
	@echo "$(BLUE)Stopping SmartArb service...$(NC)"
	sudo systemctl stop smartarb
	@echo "$(GREEN)Service stopped!$(NC)"

.PHONY: rpi-service-logs
rpi-service-logs: ## Show service logs
	sudo journalctl -u smartarb -f

# Monitoring and logs
.PHONY: logs
logs: ## Show application logs
	@echo "$(BLUE)Showing application logs...$(NC)"
	tail -f logs/main.log

.PHONY: logs-error
logs-error: ## Show error logs
	@echo "$(BLUE)Showing error logs...$(NC)"
	tail -f logs/error.log

.PHONY: logs-trading
logs-trading: ## Show trading logs
	@echo "$(BLUE)Showing trading logs...$(NC)"
	tail -f logs/trading.log

.PHONY: status
status: ## Show system status
	@echo "$(BLUE)SmartArb Engine Status:$(NC)"
	$(VENV_DIR)/bin/python -m src.cli.main status

.PHONY: monitor
monitor: ## Start monitoring dashboard
	@echo "$(BLUE)Starting monitoring dashboard...$(NC)"
	$(VENV_DIR)/bin/python -m src.monitoring.dashboard

# Performance
.PHONY: profile
profile: ## Profile application performance
	@echo "$(BLUE)Profiling application...$(NC)"
	$(VENV_DIR)/bin/python -m cProfile -o performance.prof -m src.core.engine
	@echo "$(GREEN)Performance profiling completed!$(NC)"
	@echo "$(YELLOW)Results in performance.prof$(NC)"

# Release
.PHONY: release-check
release-check: quality test-cov security-check ## Run all release checks
	@echo "$(GREEN)All release checks passed!$(NC)"

.PHONY: build
build: ## Build distribution packages
	@echo "$(BLUE)Building distribution packages...$(NC)"
	$(VENV_DIR)/bin/python setup.py sdist bdist_wheel
	@echo "$(GREEN)Build completed!$(NC)"

.PHONY: version
version: ## Show version information
	@echo "$(BLUE)SmartArb Engine v$(VERSION)$(NC)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Git: $(shell git describe --tags --dirty 2>/dev/null || echo 'no git info')"

# AI Integration
.PHONY: ai-test
ai-test: ## Test AI integration
	@echo "$(BLUE)Testing AI integration...$(NC)"
	$(VENV_DIR)/bin/python -m src.ai.test_integration
	@echo "$(GREEN)AI integration test completed!$(NC)"

.PHONY: ai-analyze
ai-analyze: ## Run AI analysis
	@echo "$(BLUE)Running AI analysis...$(NC)"
	$(VENV_DIR)/bin/python -m src.ai.analysis_engine --analyze
	@echo "$(GREEN)AI analysis completed!$(NC)"

.PHONY: ai-setup
ai-setup: ## Setup AI system
	@echo "$(BLUE)Setting up AI system...$(NC)"
	$(VENV_DIR)/bin/python scripts/setup_ai.py
	@echo "$(GREEN)AI setup completed!$(NC)"

# Utilities
.PHONY: requirements-update
requirements-update: ## Update requirements.txt
	@echo "$(BLUE)Updating requirements.txt...$(NC)"
	$(VENV_DIR)/bin/pip freeze > requirements.txt
	@echo "$(GREEN)Requirements updated!$(NC)"

.PHONY: pre-commit
pre-commit: ## Setup pre-commit hooks
	@echo "$(BLUE)Setting up pre-commit hooks...$(NC)"
	$(VENV_DIR)/bin/pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed!$(NC)"

.PHONY: clean
clean: ## Clean build artifacts and cache
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "$(GREEN)Clean completed!$(NC)"

.PHONY: clean-all
clean-all: clean venv-clean docs-clean ## Clean everything
	@echo "$(BLUE)Cleaning everything...$(NC)"
	rm -rf logs/ data/ *.prof *.json
	@echo "$(GREEN)Deep clean completed!$(NC)"

# System info
.PHONY: system-info
system-info: ## Show system information
	@echo "$(BLUE)System Information:$(NC)"
	@echo "OS: $(shell uname -s)"
	@echo "Architecture: $(shell uname -m)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Current directory: $(PWD)"
	@echo "Memory: $(shell free -h 2>/dev/null | awk '/^Mem:/ {print $$2}' || echo 'N/A')"
	@echo "Disk space: $(shell df -h . | tail -1 | awk '{print $$4}' || echo 'N/A')"

# Backup and restore
.PHONY: backup
backup: ## Create backup of configuration and data
	@echo "$(BLUE)Creating backup...$(NC)"
	tar -czf backup-$(shell date +%Y%m%d_%H%M%S).tar.gz \
		config/ data/ logs/ .env 2>/dev/null || true
	@echo "$(GREEN)Backup created!$(NC)"

.PHONY: restore
restore: ## Restore from backup
	@echo "$(BLUE)Available backups:$(NC)"
	@ls -la backup-*.tar.gz 2>/dev/null || echo "No backups found"
	@read -p "Enter backup filename: " backup_file; \
	tar -xzf $$backup_file
	@echo "$(GREEN)Restore completed!$(NC)"

# Quick shortcuts
.PHONY: start
start: dev ## Alias for dev

.PHONY: stop
stop: ## Stop all running processes
	@echo "$(BLUE)Stopping all processes...$(NC)"
	pkill -f "smartarb" || true
	@echo "$(GREEN)Processes stopped!$(NC)"

.PHONY: restart
restart: stop start ## Restart the engine

.PHONY: check
check: quality test-fast ## Quick check (format, lint, fast tests)

.PHONY: full-check
full-check: quality test-cov security-check ## Full check (all quality and tests)
