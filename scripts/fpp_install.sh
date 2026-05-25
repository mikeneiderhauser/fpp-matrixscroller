#!/bin/bash

# fpp-matrixscroller install script

PLUGIN_DIR=$(cd "$(dirname "$0")/.." && pwd)

chmod +x "$PLUGIN_DIR/plugin_event.sh"
chmod +x "$PLUGIN_DIR/matrixscroller.py"
chmod +x "$PLUGIN_DIR/scripts/fpp_uninstall.sh"

mkdir -p /home/fpp/media/logs
mkdir -p /home/fpp/media/config
mkdir -p /var/run/fppd

PIDFILE="/var/run/fppd/matrixscroller.pid"
LOGFILE="/home/fpp/media/logs/fpp-matrixscroller.log"

# Check if our daemon is genuinely running (not just a recycled PID)
RUNNING=0
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null && grep -q "matrixscroller" /proc/$PID/cmdline 2>/dev/null; then
        RUNNING=1
    else
        rm -f "$PIDFILE"
    fi
fi

if [ "$RUNNING" -eq 1 ]; then
    echo "fpp-matrixscroller daemon already running (PID $PID)"
else
    python3 "$PLUGIN_DIR/matrixscroller.py" >> "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "fpp-matrixscroller daemon started (PID $!)"
fi

echo "fpp-matrixscroller install complete"
