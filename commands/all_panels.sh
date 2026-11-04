#!/bin/bash
# FPP command "Matrix Scroller - All Panels State": <On|Off|Toggle> (the global Enable Output switch)
. "$(dirname "$0")/common.sh"

STATE=$(ms_state "${1:-On}") || exit 1
ms_post output "{\"enable\": $STATE}"
