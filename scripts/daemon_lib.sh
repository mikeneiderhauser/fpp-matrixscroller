#!/bin/bash
# Shared daemon start/stop for the plugin's lifecycle scripts (sourced, not run).
#
# The daemon is found by its command line, not only the PID file: the web UI's
# Start button launches one without writing the PID file, and a PID file can
# outlive its process. FPP runs these scripts as root; run as another user they
# cannot signal a root daemon, so stopping reports failure rather than letting
# the caller start a second daemon beside it.

MS_PLUGIN_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MS_DAEMON="$MS_PLUGIN_DIR/matrixscroller.py"
MS_PIDFILE="/var/run/fppd/matrixscroller.pid"
MS_LOGFILE="/home/fpp/media/logs/fpp-matrixscroller.log"

# PIDs of running daemons (anchored so a shell whose command line merely
# mentions the path doesn't match)
ms_daemon_pids() {
    pgrep -f "^(/usr/bin/)?python3 $MS_DAEMON\$" || true
}

# Stop every running daemon. Returns 1 if any survive.
ms_stop_daemon() {
    local pids
    pids=$(ms_daemon_pids)
    if [ -n "$pids" ]; then
        echo "Stopping matrixscroller (PID $(echo $pids))..."
        kill $pids 2>/dev/null || true
        for _ in $(seq 1 20); do
            [ -z "$(ms_daemon_pids)" ] && break
            sleep 0.1
        done
        pids=$(ms_daemon_pids)
        if [ -n "$pids" ]; then
            kill -9 $pids 2>/dev/null || true
            sleep 0.2
        fi
    fi
    rm -f "$MS_PIDFILE" 2>/dev/null || true
    pids=$(ms_daemon_pids)
    if [ -n "$pids" ]; then
        echo "ERROR: could not stop matrixscroller (PID $(echo $pids), owner $(ps -o user= -p $(echo $pids | cut -d' ' -f1))); run as root" >&2
        return 1
    fi
}

# Start the daemon unless one is already running.
ms_start_daemon() {
    local pids
    pids=$(ms_daemon_pids)
    if [ -n "$pids" ]; then
        echo "matrixscroller already running (PID $(echo $pids))"
        return 0
    fi
    mkdir -p "$(dirname "$MS_PIDFILE")" "$(dirname "$MS_LOGFILE")"
    local commit
    commit=$(git -C "$MS_PLUGIN_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
    echo "Starting matrixscroller daemon @ $commit..."
    python3 "$MS_DAEMON" >> "$MS_LOGFILE" 2>&1 &
    echo $! > "$MS_PIDFILE"
    echo "matrixscroller started (PID $!)"
}
