#!/bin/bash
set -euo pipefail

# fpp-matrixscroller install script

# FPP runs this as root. Run by hand as fpp, it couldn't stop the root daemon
# FPP started, so become root the same way when sudo allows it.
if [ "$(id -u)" -ne 0 ] && sudo -n true 2>/dev/null; then
    exec sudo -n bash "$0" "$@"
fi

PLUGIN_DIR=$(cd "$(dirname "$0")/.." && pwd)
. "$PLUGIN_DIR/scripts/daemon_lib.sh"

chmod +x "$PLUGIN_DIR/plugin_event.sh"
chmod +x "$PLUGIN_DIR/matrixscroller.py"
chmod +x "$PLUGIN_DIR/scripts/fpp_uninstall.sh"

mkdir -p /home/fpp/media/logs
mkdir -p /home/fpp/media/config
mkdir -p /home/fpp/media/scripts
mkdir -p /var/run/fppd

# Deploy FPP playlist scripts
for script in ms_enable_output.sh ms_restore_snapshot.sh ms_override_panel.sh ms_override_all.sh ms_reload_config.sh; do
    cp "$PLUGIN_DIR/scripts/$script" /home/fpp/media/scripts/
    chmod +x "/home/fpp/media/scripts/$script"
done
echo "Playlist scripts installed to /home/fpp/media/scripts"

# Restart the daemon so it picks up the new code. If the old one can't be
# stopped, fail rather than start a second daemon beside it.
ms_stop_daemon
ms_start_daemon

echo "fpp-matrixscroller install complete"
