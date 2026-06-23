#!/bin/bash
#
# fpp-matrixscroller plugin event handler
# Called by FPP for lifecycle events
#

PLUGIN_DIR="/home/fpp/media/plugins/fpp-matrixscroller"
DAEMON="$PLUGIN_DIR/matrixscroller.py"
PIDFILE="/var/run/fppd/matrixscroller.pid"
LOGFILE="/home/fpp/media/logs/fpp-matrixscroller.log"

start_daemon() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null && grep -q "matrixscroller" /proc/$PID/cmdline 2>/dev/null; then
            echo "matrixscroller already running (PID $PID)"
            return
        fi
        rm -f "$PIDFILE"
    fi
    COMMIT=$(git -C "$PLUGIN_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
    echo "Starting matrixscroller daemon @ $COMMIT..."
    python3 "$DAEMON" >> "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "matrixscroller started (PID $!)"
}

stop_daemon() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Stopping matrixscroller (PID $PID)..."
            kill "$PID"
            sleep 1
            kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
        fi
        rm -f "$PIDFILE"
    fi
    echo "matrixscroller stopped"
}

case "$1" in
    fppd_start)
        start_daemon
        ;;
    fppd_stop)
        stop_daemon
        ;;
    *)
        echo "Usage: $0 {fppd_start|fppd_stop}"
        echo "Event received: $1"
        ;;
esac
