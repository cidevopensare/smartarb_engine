#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

start_services() {
    echo "Starting SmartArb Engine and Dashboard..."
    source venv/bin/activate
    
    # Start engine
    python -m src.core.engine &
    ENGINE_PID=$!
    echo $ENGINE_PID > .engine.pid
    
    # Wait a bit
    sleep 3
    
    # Start dashboard  
    python src/api/dashboard_server.py &
    DASHBOARD_PID=$!
    echo $DASHBOARD_PID > .dashboard.pid
    
    echo "Services started:"
    echo "  - Engine PID: $ENGINE_PID"
    echo "  - Dashboard PID: $DASHBOARD_PID" 
    echo "  - Dashboard URL: http://localhost:8000"
    echo "  - Network URL: http://$(hostname -I | awk '{print $1}'):8000"
    
    # Keep script running
    wait
}

stop_services() {
    echo "Stopping services..."
    if [ -f .engine.pid ]; then
        kill $(cat .engine.pid) 2>/dev/null || true
        rm .engine.pid
    fi
    if [ -f .dashboard.pid ]; then
        kill $(cat .dashboard.pid) 2>/dev/null || true  
        rm .dashboard.pid
    fi
    pkill -f "src.core.engine" 2>/dev/null || true
    pkill -f "dashboard_server" 2>/dev/null || true
    echo "Services stopped"
}

status_services() {
    echo "Service Status:"
    ps aux | grep -E "(src.core.engine|dashboard_server)" | grep -v grep || echo "No services running"
}

case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_services
        ;;
    status)
        status_services
        ;;
    url)
        echo "Dashboard URLs:"
        echo "  Local: http://localhost:8000" 
        echo "  Network: http://$(hostname -I | awk '{print $1}'):8000"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|url}"
        exit 1
        ;;
esac
