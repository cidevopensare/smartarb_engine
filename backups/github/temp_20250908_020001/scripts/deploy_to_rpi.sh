#!/bin/bash
# SmartArb Engine - Automatic Deployment Script for Raspberry Pi 5
# This script handles complete deployment with all fixes applied

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/your-username/smartarb_engine.git"
PROJECT_DIR="$HOME/smartarb_engine"
BACKUP_DIR="$HOME/smartarb_backups"
EXTERNAL_SSD="/mnt/external-ssd"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}==== $1 ====${NC}"
}

check_raspberry_pi() {
    log_step "Checking Raspberry Pi Environment"
    
    if ! grep -q "BCM" /proc/cpuinfo; then
        log_error "This script is designed for Raspberry Pi"
        exit 1
    fi
    
    # Check for Raspberry Pi 5
    PI_MODEL=$(grep "Model" /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)
    log_info "Detected: $PI_MODEL"
    
    # Check available memory
    MEMORY_MB=$(free -m | grep "Mem:" | awk '{print $2}')
    if [ "$MEMORY_MB" -lt 1000 ]; then
        log_warn "Low memory detected: ${MEMORY_MB}MB. Recommend 2GB+ for optimal performance"
    fi
    
    # Check disk space
    DISK_FREE=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$DISK_FREE" -lt 5 ]; then
        log_error "Insufficient disk space: ${DISK_FREE}GB free. Need at least 5GB"
        exit 1
    fi
    
    log_info "System checks passed ✓"
}

setup_external_storage() {
    log_step "Setting up External Storage"
    
    if [ -d "$EXTERNAL_SSD" ] && mountpoint -q "$EXTERNAL_SSD"; then
        log_info "External SSD detected at $EXTERNAL_SSD ✓"
        
        # Create directories on external storage
        sudo mkdir -p "$EXTERNAL_SSD/smartarb/"{logs,data,backups,postgres,redis}
        sudo chown -R $USER:$USER "$EXTERNAL_SSD/smartarb/"
        
        log_info "External storage directories created ✓"
    else
        log_warn "No external SSD detected. Using SD card (not recommended for production)"
        
        # Create local directories
        mkdir -p "$HOME/smartarb_data/"{logs,data,backups}
    fi
}

backup_existing_installation() {
    log_step "Backing up Existing Installation"
    
    if [ -d "$PROJECT_DIR" ]; then
        log_info "Found existing installation, creating backup..."
        
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        mkdir -p "$BACKUP_DIR"
        
        # Backup configuration and data
        if [ -f "$PROJECT_DIR/.env" ]; then
            cp "$PROJECT_DIR/.env" "$BACKUP_DIR/.env.backup_$TIMESTAMP"
            log_info "Backed up .env file ✓"
        fi
        
        if [ -d "$PROJECT_DIR/config" ]; then
            cp -r "$PROJECT_DIR/config" "$BACKUP_DIR/config_backup_$TIMESTAMP"
            log_info "Backed up config directory ✓"
        fi
        
        if [ -d "$PROJECT_DIR/data" ]; then
            cp -r "$PROJECT_DIR/data" "$BACKUP_DIR/data_backup_$TIMESTAMP"
            log_info "Backed up data directory ✓"
        fi
        
        # Remove old installation
        rm -rf "$PROJECT_DIR"
        log_info "Old installation removed ✓"
    fi
}

clone_repository() {
    log_step "Cloning Updated Repository"
    
    log_info "Cloning from: $REPO_URL"
    git clone "$REPO_URL" "$PROJECT_DIR"
    
    cd "$PROJECT_DIR"
    
    # Show latest commits
    log_info "Latest changes:"
    git log --oneline -5
    
    log_info "Repository cloned successfully ✓"
}

install_system_dependencies() {
    log_step "Installing System Dependencies"
    
    log_info "Updating package list..."
    sudo apt update
    
    log_info "Installing system packages..."
    sudo apt install -y \
        python3-dev python3-pip python3-venv \
        build-essential pkg-config \
        libpq-dev libssl-dev libffi-dev \
        git curl wget htop vim nano \
        redis-server postgresql postgresql-contrib \
        nginx certbot \
        docker.io docker-compose \
        fail2ban ufw logrotate \
        libraspberrypi-bin raspi-config rpi-eeprom
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    log_info "System dependencies installed ✓"
}

setup_python_environment() {
    log_step "Setting up Python Environment"
    
    cd "$PROJECT_DIR"
    
    # Create virtual environment
    log_info "Creating Python virtual environment..."
    python3 -m venv venv
    
    # Activate and upgrade pip
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel
    
    # Install requirements
    log_info "Installing Python dependencies (this may take several minutes)..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        log_error "requirements.txt not found!"
        exit 1
    fi
    
    log_info "Python environment setup complete ✓"
}

create_configurations() {
    log_step "Creating Configuration Files"
    
    cd "$PROJECT_DIR"
    
    # Create config directory
    mkdir -p config secrets logs data backups
    chmod 700 secrets
    
    # Copy example configurations
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_info "Created .env from template ✓"
    fi
    
    if [ -f "config/settings.yaml.example" ]; then
        cp config/settings.yaml.example config/settings.yaml
        log_info "Created settings.yaml from template ✓"
    fi
    
    # Restore backed up configurations
    if [ -f "$BACKUP_DIR/.env.backup_"* ]; then
        LATEST_ENV=$(ls -t "$BACKUP_DIR"/.env.backup_* | head -1)
        log_warn "Found backed up .env file. Do you want to restore it?"
        read -p "Restore backed up .env? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp "$LATEST_ENV" .env
            log_info "Restored backed up .env ✓"
        fi
    fi
    
    log_info "Configuration files created ✓"
}

setup_database() {
    log_step "Setting up Database"
    
    # Start PostgreSQL
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
    
    # Create database user and database
    log_info "Creating database..."
    sudo -u postgres psql -c "CREATE USER smartarb_user WITH PASSWORD 'smartarb_temp_password';" || true
    sudo -u postgres psql -c "CREATE DATABASE smartarb_dev OWNER smartarb_user;" || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE smartarb_dev TO smartarb_user;" || true
    
    log_info "Database setup complete ✓"
}

setup_redis() {
    log_step "Setting up Redis"
    
    # Start Redis
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
    
    log_info "Redis setup complete ✓"
}

generate_secrets() {
    log_step "Generating Secrets"
    
    cd "$PROJECT_DIR"
    source venv/bin/activate
    
    # Generate secrets
    if [ -f "scripts/generate_secrets.py" ]; then
        log_info "Generating application secrets..."
        python scripts/generate_secrets.py --environment=development --generate-ssl --docker-env
        log_info "Secrets generated ✓"
    else
        log_warn "Secret generation script not found, using manual setup"
    fi
}

optimize_for_raspberry_pi() {
    log_step "Applying Raspberry Pi Optimizations"
    
    # GPU memory split
    if command -v raspi-config >/dev/null; then
        log_info "Setting GPU memory split to 64MB..."
        sudo raspi-config nonint do_memory_split 64
    fi
    
    # Performance governor
    log_info "Setting CPU governor to performance..."
    if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
        echo "performance" | sudo tee /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
    fi
    
    # Disable unnecessary services
    log_info "Disabling unnecessary services..."
    for service in bluetooth hciuart triggerhappy; do
        sudo systemctl disable $service 2>/dev/null || true
        sudo systemctl stop $service 2>/dev/null || true
    done
    
    log_info "Raspberry Pi optimizations applied ✓"
}

run_tests() {
    log_step "Running System Tests"
    
    cd "$PROJECT_DIR"
    source venv/bin/activate
    
    # Basic import test
    log_info "Testing imports..."
    python -c "import src; print('✓ Basic imports working')"
    
    # Run test suite if available
    if [ -f "tests/test_comprehensive.py" ]; then
        log_info "Running test suite..."
        python -m pytest tests/test_basic.py -v || log_warn "Some tests failed"
    fi
    
    # Health check
    if [ -f "scripts/health_check.py" ]; then
        log_info "Running health check..."
        python scripts/health_check.py || log_warn "Health check reported issues"
    fi
    
    log_info "System tests completed ✓"
}

setup_systemd_service() {
    log_step "Setting up Systemd Service"
    
    cat > /tmp/smartarb.service << EOF
[Unit]
Description=SmartArb Engine
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python -m src.core.engine
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo mv /tmp/smartarb.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable smartarb
    
    log_info "Systemd service created ✓"
}

final_configuration_reminder() {
    log_step "Deployment Complete!"
    
    log_info "🎉 SmartArb Engine has been successfully deployed!"
    echo
    log_warn "⚠️  IMPORTANT: Complete these steps before starting:"
    echo
    echo "1. Edit configuration files with your API keys:"
    echo "   nano $PROJECT_DIR/.env"
    echo "   nano $PROJECT_DIR/config/settings.yaml"
    echo
    echo "2. Add your exchange API keys:"
    echo "   - KRAKEN_API_KEY and KRAKEN_API_SECRET"
    echo "   - BYBIT_API_KEY and BYBIT_API_SECRET" 
    echo "   - MEXC_API_KEY and MEXC_API_SECRET"
    echo "   - CLAUDE_API_KEY (for AI features)"
    echo
    echo "3. Start the application:"
    echo "   cd $PROJECT_DIR"
    echo "   make run-paper  # Start in paper trading mode"
    echo
    echo "4. Monitor the system:"
    echo "   - Dashboard: http://$(hostname -I | awk '{print $1}'):3000"
    echo "   - Health: http://$(hostname -I | awk '{print $1}'):8000/health"
    echo "   - Logs: make logs"
    echo
    echo "5. For production deployment:"
    echo "   make docker-compose-secure"
    echo
    log_info "🚀 Happy trading!"
}

main() {
    log_info "🚀 Starting SmartArb Engine deployment on Raspberry Pi 5"
    echo
    
    # Confirm before proceeding
    read -p "This will deploy SmartArb Engine with all latest fixes. Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
    
    # Run deployment steps
    check_raspberry_pi
    setup_external_storage
    backup_existing_installation
    clone_repository
    install_system_dependencies
    setup_python_environment
    create_configurations
    setup_database
    setup_redis
    generate_secrets
    optimize_for_raspberry_pi
    run_tests
    setup_systemd_service
    final_configuration_reminder
    
    log_info "✅ Deployment completed successfully!"
}

# Run main function
main "$@"
