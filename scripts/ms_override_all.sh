#!/bin/bash
# ms_override_all.sh — Set or clear a message override on ALL matrixscroller panels
# Usage: ms_override_all.sh [message]
#
# Sets the same manual message override on every configured panel simultaneously,
# bypassing the normal media/no-media logic. Omit the message to clear all overrides
# and return every panel to its normal operating mode.
#
# Examples:
#   ms_override_all.sh "Show starts in 5 minutes!"   # set override on all panels
#   ms_override_all.sh                                # clear all overrides
#
# Add to a playlist via: Run Script > ms_override_all.sh, args: [message]

set -euo pipefail

MESSAGE="${1:-}"

if [ -z "$MESSAGE" ]; then
    BODY='{"message": null}'
    ACTION="cleared on all panels"
else
    ESCAPED=$(printf '%s' "$MESSAGE" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))")
    BODY="{\"message\": $ESCAPED}"
    ACTION="set to: $MESSAGE on all panels"
fi

curl -sf --connect-timeout 3 --max-time 5 -X POST http://localhost/api/plugin/fpp-matrixscroller/message/all \
    -H 'Content-Type: application/json' \
    -d "$BODY" \
    || { echo "ERROR: could not reach matrixscroller daemon"; exit 1; }

echo "matrixscroller override $ACTION"
