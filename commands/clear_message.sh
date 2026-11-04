#!/bin/bash
# FPP command "Matrix Scroller - Clear Message": <panel id | all>
. "$(dirname "$0")/common.sh"

PANEL="${1:-all}"
if [ "$PANEL" = "all" ]; then
    ms_post message/all '{"message": null}'
else
    ms_post message "{\"panel_id\": $(ms_json_string "$PANEL"), \"message\": null}"
fi
