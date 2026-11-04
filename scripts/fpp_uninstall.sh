#!/bin/bash

# fpp-matrixscroller uninstall script

. "$(dirname "$0")/daemon_lib.sh"

ms_stop_daemon

# Remove playlist scripts
for script in ms_enable_output.sh ms_restore_snapshot.sh ms_override_panel.sh ms_override_all.sh ms_reload_config.sh; do
    rm -f "/home/fpp/media/scripts/$script"
done

echo "fpp-matrixscroller uninstall complete"
