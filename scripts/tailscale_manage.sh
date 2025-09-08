# Script per gestire Tailscale senza interferire con DNS

#!/bin/bash

case $1 in
    "start")
        echo "🚀 Starting Tailscale with DNS protection..."
        # Proteggi DNS prima di avviare Tailscale
        sudo chattr +i /etc/resolv.conf
        sudo tailscale up --accept-dns=false
        echo "✅ Tailscale started without DNS override"
        ;;
    "stop")
        echo "🛑 Stopping Tailscale..."
        sudo tailscale down
        # Ripristina DNS se necessario
        if [ -f /etc/resolv.conf.tailscale.backup ]; then
            sudo chattr -i /etc/resolv.conf
            sudo tee /etc/resolv.conf << 'DNSEOF'
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
DNSEOF
            sudo chattr +i /etc/resolv.conf
        fi
        echo "✅ Tailscale stopped, DNS restored"
        ;;
    "status")
        echo "📊 Tailscale Status:"
        sudo tailscale status
        echo ""
        echo "📊 DNS Status:"
        cat /etc/resolv.conf
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        echo "Manages Tailscale without DNS conflicts"
        ;;
esac
