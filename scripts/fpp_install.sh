#!/bin/bash

# fpp-matrixscroller install script

. ${FPPDIR}/scripts/common

PLUGIN_DIR=$(cd "$(dirname "$0")/.." && pwd)

chmod +x "$PLUGIN_DIR/plugin_event.sh"
chmod +x "$PLUGIN_DIR/matrixscroller.py"
chmod +x "$PLUGIN_DIR/scripts/fpp_uninstall.sh"

mkdir -p /home/fpp/media/logs
mkdir -p /home/fpp/media/config

PIDFILE="/var/run/fppd/matrixscroller.pid"
LOGFILE="/home/fpp/media/logs/fpp-matrixscroller.log"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "fpp-matrixscroller daemon already running"
else
    python3 "$PLUGIN_DIR/matrixscroller.py" >> "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "fpp-matrixscroller daemon started (PID $!)"
fi

echo "fpp-matrixscroller install complete"
