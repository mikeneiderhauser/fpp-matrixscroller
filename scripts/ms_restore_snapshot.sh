#!/bin/bash
# ms_restore_snapshot.sh — Restore a matrixscroller config snapshot
# Usage: ms_restore_snapshot.sh <snapshot-name>
#
# The snapshot name is the user-chosen name used when saving (without the
# plugin.fpp-matrixscroller.backup. prefix and .json suffix).
# Example: ms_restore_snapshot.sh my-show-config
#
# Add to a playlist via: Run Script > ms_restore_snapshot.sh, args: <name>

set -euo pipefail

NAME="${1:-}"
if [ -z "$NAME" ]; then
    echo "Usage: $0 <snapshot-name>"
    exit 1
fi

FILENAME="plugin.fpp-matrixscroller.backup.${NAME}.json"

curl -sf -X POST http://localhost/api/plugin/fpp-matrixscroller/restore \
    -H 'Content-Type: application/json' \
    -d "{\"filename\": \"$(echo "$FILENAME" | sed 's/"/\\"/g')\"}" \
    || { echo "ERROR: could not reach matrixscroller daemon"; exit 1; }

echo "matrixscroller restored snapshot: $NAME"
