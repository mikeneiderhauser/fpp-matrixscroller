#!/bin/bash
# FPP command "Matrix Scroller - Show Message": <panel id | all> <message> [duration seconds]
. "$(dirname "$0")/common.sh"

PANEL="${1:-all}"
[ -n "$2" ] || { echo "matrixscroller: a message is required" >&2; exit 1; }
MESSAGE=$(ms_json_string "$2")
DURATION="${3:-0}"
case "$DURATION" in ''|*[!0-9]*) DURATION=0 ;; esac

if [ "$PANEL" = "all" ]; then
    ms_post message/all "{\"message\": $MESSAGE, \"duration\": $DURATION}"
else
    ms_post message "{\"panel_id\": $(ms_json_string "$PANEL"), \"message\": $MESSAGE, \"duration\": $DURATION}"
fi
