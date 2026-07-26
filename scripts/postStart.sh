#!/bin/bash
# Called by FPP after fppd starts (FPP 10+ bare metal boot path)

PLUGIN_DIR="/home/fpp/media/plugins/fpp-matrixscroller"
DAEMON="$PLUGIN_DIR/matrixscroller.py"
PIDFILE="/var/run/fppd/matrixscroller.pid"
LOGFILE="/home/fpp/media/logs/fpp-matrixscroller.log"

mkdir -p "$(dirname "$PIDFILE")"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null && grep -q "matrixscroller" /proc/$PID/cmdline 2>/dev/null; then
        echo "matrixscroller already running (PID $PID)"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

COMMIT=$(git -C "$PLUGIN_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
echo "Starting matrixscroller daemon @ $COMMIT..."
python3 "$DAEMON" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "matrixscroller started (PID $!)"
