#!/bin/bash
# Called by FPP before fppd stops (FPP 10+ bare metal boot path)

PIDFILE="/var/run/fppd/matrixscroller.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping matrixscroller (PID $PID)..."
        kill "$PID"
        sleep 1
        kill -0 "$PID" 2>/dev/null && kill -9 "$PID" || true
    fi
    rm -f "$PIDFILE"
fi
echo "matrixscroller stopped"
