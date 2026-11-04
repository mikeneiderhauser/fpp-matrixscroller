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

# Settings (config/plugin.fpp-matrixscroller.json) and snapshots
# (plugindata/fpp-matrixscroller/) are kept, as FPP itself keeps plugin
# settings: FPP 10.3 and earlier don't tell a Reinstall from an uninstall,
# and "Reinstall All" after an OS upgrade would otherwise wipe them.

echo "fpp-matrixscroller uninstall complete"
