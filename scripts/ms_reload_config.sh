#!/bin/bash
# ms_reload_config.sh — Reload the matrixscroller config from disk without restarting the daemon
# Usage: ms_reload_config.sh
#
# Tells the running daemon to re-read its config file from disk and apply the
# changes immediately. Useful if you have edited the config JSON on disk directly
# and want the changes to take effect without a full daemon restart.
#
# Note: restoring a config snapshot via the UI or the ms_restore_snapshot.sh script
# already applies the new config live — this script is not needed after a snapshot restore.
#
# Add to a playlist via: Run Script > ms_reload_config.sh, args: (none)

set -euo pipefail

curl -sf -X POST http://localhost/api/plugin/fpp-matrixscroller/reload \
    -H 'Content-Type: application/json' \
    || { echo "ERROR: could not reach matrixscroller daemon"; exit 1; }

echo "matrixscroller config reloaded from disk"
