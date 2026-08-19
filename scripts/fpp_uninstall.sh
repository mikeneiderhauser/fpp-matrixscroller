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

# Remove playlist scripts
for script in ms_enable_output.sh ms_restore_snapshot.sh ms_override_panel.sh ms_override_all.sh ms_reload_config.sh; do
    rm -f "/home/fpp/media/scripts/$script"
done

echo "fpp-matrixscroller uninstall complete"
