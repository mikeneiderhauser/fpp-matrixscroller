#!/bin/bash
set -euo pipefail

# fpp-matrixscroller install script (FPP runs it as root)

PLUGIN_DIR=$(cd "$(dirname "$0")/.." && pwd)
. "$PLUGIN_DIR/scripts/daemon_lib.sh"

chmod +x "$PLUGIN_DIR/plugin_event.sh"
chmod +x "$PLUGIN_DIR/matrixscroller.py"
chmod +x "$PLUGIN_DIR/scripts/fpp_uninstall.sh"
# fppd runs these directly (FPP commands and the callbacks script)
chmod +x "$PLUGIN_DIR/callbacks.sh" "$PLUGIN_DIR"/commands/*.sh

mkdir -p "$MS_LOGDIR"
mkdir -p "$MS_MEDIADIR/config"
mkdir -p "$MS_MEDIADIR/scripts"

# Left by versions that kept a PID file
rm -f /var/run/fppd/matrixscroller.pid

# Deploy FPP playlist scripts
for script in ms_enable_output.sh ms_restore_snapshot.sh ms_override_panel.sh ms_override_all.sh ms_reload_config.sh; do
    cp "$PLUGIN_DIR/scripts/$script" "$MS_MEDIADIR/scripts/"
    chmod +x "$MS_MEDIADIR/scripts/$script"
done
echo "Playlist scripts installed to $MS_MEDIADIR/scripts"

# Restart the daemon so it picks up the new code. If the old one can't be
# stopped (run by hand as a user other than root), fail rather than start a
# second daemon beside it.
ms_stop_daemon
ms_start_daemon

echo "fpp-matrixscroller install complete"
