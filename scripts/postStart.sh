#!/bin/bash

PLUGIN_DIR="/home/fpp/media/plugins/fpp-matrixscroller"
DAEMON="$PLUGIN_DIR/matrixscroller.py"
PIDFILE="/var/run/matrixscroller.pid"
LOGFILE="/home/fpp/media/logs/matrixscroller.log"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "matrixscroller already running (PID $PID)"
        exit 0
    fi
    rm -f "$PIDFILE"
fi

echo "Starting matrixscroller daemon..."
python3 "$DAEMON" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "matrixscroller started (PID $!)"
