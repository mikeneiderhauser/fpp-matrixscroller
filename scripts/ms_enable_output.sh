#!/bin/bash
# ms_enable_output.sh — Enable or disable matrixscroller overlay output
# Usage: ms_enable_output.sh <1|0>
#   1 = enable output
#   0 = disable output
#
# Add to a playlist via: Run Script > ms_enable_output.sh, args: 1

set -euo pipefail

ENABLE="${1:-}"
if [[ "$ENABLE" != "0" && "$ENABLE" != "1" ]]; then
    echo "Usage: $0 <1|0>"
    exit 1
fi

curl -sf --connect-timeout 3 --max-time 5 -X POST http://localhost/api/plugin/fpp-matrixscroller/output \
    -H 'Content-Type: application/json' \
    -d "{\"enable\": $([ "$ENABLE" = "1" ] && echo true || echo false)}" \
    || { echo "ERROR: could not reach matrixscroller daemon"; exit 1; }

echo "matrixscroller output $([ "$ENABLE" = "1" ] && echo enabled || echo disabled)"
