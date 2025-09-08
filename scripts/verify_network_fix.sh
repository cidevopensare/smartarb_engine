# Script verifica finale
#!/bin/bash

echo "🌐 SmartArb Engine - Network Fix Verification"
echo "============================================"

# 1. DNS Configuration
echo "📊 DNS Configuration:"
cat /etc/resolv.conf
echo ""

# 2. Connectivity tests
echo "🧪 Connectivity Tests:"

# Basic internet
if ping -c 2 8.8.8.8 >/dev/null 2>&1; then
    echo "✅ Internet connectivity: OK"
else
    echo "❌ Internet connectivity: FAILED"
fi

# DNS Resolution
if nslookup google.com >/dev/null 2>&1; then
    echo "✅ DNS resolution: OK"
else
    echo "❌ DNS resolution: FAILED"
fi

# Trading endpoints
ENDPOINTS=("api.bybit.com" "api.mexc.com" "api.kraken.com" "api.telegram.org")
for endpoint in "${ENDPOINTS[@]}"; do
    if ping -c 2 "$endpoint" >/dev/null 2>&1; then
        echo "✅ $endpoint: OK"
    else
        echo "❌ $endpoint: FAILED"
    fi
done

echo ""
echo "📊 Network Summary:"
echo "   IP: $(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' || echo 'Unknown')"
echo "   Gateway: $(ip route | grep default | grep -oP 'via \K\S+' || echo 'Unknown')"
echo "   DNS: $(cat /etc/resolv.conf | grep nameserver | head -1 | awk '{print $2}')"

# Tailscale status
echo ""
echo "🔧 Tailscale Status:"
sudo tailscale status 2>/dev/null || echo "Tailscale not running"
