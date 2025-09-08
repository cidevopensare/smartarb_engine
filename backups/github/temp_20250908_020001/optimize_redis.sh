#!/bin/bash
# SmartArb Engine - Redis Optimization Script for Raspberry Pi 5
# Optimized for cryptocurrency arbitrage trading

set -e

echo "🔧 SmartArb Engine - Optimizing Redis for Raspberry Pi 5"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get system info
RAM_MB=$(free -m | awk 'NR==2{print $2}')
CPU_CORES=$(nproc)

echo -e "${BLUE}System Info:${NC}"
echo "  RAM: ${RAM_MB}MB"
echo "  CPU Cores: ${CPU_CORES}"

# Backup existing Redis config
echo -e "${YELLOW}📋 Backing up current Redis config...${NC}"
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup.$(date +%Y%m%d_%H%M%S)

# Create optimized Redis configuration
echo -e "${BLUE}🔧 Creating optimized Redis configuration...${NC}"

sudo tee /etc/redis/redis.conf > /dev/null <<EOF
# SmartArb Engine - Redis Configuration
# Optimized for Raspberry Pi 5 + Cryptocurrency Arbitrage Trading

# =============================================================================
# NETWORK & SECURITY
# =============================================================================
bind 127.0.0.1 ::1
protected-mode yes
port 6379
tcp-backlog 511
timeout 300
tcp-keepalive 300

# Password protection (uncomment and set your password)
# requirepass your_secure_redis_password_here

# =============================================================================
# GENERAL SETTINGS
# =============================================================================
daemonize yes
supervised systemd
pidfile /var/run/redis/redis-server.pid
loglevel notice
logfile /var/log/redis/redis-server.log
syslog-enabled yes
syslog-ident redis

# =============================================================================
# MEMORY OPTIMIZATION (RPi 5 Specific)
# =============================================================================

# Set max memory to 25% of total RAM (conservative for arbitrage)
maxmemory $(($RAM_MB * 1024 * 1024 / 4))
maxmemory-policy allkeys-lru

# Memory sampling for LRU eviction (balanced accuracy/performance)
maxmemory-samples 5

# =============================================================================
# PERSISTENCE STRATEGY (Arbitrage Optimized)
# =============================================================================

# RDB Snapshots - Important for arbitrage data
save 900 1      # Save if at least 1 key changes in 900 seconds
save 300 10     # Save if at least 10 keys change in 300 seconds  
save 60 10000   # Save if at least 10000 keys change in 60 seconds

stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename smartarb_dump.rdb
dir /var/lib/redis

# AOF - Disabled for speed (arbitrage needs speed over durability)
appendonly no

# =============================================================================
# PERFORMANCE TUNING (Arbitrage Trading)
# =============================================================================

# Hash optimization (for order books, price data)
hash-max-ziplist-entries 512
hash-max-ziplist-value 64

# List optimization (for trade queues)
list-max-ziplist-size -2
list-compress-depth 0

# Set optimization (for active symbols)
set-max-intset-entries 512

# Sorted set optimization (for price levels)
zset-max-ziplist-entries 128
zset-max-ziplist-value 64

# HyperLogLog optimization
hll-sparse-max-bytes 3000

# Stream optimization (for real-time data)
stream-node-max-bytes 4096
stream-node-max-entries 100

# =============================================================================
# CONNECTION HANDLING
# =============================================================================

# Connection limits (conservative for RPi)
maxclients 100

# =============================================================================
# CPU OPTIMIZATION
# =============================================================================

# Use single thread for I/O (optimal for RPi 5)
io-threads 1
io-threads-do-reads no

# =============================================================================
# SLOW QUERY MONITORING
# =============================================================================

# Monitor commands slower than 10ms (arbitrage is time-sensitive)
slowlog-log-slower-than 10000
slowlog-max-len 128

# =============================================================================
# LATENCY MONITORING
# =============================================================================

# Enable latency monitoring for arbitrage optimization  
latency-monitor-threshold 100

# =============================================================================
# CLIENT OUTPUT BUFFER LIMITS
# =============================================================================

# Normal clients (trading connections)
client-output-buffer-limit normal 0 0 0

# Replica clients
client-output-buffer-limit replica 256mb 64mb 60

# Pub/sub clients (for real-time price updates)
client-output-buffer-limit pubsub 32mb 8mb 60

# =============================================================================
# ADVANCED SETTINGS
# =============================================================================

# Disable dangerous commands in production
rename-command FLUSHALL ""
rename-command FLUSHDB ""
rename-command CONFIG SMARTARB_CONFIG
rename-command DEBUG SMARTARB_DEBUG

# Enable notifications for key events (useful for arbitrage monitoring)
notify-keyspace-events "AKE"

# Optimize for small memory footprint
activedefrag yes
active-defrag-ignore-bytes 100mb
active-defrag-threshold-lower 10
active-defrag-threshold-upper 100
active-defrag-cycle-min 1
active-defrag-cycle-max 25

# =============================================================================
# RASPBERRY PI SPECIFIC OPTIMIZATIONS  
# =============================================================================

# Reduce disk I/O (SD card protection)
save 1800 1     # Longer save intervals
save 3600 1

# Optimize for ARM architecture
tcp-keepalive 60

# Memory overcommit (careful with RPi)
# Set in /etc/sysctl.conf: vm.overcommit_memory=1

EOF

# Set proper permissions
sudo chown redis:redis /etc/redis/redis.conf
sudo chmod 640 /etc/redis/redis.conf

# Create Redis systemd override for performance
echo -e "${BLUE}⚡ Creating systemd performance overrides...${NC}"
sudo mkdir -p /etc/systemd/system/redis-server.service.d/

sudo tee /etc/systemd/system/redis-server.service.d/smartarb-performance.conf > /dev/null <<EOF
[Service]
# Performance optimizations for SmartArb Engine
LimitNOFILE=65535
LimitNPROC=32768

# CPU scheduling priority (higher priority for trading)
Nice=-5
IOSchedulingClass=1
IOSchedulingPriority=4

# Memory settings
OOMScoreAdjust=-900

# Security
NoNewPrivileges=yes
PrivateTmp=yes
EOF

# Optimize system settings for Redis
echo -e "${BLUE}🔧 Optimizing system settings...${NC}"

# Sysctl optimizations
sudo tee /etc/sysctl.d/99-smartarb-redis.conf > /dev/null <<EOF
# SmartArb Engine - Redis System Optimizations

# Memory overcommit for Redis
vm.overcommit_memory=1

# Network optimizations
net.core.somaxconn=65535
net.core.netdev_max_backlog=5000
net.ipv4.tcp_max_syn_backlog=65535

# Virtual memory optimizations for trading
vm.swappiness=1

# Transparent huge pages (disable for Redis)
# This will be set at runtime
EOF

sudo sysctl -p /etc/sysctl.d/99-smartarb-redis.conf

# Disable transparent huge pages (critical for Redis performance)
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo 'echo never > /sys/kernel/mm/transparent_hugepage/enabled' | sudo tee -a /etc/rc.local

# Reload systemd and restart Redis
echo -e "${YELLOW}🔄 Restarting Redis with new configuration...${NC}"
sudo systemctl daemon-reload
sudo systemctl restart redis-server

# Wait for Redis to start
sleep 3

# Test Redis
echo -e "${BLUE}🧪 Testing Redis configuration...${NC}"
if redis-cli ping | grep -q PONG; then
    echo -e "${GREEN}✅ Redis is running successfully!${NC}"
    
    # Show Redis info
    echo -e "${BLUE}📊 Redis Status:${NC}"
    redis-cli info memory | grep used_memory_human
    redis-cli info persistence | grep rdb_last_save_time
    redis-cli info stats | grep total_connections_received
    
    echo -e "${GREEN}🚀 Redis optimization completed successfully!${NC}"
    echo -e "${YELLOW}💡 Remember to set a strong password with: redis-cli CONFIG SET requirepass 'your_password'${NC}"
else
    echo -e "${RED}❌ Redis failed to start! Check logs: sudo journalctl -u redis-server${NC}"
    exit 1
fi

# Create Redis monitoring script
echo -e "${BLUE}📊 Creating Redis monitoring script...${NC}"
sudo tee /opt/smartarb/scripts/redis_monitor.sh > /dev/null <<'EOF'
#!/bin/bash
# SmartArb Redis Performance Monitor

while true; do
    echo "=== Redis Status $(date) ==="
    
    # Basic stats
    redis-cli info memory | grep "used_memory_human\|used_memory_peak_human"
    redis-cli info stats | grep "total_commands_processed\|instantaneous_ops_per_sec"
    redis-cli info persistence | grep "rdb_last_save_time"
    
    # Slow queries
    echo "Recent slow queries:"
    redis-cli slowlog get 3
    
    # Latency
    echo "Latency samples:"
    redis-cli latency latest
    
    echo "================================="
    sleep 60
done
EOF

sudo chmod +x /opt/smartarb/scripts/redis_monitor.sh

echo -e "${GREEN}✅ SmartArb Redis optimization completed!${NC}"
echo -e "${BLUE}📋 Summary:${NC}"
echo "  ✅ Redis configuration optimized for arbitrage trading"
echo "  ✅ System settings tuned for performance"  
echo "  ✅ Monitoring scripts created"
echo "  ✅ Service configured for high priority"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Set Redis password: redis-cli CONFIG SET requirepass 'your_secure_password'"
echo "  2. Update your .env file with the password"
echo "  3. Test API connections to exchanges"
echo "  4. Monitor performance: /opt/smartarb/scripts/redis_monitor.sh"
