#!/bin/bash

# SmartArb Engine - Raspberry Pi Setup Script (Fixed Version)

# Professional cryptocurrency arbitrage trading bot setup

set -euo pipefail

# Color codes (fixed)

RED=’\033[0;31m’
GREEN=’\033[0;32m’
YELLOW=’\033[1;33m’
BLUE=’\033[0;34m’
CYAN=’\033[0;36m’
NC=’\033[0m’ # No Color

# Configuration

SMARTARB_USER=“smartarb”
SMARTARB_HOME=”/home/$SMARTARB_USER”
PYTHON_VERSION=“3.11”

# Helper functions

print_header() {
echo -e “${CYAN}”
echo “╔══════════════════════════════════════════════════════════════╗”
echo “║                                                              ║”
echo “║            🚀 SmartArb Engine - Raspberry Pi Setup          ║”
echo “║                                                              ║”
echo “╚══════════════════════════════════════════════════════════════╝”
echo -e “${NC}”
}

print_step() {
echo -e “${BLUE}[$(date +’%H:%M:%S’)] $1…${NC}”
}

print_success() {
echo -e “${GREEN}✅ $1${NC}”
}

print_error() {
echo -e “${RED}❌ $1${NC}”
}

print_warning() {
echo -e “${YELLOW}⚠️  $1${NC}”
}

# Check system requirements

check_requirements() {
print_step “Checking system requirements”

```
# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    print_warning "This doesn't appear to be a Raspberry Pi, but continuing anyway"
fi

# Check available space (need at least 2GB)
AVAILABLE_SPACE=$(df / | awk 'NR==2{print $4}')
if [ $AVAILABLE_SPACE -lt 2097152 ]; then
    print_error "Insufficient disk space. Need at least 2GB free"
    exit 1
fi

# Check memory (recommend at least 1GB)
TOTAL_MEM=$(free -m | awk 'NR==2{print $2}')
if [ $TOTAL_MEM -lt 900 ]; then
    print_warning "Low memory detected ($TOTAL_MEM MB). Consider adding swap"
fi

print_success "System requirements check completed"
```

}

# Update system

update_system() {
print_step “Updating system packages”
sudo apt update && sudo apt upgrade -y
print_success “System updated successfully”
}

# Install Python 3.11

install_python() {
print_step “Installing Python $PYTHON_VERSION”

```
sudo apt install -y \
    python$PYTHON_VERSION \
    python$PYTHON_VERSION-venv \
    python$PYTHON_VERSION-dev \
    python3-pip \
    build-essential \
    libffi-dev \
    libssl-dev

print_success "Python $PYTHON_VERSION installed"
```

}

# Install databases

install_databases() {
print_step “Installing PostgreSQL and Redis”

```
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install Redis
sudo apt install -y redis-server

# Configure PostgreSQL
sudo -u postgres createdb smartarb || print_warning "Database smartarb already exists"
sudo -u postgres createuser smartarb_user || print_warning "User smartarb_user already exists"
sudo -u postgres psql -c "ALTER USER smartarb_user WITH PASSWORD 'smartarb_secure_pass';" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE smartarb TO smartarb_user;" || true

# Start services
sudo systemctl enable postgresql redis-server
sudo systemctl start postgresql redis-server

print_success "Databases installed and configured"
```

}

# Create smartarb user

create_smartarb_user() {
print_step “Creating SmartArb user”

```
# Create user if not exists
if ! id "$SMARTARB_USER" &>/dev/null; then
    sudo useradd -m -s /bin/bash "$SMARTARB_USER"
    sudo usermod -aG sudo "$SMARTARB_USER"
fi

# Create directories
sudo -u "$SMARTARB_USER" mkdir -p "$SMARTARB_HOME/"{logs,data,config,scripts}

print_success "SmartArb user created"
```

}

# Setup SmartArb environment

setup_smartarb_environment() {
print_step “Setting up SmartArb environment”

```
# Copy project files to smartarb user directory
sudo cp -r . "$SMARTARB_HOME/smartarb-engine"
sudo chown -R "$SMARTARB_USER:$SMARTARB_USER" "$SMARTARB_HOME/smartarb-engine"

# Create Python virtual environment
sudo -u "$SMARTARB_USER" python$PYTHON_VERSION -m venv "$SMARTARB_HOME/venv"

# Install Python dependencies
sudo -u "$SMARTARB_USER" "$SMARTARB_HOME/venv/bin/pip" install --upgrade pip
sudo -u "$SMARTARB_USER" "$SMARTARB_HOME/venv/bin/pip" install -r requirements.txt

print_success "SmartArb environment setup completed"
```

}

# Configure systemd service

configure_systemd() {
print_step “Configuring systemd service”

```
# Create systemd service file
sudo tee /etc/systemd/system/smartarb.service > /dev/null <<EOF
```

[Unit]
Description=SmartArb Engine - Cryptocurrency Arbitrage Trading Bot
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=$SMARTARB_USER
Group=$SMARTARB_USER
WorkingDirectory=$SMARTARB_HOME/smartarb-engine
Environment=PATH=$SMARTARB_HOME/venv/bin
ExecStart=$SMARTARB_HOME/venv/bin/python -m src.core.engine
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=smartarb

# Resource limits for Raspberry Pi

MemoryLimit=1G
CPUQuota=80%

# Security settings

NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$SMARTARB_HOME
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

```
# Enable service
sudo systemctl daemon-reload
sudo systemctl enable smartarb

print_success "Systemd service configured"
```

}

# Optimize for Raspberry Pi

optimize_raspberry_pi() {
print_step “Optimizing for Raspberry Pi”

```
# Add swap if memory is low
if [ $TOTAL_MEM -lt 1500 ]; then
    if [ ! -f /swapfile ]; then
        sudo fallocate -l 1G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    fi
fi

# Optimize GPU memory split
echo "gpu_mem=16" | sudo tee -a /boot/config.txt

print_success "Raspberry Pi optimizations applied"
```

}

# Final configuration

final_configuration() {
print_step “Performing final configuration”

```
# Create example configuration files
sudo -u "$SMARTARB_USER" cp "$SMARTARB_HOME/smartarb-engine/.env.example" "$SMARTARB_HOME/smartarb-engine/.env" 2>/dev/null || true

# Set proper permissions
sudo chmod 600 "$SMARTARB_HOME/smartarb-engine/.env" 2>/dev/null || true
sudo chmod -R 755 "$SMARTARB_HOME/logs"
sudo chmod -R 755 "$SMARTARB_HOME/data"

print_success "Final configuration completed"
```

}

# Print completion information

print_completion_info() {
echo -e “${GREEN}”
echo “╔══════════════════════════════════════════════════════════════╗”
echo “║                                                              ║”
echo “║            🎉 SmartArb Engine Setup Completed! 🎉           ║”
echo “║                                                              ║”
echo “╚══════════════════════════════════════════════════════════════╝”
echo -e “${NC}”

```
echo -e "${CYAN}Next Steps:${NC}"
echo "1. 📝 Configure your API keys:"
echo "   sudo -u $SMARTARB_USER nano $SMARTARB_HOME/smartarb-engine/.env"
echo ""
echo "2. 🚀 Start SmartArb Engine:"
echo "   sudo systemctl start smartarb"
echo ""
echo "3. 📊 Check status:"
echo "   sudo systemctl status smartarb"
echo ""
echo "4. 📋 View logs:"
echo "   sudo journalctl -u smartarb -f"
echo ""
echo "5. 🌐 Access dashboard (when running):"
echo "   http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo -e "${YELLOW}Important Files:${NC}"
echo "📁 Installation directory: $SMARTARB_HOME"
echo "📁 Configuration: $SMARTARB_HOME/smartarb-engine/.env"
echo "📁 Logs: $SMARTARB_HOME/logs/"
echo "🔧 Service: sudo systemctl {start|stop|restart|status} smartarb"
echo ""
echo -e "${RED}Security Reminder:${NC}"
echo "🔐 Change default passwords and secure your API keys!"
```

}

# Main execution

main() {
print_header

```
echo -e "${YELLOW}This script will install SmartArb Engine on your Raspberry Pi.${NC}"
echo -e "${YELLOW}It will take approximately 15-30 minutes to complete.${NC}"
echo ""
read -p "Do you want to continue? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "This script should not be run as root"
    exit 1
fi

# Execute setup steps
check_requirements
update_system
install_python
install_databases
create_smartarb_user
setup_smartarb_environment
configure_systemd
optimize_raspberry_pi
final_configuration

print_completion_info

echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${YELLOW}Please reboot your Raspberry Pi to apply all changes:${NC}"
echo "sudo reboot"
```

}

# Run main function

main “$@”