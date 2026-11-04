#!/bin/bash
#
# fpp-matrixscroller plugin event handler
# Called by FPP for lifecycle events
#

. "$(dirname "$0")/scripts/daemon_lib.sh"

case "$1" in
    fppd_start)
        ms_start_daemon
        ;;
    fppd_stop)
        ms_stop_daemon
        echo "matrixscroller stopped"
        ;;
    *)
        echo "Usage: $0 {fppd_start|fppd_stop}"
        echo "Event received: $1"
        ;;
esac
