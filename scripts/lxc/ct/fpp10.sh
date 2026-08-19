#!/usr/bin/env bash
# Copyright (c) 2024-2026 mikeneiderhauser
# Author: mikeneiderhauser
# License: MIT | https://github.com/mikeneiderhauser/fpp-matrixscroller/blob/master/LICENSE
# Source: https://github.com/FalconChristmas/fpp
#
# FPP 10.x is a DEVELOPMENT branch. Expect instability.
#
# Run on the Proxmox VE host:
#   bash <(curl -fsSL https://raw.githubusercontent.com/mikeneiderhauser/fpp-matrixscroller/master/scripts/lxc/ct/fpp10.sh)

RAW="https://raw.githubusercontent.com/mikeneiderhauser/fpp-matrixscroller/master/scripts/lxc"
source <(curl -fsSL "${RAW}/misc/helpers.sh")

APP="FPP10"
FPPBRANCH="10.x-master"
var_tags="${var_tags:-media;iot;lighting;development}"
var_cpu="${var_cpu:-2}"
var_ram="${var_ram:-2048}"
var_disk="${var_disk:-10}"
var_os="${var_os:-debian}"
var_version="${var_version:-13}"
var_unprivileged="${var_unprivileged:-0}"

INSTALL_SCRIPT_LOCAL="${INSTALL_SCRIPT_LOCAL:-}"
if [[ -z "${INSTALL_SCRIPT_LOCAL}" ]]; then
  curl -fsSL "${RAW}/install/fpp10-install.sh" -o /tmp/fpp10-install.sh
  INSTALL_SCRIPT_LOCAL="/tmp/fpp10-install.sh"
fi

header_info "$APP"
variables
color
catch_errors

function update_script() {
  header_info
  if [[ ! -d /opt/fpp ]]; then
    msg_error "No FPP Installation Found!"
    exit
  fi
  msg_info "Pulling latest ${FPPBRANCH}"
  $STD git -C /opt/fpp fetch --all
  $STD git -C /opt/fpp checkout "${FPPBRANCH}"
  $STD git -C /opt/fpp pull
  msg_ok "Pulled ${FPPBRANCH}"

  msg_info "Rebuilding FPP"
  $STD make -C /opt/fpp/src -j"$(nproc)" optimized
  msg_ok "Rebuilt FPP"

  msg_info "Restarting fppd"
  $STD systemctl restart fppd
  msg_ok "Restarted fppd"
  msg_ok "Updated successfully!"
  exit
}

start
build_container
description

CT_IP="$(pct exec "${CTID}" -- hostname -I 2>/dev/null | awk '{print $1}')"
msg_ok "Completed Successfully!\n"
echo -e "${CREATING}${GN}${APP} (development) setup has been successfully initialized!${CL}"
echo -e "${INFO}${YW} Access it using the following URL:${CL}"
echo -e "${TAB}${BGN}http://${CT_IP}${CL}"
echo ""
if [[ "${CT_PERSIST:-1}" == "1" ]]; then
  echo -e "${TAB}${INFO} Persist dir (survives container rebuild):${CL}"
  echo -e "${TAB}    ${PERSIST_BASE}/${CTID}/config/   <- FPP settings + plugin configs"
  echo -e "${TAB}    ${PERSIST_BASE}/${CTID}/plugins/  <- installed plugins"
  echo -e "${TAB}    ${PERSIST_BASE}/${CTID}/backups/  <- FPP backup ZIPs"
fi
echo ""
echo -e "${TAB}${INFO} Full container backup (run on Proxmox host):${CL}"
echo -e "${TAB}    vzdump ${CTID} --storage local --compress zstd --mode snapshot"
