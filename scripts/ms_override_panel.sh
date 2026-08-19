#!/bin/bash
# ms_override_panel.sh — Set or clear a message override on a matrixscroller panel
# Usage: ms_override_panel.sh <panel_id> [message]
#
#   panel_id : panel ID string as shown in the plugin UI (e.g. panel_1, panel_2)
#   message  : text to display; omit or leave blank to clear the override
#
# Examples:
#   ms_override_panel.sh panel_1 "Show starts soon!"   # set override
#   ms_override_panel.sh panel_1                        # clear override
#
# Add to a playlist via: Run Script > ms_override_panel.sh, args: <id> [msg]

set -euo pipefail

PANEL_ID="${1:-}"
if [ -z "$PANEL_ID" ]; then
    echo "Usage: $0 <panel_id> [message]"
    exit 1
fi

MESSAGE="${2:-}"

if [ -z "$MESSAGE" ]; then
    BODY="{\"panel_id\": \"$PANEL_ID\", \"message\": null}"
    ACTION="cleared"
else
    ESCAPED=$(printf '%s' "$MESSAGE" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))")
    BODY="{\"panel_id\": \"$PANEL_ID\", \"message\": $ESCAPED}"
    ACTION="set to: $MESSAGE"
fi

curl -sf -X POST http://localhost/api/plugin/fpp-matrixscroller/message \
    -H 'Content-Type: application/json' \
    -d "$BODY" \
    || { echo "ERROR: could not reach matrixscroller daemon"; exit 1; }

echo "matrixscroller panel $PANEL_ID override $ACTION"
