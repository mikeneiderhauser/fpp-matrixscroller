#!/bin/bash
# FPP command "Matrix Scroller - Panel": <panel id> <On|Off|Toggle>
. "$(dirname "$0")/common.sh"

[ -n "$1" ] || { echo "matrixscroller: a panel is required" >&2; exit 1; }
STATE=$(ms_state "${2:-On}") || exit 1
ms_post panel "{\"panel_id\": $(ms_json_string "$1"), \"enabled\": $STATE}"
