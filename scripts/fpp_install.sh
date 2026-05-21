#!/bin/bash

# fpp-matrixscroller install script

. ${FPPDIR}/scripts/common

PLUGIN_DIR=$(cd "$(dirname "$0")/.." && pwd)

chmod +x "$PLUGIN_DIR/plugin_event.sh"
chmod +x "$PLUGIN_DIR/matrixscroller.py"
chmod +x "$PLUGIN_DIR/scripts/postStart.sh"
chmod +x "$PLUGIN_DIR/scripts/postStop.sh"
chmod +x "$PLUGIN_DIR/scripts/fpp_uninstall.sh"

mkdir -p /home/fpp/media/logs
mkdir -p /home/fpp/media/config

echo "fpp-matrixscroller install complete"
