# Crea script intelligente per IP statico
#!/bin/bash

TARGET_IP="192.168.1.100"
GATEWAY="192.168.1.1"
DNS1="8.8.8.8"
DNS2="8.8.4.4"

echo "🌐 SmartArb Engine - Static IP Setup"
echo "Target IP: $TARGET_IP"

# Trova interfaccia ethernet
ETH_INTERFACE=$(ip link show | grep -E '^[0-9]+: e' | cut -d: -f2 | tr -d ' ' | head -1)
if [ -z "$ETH_INTERFACE" ]; then
    echo "❌ No ethernet interface found!"
    exit 1
fi

echo "Interface: $ETH_INTERFACE"

# Backup configurazione attuale
echo "💾 Creating network backup..."
mkdir -p backups/network/
ip addr show > backups/network/network_config_$(date +%Y%m%d_%H%M).backup
ip route show > backups/network/routes_$(date +%Y%m%d_%H%M).backup

# Detect network management system
if systemctl is-active NetworkManager >/dev/null 2>&1; then
    echo "🔧 Using NetworkManager..."
    
    # Ottieni nome connessione
    CONNECTION_NAME=$(nmcli -t -f NAME connection show --active | head -1)
    
    if [ -n "$CONNECTION_NAME" ]; then
        sudo nmcli connection modify "$CONNECTION_NAME" \
            ipv4.addresses $TARGET_IP/24 \
            ipv4.gateway $GATEWAY \
            ipv4.dns "$DNS1,$DNS2" \
            ipv4.method manual
        
        sudo nmcli connection down "$CONNECTION_NAME"
        sudo nmcli connection up "$CONNECTION_NAME"
        
        echo "✅ NetworkManager configuration applied"
    else
        echo "❌ No active connection found"
        exit 1
    fi
    
elif [ -f /etc/network/interfaces ]; then
    echo "🔧 Using traditional networking..."
    
    # Backup
    sudo cp /etc/network/interfaces /etc/network/interfaces.backup.$(date +%Y%m%d)
    
    # Crea configurazione
    sudo tee /etc/network/interfaces > /dev/null << NETEOF
auto lo
iface lo inet loopback

auto $ETH_INTERFACE
iface $ETH_INTERFACE inet static
    address $TARGET_IP
    netmask 255.255.255.0
    gateway $GATEWAY
    dns-nameservers $DNS1 $DNS2
NETEOF
    
    sudo systemctl restart networking
    echo "✅ Traditional networking configuration applied"
    
elif systemctl is-active systemd-networkd >/dev/null 2>&1; then
    echo "🔧 Using systemd-networkd..."
    
    sudo tee /etc/systemd/network/10-static.network > /dev/null << SYSDEOF
[Match]
Name=$ETH_INTERFACE

[Network]
Address=$TARGET_IP/24
Gateway=$GATEWAY
DNS=$DNS1
DNS=$DNS2
SYSDEOF
    
    sudo systemctl restart systemd-networkd
    echo "✅ systemd-networkd configuration applied"
    
else
    echo "❌ Unknown network management system"
    exit 1
fi

# Verifica configurazione
echo ""
echo "🔍 Verifying new configuration..."
sleep 5

# Test connettività
if ping -c 2 $GATEWAY >/dev/null 2>&1; then
    echo "✅ Gateway reachable"
else
    echo "❌ Gateway not reachable"
fi

if ping -c 2 8.8.8.8 >/dev/null 2>&1; then
    echo "✅ Internet connectivity OK"
else
    echo "❌ No internet connectivity"
fi

# Mostra configurazione finale
echo ""
echo "📊 Final network configuration:"
ip addr show $ETH_INTERFACE
echo ""
echo "🌐 Routes:"
ip route show
