#!/bin/bash
# FPP command "Matrix Scroller - All Panels": <On|Off|Toggle>
. "$(dirname "$0")/common.sh"

STATE=$(ms_state "${1:-On}") || exit 1
ms_post output "{\"enable\": $STATE}"
