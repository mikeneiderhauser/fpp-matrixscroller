#!/bin/bash
set -euo pipefail

# fpp-matrixscroller install script

PLUGIN_DIR=$(cd "$(dirname "$0")/.." && pwd)

chmod +x "$PLUGIN_DIR/plugin_event.sh"
chmod +x "$PLUGIN_DIR/matrixscroller.py"
chmod +x "$PLUGIN_DIR/scripts/fpp_uninstall.sh"

mkdir -p /home/fpp/media/logs
mkdir -p /home/fpp/media/config
mkdir -p /home/fpp/media/scripts
mkdir -p /var/run/fppd

# Deploy FPP playlist scripts
for script in ms_enable_output.sh ms_restore_snapshot.sh ms_override_panel.sh; do
    cp "$PLUGIN_DIR/scripts/$script" /home/fpp/media/scripts/
    chmod +x "/home/fpp/media/scripts/$script"
done
echo "Playlist scripts installed to /home/fpp/media/scripts"

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
        kill -0 "$PID" 2>/dev/null && kill -9 "$PID" || true
    fi
    rm -f "$PIDFILE"
fi

python3 "$PLUGIN_DIR/matrixscroller.py" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "fpp-matrixscroller daemon started (PID $!)"

echo "fpp-matrixscroller install complete"
