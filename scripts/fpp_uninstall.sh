#!/bin/bash

# fpp-matrixscroller uninstall script

PIDFILE="/var/run/matrixscroller.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
    fi
    rm -f "$PIDFILE"
fi
