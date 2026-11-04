#!/bin/bash
# FPP command "Matrix Scroller - Restore Snapshot": <snapshot filename or name>
. "$(dirname "$0")/common.sh"

[ -n "$1" ] || { echo "matrixscroller: a snapshot is required" >&2; exit 1; }
FILE="$1"
# Accept the bare name too (what ms_restore_snapshot.sh takes)
case "$FILE" in
    plugin.fpp-matrixscroller.backup.*.json) ;;
    *) FILE="plugin.fpp-matrixscroller.backup.${FILE}.json" ;;
esac
ms_post restore "{\"filename\": $(ms_json_string "$FILE")}"
