#!/bin/bash

# =============================================================================

# SmartArb Engine - Raspberry Pi Setup Script

# Automated setup for Raspberry Pi 5 deployment

# =============================================================================

set -e  # Exit on any error

# Colors for output

RED=’\033[0;31m’
GREEN=’\033[0;32m’
YELLOW=’\033[1;33m’
BLUE=’\033[0;34m’
CYAN=’\033[0;36m’
NC=’\033[0m’ # No Color

# Configuration

SMARTARB_USER=“smartarb”
SMARTARB_HOME=”/opt/smartarb”
PYTHON_VERSION=“3.11”
NODE_VERSION=“18”

# Functions

print_header() {
echo -e “${CYAN}”
echo “╔══════════════════════════════════════════════════════════════╗”
echo “║                                                              ║”
echo “║              SmartArb Engine - Raspberry Pi Setup           ║”
echo “║                    Professional Trading Bot                  ║”
echo “║                                                              ║”
echo “╚══════════════════════════════════════════════════════════════╝”
echo -e “${NC}”
}

print_step() {
echo -e “${BLUE}[INFO]${NC} $1”
}

print_success() {
echo -e “${GREEN}[SUCCESS]${NC} $1”
}

print_warning() {
echo -e “${YELLOW}[WARNING]${NC} $1”
}

print_error() {
echo -e “${RED}[ERROR]${NC} $1”
}

check_requirements() {
print_step “Checking system requirements…”

```
# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    print_warning "This script is optimized for Raspberry Pi but will continue..."
fi

# Check available memory
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_MEM" -lt 3800 ]; then
    print_warning "Less than 4GB RAM detected. SmartArb Engine may run slowly."
fi

# Check available disk space
AVAILABLE_SPACE=$(df / | awk 'NR==2{print $4}')
if [ "$AVAILABLE_SPACE" -lt 10485760 ]; then  # 10GB in KB
    print_error "Insufficient disk space. At least 10GB free space required."
    exit 1
fi

print_success "System requirements check completed"
```

}

update_system() {
print_step “Updating system packages…”

```
sudo apt update
sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    tmux \
    unzip \
    build-essential \
    libssl-dev \
    libffi-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev

print_success "System packages updated"
```

}

install_python() {
print_step “Installing Python ${PYTHON_VERSION}…”

```
# Check if Python 3.11+ is already installed
if python3.11 --version >/dev/null 2>&1; then
    print_success "Python 3.11 already installed"
    return
fi

# Add deadsnakes PPA for latest Python versions
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.11
sudo apt install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3.11-distutils

# Install pip
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.11

# Create symlinks
sudo ln -sf /usr/bin/python3.11 /usr/local/bin/python3
sudo ln -sf /usr/bin/python3.11 /usr/local/bin/python

print_success "Python ${PYTHON_VERSION} installed"
```

}

install_nodejs() {
print_step “Installing Node.js ${NODE_VERSION}…”

```
# Install Node.js using NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | sudo -E bash -
sudo apt install -y nodejs

# Install global packages for development
sudo npm install -g \
    yarn \
    pm2 \
    nodemon

print_success "Node.js ${NODE_VERSION} installed"
```

}

install_docker() {
print_step “Installing Docker…”

```
# Remove old versions
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
sudo usermod -aG docker $SMARTARB_USER 2>/dev/null || true

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker

print_success "Docker installed"
```

}

install_databases() {
print_step “Installing databases…”

```
# PostgreSQL
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Redis
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Configure PostgreSQL
sudo -u postgres createuser --createdb --no-superuser --no-createrole smartarb || true
sudo -u postgres createdb smartarb_dev || true

print_success "Databases installed"
```

}

create_smartarb_user() {
print_step “Creating SmartArb user…”

```
# Create system user for SmartArb
if ! id "$SMARTARB_USER" &>/dev/null; then
    sudo useradd -r -m -s /bin/bash -d "$SMARTARB_HOME" "$SMARTARB_USER"
    print_success "User $SMARTARB_USER created"
else
    print_success "User $SMARTARB_USER already exists"
fi

# Add to necessary groups
sudo usermod -aG sudo $SMARTARB_USER
sudo usermod -aG docker $SMARTARB_USER
sudo usermod -aG gpio $SMARTARB_USER 2>/dev/null || true
sudo usermod -aG spi $SMARTARB_USER 2>/dev/null || true
sudo usermod -aG i2c $SMARTARB_USER 2>/dev/null || true
```

}

setup_smartarb_environment() {
print_step “Setting up SmartArb environment…”

```
# Create directories
sudo mkdir -p "$SMARTARB_HOME"/{logs,data,config,backups,scripts}
sudo chown -R $SMARTARB_USER:$SMARTARB_USER "$SMARTARB_HOME"

# Clone repository (if not already present)
if [ ! -d "$SMARTARB_HOME/smartarb-engine" ]; then
    sudo -u $SMARTARB_USER git clone https://github.com/smartarb/smartarb-engine.git "$SMARTARB_HOME/smartarb-engine"
fi

# Create Python virtual environment
sudo -u $SMARTARB_USER python3.11 -m venv "$SMARTARB_HOME/venv"

# Install Python dependencies
sudo -u $SMARTARB_USER "$SMARTARB_HOME/venv/bin/pip" install --upgrade pip
sudo -u $SMARTARB_USER "$SMARTARB_HOME/venv/bin/pip" install -r "$SMARTARB_HOME/smartarb-engine/requirements.txt"

print_success "SmartArb environment setup completed"
```

}

configure_systemd() {
print_step “Configuring systemd service…”

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

configure_logrotate() {
print_step “Configuring log rotation…”

```
# Create logrotate configuration
sudo tee /etc/logrotate.d/smartarb > /dev/null <<EOF
```

$SMARTARB_HOME/logs/*.log {
daily
missingok
rotate 30
compress
delaycompress
notifempty
create 644 $SMARTARB_USER $SMARTARB_USER
postrotate
systemctl reload smartarb 2>/dev/null || true
endscript
}
EOF

```
print_success "Log rotation configured"
```

}

configure_firewall() {
print_step “Configuring firewall…”

```
# Install and configure ufw
sudo apt install -y ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow ssh

# Allow SmartArb API/Dashboard
sudo ufw allow 8000/tcp comment 'SmartArb API'

# Allow monitoring (if needed)
sudo ufw allow from 192.168.0.0/16 to any port 9090 comment 'Prometheus'
sudo ufw allow from 192.168.0.0/16 to any port 3000 comment 'Grafana'

# Enable firewall
echo "y" | sudo ufw enable

print_success "Firewall configured"
```

}

optimize_raspberry_pi() {
print_step “Optimizing Raspberry Pi settings…”

```
# Update boot config
sudo tee -a /boot/config.txt > /dev/null <<EOF
```

# SmartArb Engine optimizations

gpu_mem=16
disable_camera=1
dtparam=audio=off
dtoverlay=disable-wifi
dtoverlay=disable-bt

# Performance optimizations

arm_freq=2000
over_voltage=6
temp_soft_limit=70

# Enable GPIO

dtparam=i2c_arm=on
dtparam=spi=on
enable_uart=1
EOF

```
# Update sysctl for networking
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF
```

# SmartArb Engine network optimizations

net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 16384 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
EOF

```
# Disable unnecessary services
sudo systemctl disable bluetooth.service
sudo systemctl disable hciuart.service
sudo systemctl disable avahi-daemon.service
sudo systemctl disable cups.service 2>/dev/null || true

print_success "Raspberry Pi optimized"
```

}

install_monitoring() {
print_step “Installing monitoring tools…”

```
# Install system monitoring
sudo apt install -y \
    htop \
    iotop \
    nethogs \
    sysstat \
    lm-sensors

# Configure sensors
sudo sensors-detect --auto 2>/dev/null || true

# Install custom monitoring script
sudo tee "$SMARTARB_HOME/scripts/monitor.py" > /dev/null <<'EOF'
```

#!/usr/bin/env python3
import psutil
import json
import time
from pathlib import Path

def get_system_metrics():
return {
‘cpu_percent’: psutil.cpu_percent(interval=1),
‘memory_percent’: psutil.virtual_memory().percent,
‘disk_usage’: psutil.disk_usage(’/’).percent,
‘temperature’: get_temperature(),
‘uptime’: time.time() - psutil.boot_time(),
‘load_average’: psutil.getloadavg(),
‘network_io’: dict(psutil.net_io_counters()._asdict())
}

def get_temperature():
try:
# Raspberry Pi temperature
with open(’/sys/class/thermal/thermal_zone0/temp’, ‘r’) as f:
temp = int(f.read()) / 1000.0
return temp
except:
return 0

if **name** == “**main**”:
metrics = get_system_metrics()
print(json.dumps(metrics, indent=2))
EOF

```
sudo chmod +x "$SMARTARB_HOME/scripts/monitor.py"
sudo chown $SMARTARB_USER:$SMARTARB_USER "$SMARTARB_HOME/scripts/monitor.py"

print_success "Monitoring tools installed"
```

}

create_startup_script() {
print_step “Creating startup script…”

```
# Create startup script
sudo tee "$SMARTARB_HOME/scripts/start.sh" > /dev/null <<EOF
```

#!/bin/bash

# SmartArb Engine Startup Script

cd $SMARTARB_HOME/smartarb-engine

# Wait for network

sleep 10

# Start SmartArb Engine

echo “Starting SmartArb Engine…”
sudo systemctl start smartarb

# Check status

sleep 5
if sudo systemctl is-active –quiet smartarb; then
echo “SmartArb Engine started successfully”
else
echo “Failed to start SmartArb Engine”
sudo systemctl status smartarb
fi
EOF

```
sudo chmod +x "$SMARTARB_HOME/scripts/start.sh"
sudo chown $SMARTARB_USER:$SMARTARB_USER "$SMARTARB_HOME/scripts/start.sh"

print_success "Startup script created"
```

}

final_configuration() {
print_step “Performing final configuration…”

```
# Create example configuration
sudo -u $SMARTARB_USER cp "$SMARTARB_HOME/smartarb-engine/.env.example" "$SMARTARB_HOME/smartarb-engine/.env"
sudo -u $SMARTARB_USER cp "$SMARTARB_HOME/smartarb-engine/config/settings.yaml" "$SMARTARB_HOME/config/" 2>/dev/null || true

# Set proper permissions
sudo chmod 600 "$SMARTARB_HOME/smartarb-engine/.env"
sudo chmod -R 755 "$SMARTARB_HOME/logs"
sudo chmod -R 755 "$SMARTARB_HOME/data"

# Create crontab for monitoring
sudo -u $SMARTARB_USER crontab -l 2>/dev/null | {
    cat
    echo "*/5 * * * * $SMARTARB_HOME/scripts/monitor.py >> $SMARTARB_HOME/logs/system_metrics.log 2>&1"
} | sudo -u $SMARTARB_USER crontab -

print_success "Final configuration completed"
```

}

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
echo "2. ⚙️  Configure trading settings:"
echo "   sudo -u $SMARTARB_USER nano $SMARTARB_HOME/config/settings.yaml"
echo ""
echo "3. 🚀 Start SmartArb Engine:"
echo "   sudo systemctl start smartarb"
echo ""
echo "4. 📊 Check status:"
echo "   sudo systemctl status smartarb"
echo ""
echo "5. 📋 View logs:"
echo "   sudo journalctl -u smartarb -f"
echo ""
echo "6. 🌐 Access dashboard (when running):"
echo "   http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "7. 🔄 Enable auto-start on boot:"
echo "   sudo systemctl enable smartarb"
echo ""
echo -e "${YELLOW}Important Files:${NC}"
echo "📁 Installation directory: $SMARTARB_HOME"
echo "📁 Configuration: $SMARTARB_HOME/config/"
echo "📁 Logs: $SMARTARB_HOME/logs/"
echo "📁 Data: $SMARTARB_HOME/data/"
echo "🔧 Service: sudo systemctl {start|stop|restart|status} smartarb"
echo ""
echo -e "${RED}Security Reminder:${NC}"
echo "🔐 Change default passwords and secure your API keys!"
echo "🔒 Configure firewall rules for your network"
echo "🛡️  Enable SSH key authentication"
echo ""
echo -e "${BLUE}Support:${NC}"
echo "📖 Documentation: https://docs.smartarb.dev"
echo "💬 Community: https://discord.gg/smartarb"
echo "🐛 Issues: https://github.com/smartarb/smartarb-engine/issues"
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

# Check if user has sudo privileges
if ! sudo -n true 2>/dev/null; then
    print_error "This script requires sudo privileges"
    exit 1
fi

# Execute setup steps
check_requirements
update_system
install_python
install_nodejs
install_docker
install_databases
create_smartarb_user
setup_smartarb_environment
configure_systemd
configure_logrotate
configure_firewall
optimize_raspberry_pi
install_monitoring
create_startup_script
final_configuration

print_completion_info

echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${YELLOW}Please reboot your Raspberry Pi to apply all changes:${NC}"
echo "sudo reboot"
```

}

# Run main function

main “$@”