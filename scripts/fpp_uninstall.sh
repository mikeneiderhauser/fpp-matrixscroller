#!/bin/bash

# fpp-matrixscroller uninstall script

PIDFILE="/var/run/fppd/matrixscroller.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null && grep -q "matrixscroller" /proc/$PID/cmdline 2>/dev/null; then
        echo "Stopping matrixscroller (PID $PID)..."
        kill "$PID"
        sleep 1
        kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
    fi
    rm -f "$PIDFILE"
fi

echo "fpp-matrixscroller uninstall complete"
