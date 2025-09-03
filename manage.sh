#!/bin/bash

# SmartArb Engine - Proper Management Script
# Runs the REAL engine with trading + Telegram, not mock dashboard

ENGINE_PID_FILE="smartarb_engine.pid"
LOG_FILE="logs/smartarb.log"
PYTHON_ENV="venv/bin/python3"

start_engine() {
    echo "🚀 Starting REAL SmartArb Engine with Trading + Telegram..."
    
    # Ensure logs directory exists
    mkdir -p logs
    
    # Load environment variables
    source .env
    
    # Start the REAL engine (not dashboard mock)
    nohup $PYTHON_ENV src/main.py > $LOG_FILE 2>&1 &
    ENGINE_PID=$!
    
    # Save PID
    echo $ENGINE_PID > $ENGINE_PID_FILE
    
    echo "✅ SmartArb Engine started with PID: $ENGINE_PID"
    echo "📊 Logs: tail -f $LOG_FILE"
    echo "📱 Telegram notifications: Enabled"
    echo "💰 Trading mode: Paper Trading"
}

stop_engine() {
    echo "🛑 Stopping SmartArb Engine..."
    
    if [ -f $ENGINE_PID_FILE ]; then
        ENGINE_PID=$(cat $ENGINE_PID_FILE)
        if kill -0 $ENGINE_PID 2>/dev/null; then
            kill $ENGINE_PID
            echo "✅ Engine stopped (PID: $ENGINE_PID)"
        else
            echo "⚠️ Engine PID $ENGINE_PID not found"
        fi
        rm -f $ENGINE_PID_FILE
    else
        echo "⚠️ No PID file found"
    fi
    
    # Cleanup any remaining python processes
    pkill -f "src/main.py"
}

status_engine() {
    if [ -f $ENGINE_PID_FILE ]; then
        ENGINE_PID=$(cat $ENGINE_PID_FILE)
        if kill -0 $ENGINE_PID 2>/dev/null; then
            echo "✅ SmartArb Engine is running (PID: $ENGINE_PID)"
            echo "📊 Memory usage: $(ps -p $ENGINE_PID -o %mem --no-headers)%"
            echo "⚡ CPU usage: $(ps -p $ENGINE_PID -o %cpu --no-headers)%"
        else
            echo "❌ Engine PID $ENGINE_PID not responding"
            rm -f $ENGINE_PID_FILE
        fi
    else
        echo "❌ SmartArb Engine is not running"
    fi
}

case "$1" in
    start)
        start_engine
        ;;
    stop)
        stop_engine
        ;;
    restart)
        stop_engine
        sleep 3
        start_engine
        ;;
    status)
        status_engine
        ;;
    logs)
        tail -f $LOG_FILE
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
