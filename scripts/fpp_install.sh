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
COMMIT=$(git -C "$PLUGIN_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "fpp-matrixscroller @ $COMMIT"

# Stop any running daemon so it picks up the new code
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null && grep -q "matrixscroller" /proc/$PID/cmdline 2>/dev/null; then
        echo "Stopping fpp-matrixscroller daemon (PID $PID) for update..."
        kill "$PID"
        sleep 1
        kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
    fi
    rm -f "$PIDFILE"
fi

python3 "$PLUGIN_DIR/matrixscroller.py" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "fpp-matrixscroller daemon started (PID $!)"

echo "fpp-matrixscroller install complete"
