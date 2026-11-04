#!/bin/bash

# fpp-matrixscroller uninstall script (safe to run more than once)

. "$(dirname "$0")/daemon_lib.sh"

ms_stop_daemon

# Remove playlist scripts
for script in ms_enable_output.sh ms_restore_snapshot.sh ms_override_panel.sh ms_override_all.sh ms_reload_config.sh; do
    rm -f "$MS_MEDIADIR/scripts/$script"
done

# Left by versions that kept a PID file
rm -f /var/run/fppd/matrixscroller.pid

# Settings and snapshots survive a Reinstall (FPP 10.4+ sets
# FPP_PLUGIN_REINSTALL=1 for its uninstall half); any other uninstall,
# including a Reinstall on FPP 10.3 and earlier, removes them.
if [ "${FPP_PLUGIN_REINSTALL:-0}" != "1" ]; then
    rm -f "$MS_MEDIADIR/config/plugin.fpp-matrixscroller.json"
    rm -f "$MS_MEDIADIR/config/plugin.fpp-matrixscroller.backup."*.json
    rm -rf "$MS_MEDIADIR/plugindata/fpp-matrixscroller"
fi

echo "fpp-matrixscroller uninstall complete"
