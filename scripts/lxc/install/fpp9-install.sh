#!/usr/bin/env bash
# Copyright (c) 2024-2026 mikeneiderhauser
# Author: mikeneiderhauser
# License: MIT | https://github.com/mikeneiderhauser/fpp-matrixscroller/blob/master/LICENSE
# Source: https://github.com/FalconChristmas/fpp
#
# Runs INSIDE the LXC container. Called automatically by ct/fpp9.sh.

FPPBRANCH="${1:-9.5.3}"
APP="${2:-FPP9}"

RAW="https://raw.githubusercontent.com/mikeneiderhauser/fpp-matrixscroller/master/scripts/lxc"
source <(curl -fsSL "${RAW}/misc/helpers.sh")

color
verb_ip6
catch_errors
setting_up_container
network_check
update_os

msg_info "Downloading FPP Installer"
$STD curl -fsSL \
  "https://raw.githubusercontent.com/FalconChristmas/fpp/master/SD/FPP_Install.sh" \
  -o /tmp/FPP_Install.sh
chmod 700 /tmp/FPP_Install.sh
msg_ok "Downloaded FPP Installer"

msg_info "Installing FPP ${FPPBRANCH} (Patience)"
export FPPBRANCH
bash /tmp/FPP_Install.sh
msg_ok "Installed FPP"

msg_info "Enabling fppd service"
$STD systemctl enable fppd.service
$STD systemctl start  fppd.service
msg_ok "Enabled fppd"

motd_ssh
customize
cleanup_lxc
