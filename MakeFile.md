# SmartArb Engine Makefile
# Automation for development, testing, and deployment tasks

# Configuration
PYTHON := python3.11
PIP := $(PYTHON) -m pip
VENV_DIR := venv
PROJECT_NAME := smartarb-engine
DOCKER_IMAGE := smartarb/engine
VERSION := $(shell grep -E '^__version__' src/__init__.py | cut -d'"' -f2)

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

.PHONY: venv
venv: ## Create virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "$(GREEN)Virtual environment created!$(NC)"
	@echo "$(YELLOW)Activate with: source $(VENV_DIR)/bin/activate$(NC)"

# Code quality
.PHONY: format
format: ## Format code with black
	@echo "$(BLUE)Formatting code with black...$(NC)"
	$(VENV_DIR)/bin/black src/ tests/ scripts/
	@echo "$(GREEN)Code formatted!$(NC)"

.PHONY: lint
lint: ## Run linting with flake8
	@echo "$(BLUE)Running flake8 linting...$(NC)"
	$(VENV_DIR)/bin/flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503
	@echo "$(GREEN)Linting completed!$(NC)"

.PHONY: type-check
type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running mypy type checking...$(NC)"
	$(VENV_DIR)/bin/mypy src/ --ignore-missing-imports
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
	@echo "$(YELLOW)Coverage report: htmlcov/index.html$(NC)"

.PHONY: test-fast
test-fast: ## Run fast tests only
	@echo "$(BLUE)Running fast tests...$(NC)"
	$(VENV_DIR)/bin/pytest tests/ -v -m "not slow"
	@echo "$(GREEN)Fast tests completed!$(NC)"

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(VENV_DIR)/bin/pytest tests/ -v -m "integration"
	@echo "$(GREEN)Integration tests completed!$(NC)"

# Database
.PHONY: db-setup
db-setup: ## Setup database
	@echo "$(BLUE)Setting up database...$(NC)"
	$(VENV_DIR)/bin/python scripts/setup_database.py
	@echo "$(GREEN)Database setup completed!$(NC)"

.PHONY: db-migrate
db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(VENV_DIR)/bin/alembic upgrade head
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
	@echo "$(GREEN)Services started! Check docker-compose logs$(NC)"

.PHONY: docker-compose-down
docker-compose-down: ## Stop docker-compose services
	@echo "$(BLUE)Stopping docker-compose services...$(NC)"
	docker-compose down
	@echo "$(GREEN)Services stopped!$(NC)"

.PHONY: docker-compose-logs
docker-compose-logs: ## Show docker-compose logs
	docker-compose logs -f

# Deployment
.PHONY: deploy-rpi
deploy-rpi: ## Deploy to Raspberry Pi
	@echo "$(BLUE)Deploying to Raspberry Pi...$(NC)"
	@if [ -z "$(RPI_HOST)" ]; then \
		echo "$(RED)Error: RPI_HOST not set$(NC)"; \
		echo "$(YELLOW)Usage: make deploy-rpi RPI_HOST=pi@192.168.1.100$(NC)"; \
		exit 1; \
	fi
	rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' \
		./ $(RPI_HOST):/opt/smartarb/smartarb-engine/
	ssh $(RPI_HOST) 'cd /opt/smartarb/smartarb-engine && sudo systemctl restart smartarb'
	@echo "$(GREEN)Deployment completed!$(NC)"

.PHONY: setup-rpi
setup-rpi: ## Setup Raspberry Pi environment
	@echo "$(BLUE)Setting up Raspberry Pi environment...$(NC)"
	@if [ -z "$(RPI_HOST)" ]; then \
		echo "$(RED)Error: RPI_HOST not set$(NC)"; \
		echo "$(YELLOW)Usage: make setup-rpi RPI_HOST=pi@192.168.1.100$(NC)"; \
		exit 1; \
	fi
	scp scripts/raspberry_pi_setup.sh $(RPI_HOST):/tmp/
	ssh $(RPI_HOST) 'chmod +x /tmp/raspberry_pi_setup.sh && /tmp/raspberry_pi_setup.sh'
	@echo "$(GREEN)Raspberry Pi setup completed!$(NC)"

# Monitoring
.PHONY: logs
logs: ## Show live logs
	@echo "$(BLUE)Showing live logs...$(NC)"
	tail -f logs/smartarb.log

.PHONY: logs-error
logs-error: ## Show error logs
	@echo "$(BLUE)Showing error logs...$(NC)"
	tail -f logs/errors.log

.PHONY: status
status: ## Show system status
	@echo "$(BLUE)SmartArb Engine Status:$(NC)"
	@if command -v systemctl >/dev/null 2>&1; then \
		systemctl is-active smartarb || echo "$(YELLOW)Service not running$(NC)"; \
	fi
	@if [ -f logs/smartarb.log ]; then \
		echo "$(GREEN)Last log entries:$(NC)"; \
		tail -5 logs/smartarb.log; \
	fi

# Maintenance
.PHONY: backup
backup: ## Create backup
	@echo "$(BLUE)Creating backup...$(NC)"
	$(VENV_DIR)/bin/python scripts/backup_restore.py backup
	@echo "$(GREEN)Backup completed!$(NC)"

.PHONY: backup-list
backup-list: ## List available backups
	@echo "$(BLUE)Available backups:$(NC)"
	$(VENV_DIR)/bin/python scripts/backup_restore.py list

.PHONY: clean
clean: ## Clean temporary files
	@echo "$(BLUE)Cleaning temporary files...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/
	@echo "$(GREEN)Cleanup completed!$(NC)"

.PHONY: clean-all
clean-all: clean ## Clean everything including venv
	@echo "$(BLUE)Cleaning everything...$(NC)"
	rm -rf $(VENV_DIR)/
	@echo "$(GREEN)Deep cleanup completed!$(NC)"

# Documentation
.PHONY: docs
docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	cd docs && $(VENV_DIR)/bin/sphinx-build -b html . _build/html
	@echo "$(GREEN)Documentation generated!$(NC)"
	@echo "$(YELLOW)Open docs/_build/html/index.html$(NC)"

.PHONY: docs-serve
docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation...$(NC)"
	cd docs/_build/html && python -m http.server 8080
	@echo "$(YELLOW)Documentation available at http://localhost:8080$(NC)"

# Security
.PHONY: security-check
security-check: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	$(VENV_DIR)/bin/pip install safety bandit
	$(VENV_DIR)/bin/safety check
	$(VENV_DIR)/bin/bandit -r src/
	@echo "$(GREEN)Security checks completed!$(NC)"

# Performance
.PHONY: profile
profile: ## Run performance profiling
	@echo "$(BLUE)Running performance profiling...$(NC)"
	$(VENV_DIR)/bin/python -m cProfile -o performance.prof scripts/profile_engine.py
	@echo "$(GREEN)Profiling completed! Results in performance.prof$(NC)"

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

# Raspberry Pi specific
.PHONY: rpi-info
rpi-info: ## Show Raspberry Pi information
	@echo "$(BLUE)Raspberry Pi Information:$(NC)"
	@if [ -f /proc/cpuinfo ]; then \
		echo "Model: $(shell grep 'Model' /proc/cpuinfo | cut -d: -f2 | sed 's/^ *//')"; \
		echo "CPU: $(shell grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | sed 's/^ *//')"; \
	fi
	@if [ -f /sys/class/thermal/thermal_zone0/temp ]; then \
		echo "Temperature: $(shell awk '{print $$1/1000 "°C"}' /sys/class/thermal/thermal_zone0/temp)"; \
	fi
	@if command -v vcgencmd >/dev/null 2>&1; then \
		echo "GPU Memory: $(shell vcgencmd get_mem gpu)"; \
		echo "ARM Memory: $(shell vcgencmd get_mem arm)"; \
	fi

# Help for specific targets
.PHONY: help-docker
help-docker: ## Show Docker help
	@echo "$(BLUE)Docker Commands:$(NC)"
	@echo "  $(GREEN)make docker-build$(NC)     - Build Docker image"
	@echo "  $(GREEN)make docker-run$(NC)       - Run Docker container"
	@echo "  $(GREEN)make docker-dev$(NC)       - Run development container"
	@echo "  $(GREEN)make docker-compose-up$(NC) - Start all services"

.PHONY: help-deploy
help-deploy: ## Show deployment help
	@echo "$(BLUE)Deployment Commands:$(NC)"
	@echo "  $(GREEN)make setup-rpi RPI_HOST=pi@IP$(NC)   - Setup Raspberry Pi"
	@echo "  $(GREEN)make deploy-rpi RPI_HOST=pi@IP$(NC)  - Deploy to Raspberry Pi"
	@echo ""
	@echo "$(YELLOW)Example:$(NC)"
	@echo "  make setup-rpi RPI_HOST=pi@192.168.1.100"
	@echo "  make deploy-rpi RPI_HOST=pi@192.168.1.100"

# Check if running on Raspberry Pi
.PHONY: check-rpi
check-rpi:
	@if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then \
		echo "$(GREEN)Running on Raspberry Pi$(NC)"; \
	else \
		echo "$(YELLOW)Not running on Raspberry Pi$(NC)"; \
	fi
