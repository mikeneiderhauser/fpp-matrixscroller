#!/bin/bash
# Shared daemon start/stop for the plugin's lifecycle scripts (sourced, not run).
#
# The daemon is found by its command line, so nothing needs a PID file: that
# also finds one the web UI's Start button launched. FPP runs these scripts as
# root; run as another user they cannot signal a root daemon, so stopping
# reports failure rather than letting the caller start a second daemon beside it.

MS_PLUGIN_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MS_DAEMON="$MS_PLUGIN_DIR/matrixscroller.py"
# FPP provides MEDIADIR/LOGDIR; fall back to the default install paths
MS_MEDIADIR="${MEDIADIR:-/home/fpp/media}"
MS_LOGDIR="${LOGDIR:-$MS_MEDIADIR/logs}"
MS_LOGFILE="$MS_LOGDIR/plugin-fpp-matrixscroller.log"

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
    mkdir -p "$MS_LOGDIR"
    local commit
    commit=$(git -C "$MS_PLUGIN_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
    echo "Starting matrixscroller daemon @ $commit..."
    # The daemon writes its own log; this only catches a crash traceback
    MEDIADIR="$MS_MEDIADIR" LOGDIR="$MS_LOGDIR" python3 "$MS_DAEMON" >> "$MS_LOGFILE" 2>&1 &
    echo "matrixscroller started (PID $!)"
}
