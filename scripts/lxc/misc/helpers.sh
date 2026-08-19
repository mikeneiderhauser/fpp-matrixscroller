#!/usr/bin/env bash
# misc/helpers.sh — Community-scripts-compatible helper functions for FPP LXC scripts
# Sourced by both ct/ scripts (on Proxmox host) and install/ scripts (inside container).

# ──────────────────────────────────────────────────────────────────────────────
# Colors
# ──────────────────────────────────────────────────────────────────────────────
BL='\033[36m'
RD='\033[01;31m'
GN='\033[1;92m'
YW='\033[33m'
CL='\033[m'
BGN='\033[4;92m'
GRN='\033[0;92m'
CM='\xE2\x9C\x94\033[0;92m'
CROSS='\033[1;31m\xE2\x9C\x97'
INFO='\033[1;33m\xe2\x84\xb9\033[0m'
TAB="  "
CREATING='\033[1;33m'

STD=">/dev/null 2>&1"

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
msg_info() {
  echo -ne "${TAB}${YW}${INFO} ${1}...${CL}\r"
}

msg_ok() {
  echo -e "${TAB}${GN}${CM} ${1}${CL}"
}

msg_error() {
  echo -e "${TAB}${RD}${CROSS} ${1}${CL}"
}

# ──────────────────────────────────────────────────────────────────────────────
# CT-side helpers (run on Proxmox host)
# ──────────────────────────────────────────────────────────────────────────────

header_info() {
  local app="${1:-FPP}"
  clear
  echo -e "${BL}
    ______   ____  ____
   / ____/  / __ \/ __ \\
  / /_     / /_/ / /_/ /
 / __/    / ____/ ____/
/_/      /_/   /_/
${CL}"
  echo -e "${GN}  Falcon Player (${app}) — Proxmox LXC Setup${CL}"
  echo -e "${YW}  https://falconchristmas.com${CL}"
  echo ""
}

variables() {
  NSAPP="${NSAPP:-${APP,,}}"
  NSAPP="${NSAPP// /-}"
  CT_CPU="${var_cpu:-2}"
  CT_RAM="${var_ram:-2048}"
  CT_DISK="${var_disk:-10}"
  CT_OS="${var_os:-debian}"
  CT_VER="${var_version:-12}"
  CT_UNPRIVILEGED="${var_unprivileged:-0}"
  CT_STORAGE="${CT_STORAGE:-local-lvm}"
  CT_BRIDGE="${CT_BRIDGE:-vmbr0}"
  CT_TEMPLATE_STORAGE="${CT_TEMPLATE_STORAGE:-local}"
  # Persistence: host base dir for bind-mounted FPP data
  PERSIST_BASE="${PERSIST_BASE:-/var/lib/fpp-persist}"
  CT_PERSIST="${CT_PERSIST:-1}"   # 1 = enabled (default), 0 = disabled
}

color()        { :; }
catch_errors() { set -euo pipefail; }

_next_ctid() {
  pvesh get /cluster/nextid 2>/dev/null || echo "200"
}

_ensure_template() {
  local tmpl
  msg_info "Checking for ${CT_OS^} ${CT_VER} template"
  pveam update &>/dev/null
  tmpl="$(pveam available --section system 2>/dev/null \
    | awk '{print $2}' \
    | grep "^${CT_OS}-${CT_VER}-standard.*amd64" \
    | sort -V | tail -1)"
  [[ -n "${tmpl}" ]] || { msg_error "No ${CT_OS}-${CT_VER}-standard template found"; exit 1; }

  if ! pveam list "${CT_TEMPLATE_STORAGE}" 2>/dev/null | grep -q "${tmpl}"; then
    msg_info "Downloading ${tmpl}"
    pveam download "${CT_TEMPLATE_STORAGE}" "${tmpl}" &>/dev/null \
      || { msg_error "Template download failed"; exit 1; }
  fi
  msg_ok "${tmpl}"
  echo "${tmpl}"
}

_prompt_container_settings() {
  local auto_ctid
  auto_ctid="$(_next_ctid)"

  echo ""
  read -rp "${TAB}Container ID [${auto_ctid}]: " CTID
  CTID="${CTID:-${auto_ctid}}"

  read -rp "${TAB}Hostname [${NSAPP}]: " CT_HOSTNAME
  CT_HOSTNAME="${CT_HOSTNAME:-${NSAPP}}"

  echo ""
  echo -e "${TAB}${INFO} Network: static IP (e.g. 192.168.250.90/24) or Enter for DHCP"
  read -rp "${TAB}IP address [dhcp]: " CT_IP_INPUT
  CT_IP_INPUT="${CT_IP_INPUT:-dhcp}"

  if [[ "${CT_IP_INPUT}" != "dhcp" ]]; then
    read -rp "${TAB}Gateway [192.168.250.1]: " CT_GW
    CT_GW="${CT_GW:-192.168.250.1}"
    CT_NET="name=eth0,bridge=${CT_BRIDGE},ip=${CT_IP_INPUT},gw=${CT_GW},firewall=0"
  else
    CT_NET="name=eth0,bridge=${CT_BRIDGE},ip=dhcp,firewall=0"
  fi

  echo ""
  read -rp "${TAB}Storage [${CT_STORAGE}]: " _in; CT_STORAGE="${_in:-${CT_STORAGE}}"
  read -rp "${TAB}CPU cores [${CT_CPU}]: "  _in; CT_CPU="${_in:-${CT_CPU}}"
  read -rp "${TAB}RAM MB   [${CT_RAM}]: "   _in; CT_RAM="${_in:-${CT_RAM}}"
  read -rp "${TAB}Disk GB  [${CT_DISK}]: "  _in; CT_DISK="${_in:-${CT_DISK}}"

  echo ""
  local persist_default="y"
  [[ "${CT_PERSIST}" == "0" ]] && persist_default="n"
  read -rp "${TAB}Enable config persistence (bind mounts)? [${persist_default^^}/${persist_default^^/y/n}]: " _in
  _in="${_in:-${persist_default}}"
  [[ "${_in,,}" == "y" ]] && CT_PERSIST=1 || CT_PERSIST=0
}

_confirm() {
  local tmpl="$1"
  local persist_dir="${PERSIST_BASE}/${CTID}"
  echo ""
  echo -e "${BL}  ─────────────────────────────────────────────────${CL}"
  echo -e "${GN}  Container Summary${CL}"
  echo -e "${BL}  ─────────────────────────────────────────────────${CL}"
  echo -e "${TAB}CTID:        ${GN}${CTID}${CL}"
  echo -e "${TAB}Hostname:    ${GN}${CT_HOSTNAME}${CL}"
  echo -e "${TAB}App:         ${GN}${APP} (${FPPBRANCH})${CL}"
  echo -e "${TAB}Template:    ${GN}${tmpl}${CL}"
  echo -e "${TAB}Network:     ${GN}${CT_NET}${CL}"
  echo -e "${TAB}Storage:     ${GN}${CT_STORAGE} (${CT_DISK}GB)${CL}"
  echo -e "${TAB}CPU/RAM:     ${GN}${CT_CPU} cores / ${CT_RAM}MB${CL}"
  echo -e "${TAB}Mode:        ${YW}Privileged (required by FPP)${CL}"
  if [[ "${CT_PERSIST}" == "1" ]]; then
    echo -e "${TAB}Persistence: ${GN}enabled${CL}"
    echo -e "${TAB}  config  →  ${GN}${persist_dir}/config${CL}"
    echo -e "${TAB}  plugins →  ${GN}${persist_dir}/plugins${CL}"
  else
    echo -e "${TAB}Persistence: ${YW}disabled${CL}"
  fi
  echo -e "${BL}  ─────────────────────────────────────────────────${CL}"
  echo ""
  read -rp "${TAB}Create container? [y/N]: " _CONFIRM
  [[ "${_CONFIRM,,}" == "y" ]] || { echo ""; msg_info "Aborted"; echo ""; exit 0; }
}

# Set up bind mounts for FPP config and plugins on the Proxmox host.
# Called BEFORE container start so FPP installs directly into persistent dirs.
_setup_persist_mounts() {
  local persist_dir="${PERSIST_BASE}/${CTID}"

  msg_info "Creating persistence directories at ${persist_dir}"
  mkdir -p "${persist_dir}/config" "${persist_dir}/plugins" "${persist_dir}/backups"
  msg_ok "Created ${persist_dir}"

  msg_info "Configuring bind mounts (CTID ${CTID})"
  pct set "${CTID}" \
    --mp0 "${persist_dir}/config,mp=/home/fpp/media/config"   \
    --mp1 "${persist_dir}/plugins,mp=/home/fpp/media/plugins" \
    --mp2 "${persist_dir}/backups,mp=/home/fpp/media/backups"
  msg_ok "Bind mounts configured"

  echo ""
  echo -e "${TAB}${INFO} Persist layout on Proxmox host:${CL}"
  echo -e "${TAB}  ${persist_dir}/config/   → /home/fpp/media/config   (FPP settings, plugin configs)"
  echo -e "${TAB}  ${persist_dir}/plugins/  → /home/fpp/media/plugins  (installed plugins)"
  echo -e "${TAB}  ${persist_dir}/backups/  → /home/fpp/media/backups  (FPP backup ZIPs)"
  echo ""
}

build_container() {
  [[ "$(id -u)" -eq 0 ]] || { msg_error "Must run as root on Proxmox VE host"; exit 1; }
  command -v pct &>/dev/null || { msg_error "pct not found — run on Proxmox VE host"; exit 1; }

  local tmpl
  tmpl="$(_ensure_template)"
  _prompt_container_settings
  _confirm "${tmpl}"

  msg_info "Creating LXC container ${CTID}"
  pct create "${CTID}" "${CT_TEMPLATE_STORAGE}:vztmpl/${tmpl}" \
    --hostname     "${CT_HOSTNAME}"          \
    --cores        "${CT_CPU}"               \
    --memory       "${CT_RAM}"               \
    --swap         512                       \
    --rootfs       "${CT_STORAGE}:${CT_DISK}" \
    --net0         "${CT_NET}"               \
    --nameserver   "1.1.1.1"                 \
    --features     "nesting=1"               \
    --unprivileged "${CT_UNPRIVILEGED}"       \
    --onboot       1 &>/dev/null
  msg_ok "Created container ${CTID}"

  # Bind mounts must be added BEFORE first start so FPP installs into them
  if [[ "${CT_PERSIST}" == "1" ]]; then
    _setup_persist_mounts
  fi

  msg_info "Starting container ${CTID}"
  pct start "${CTID}"
  local i
  for i in $(seq 1 20); do
    pct exec "${CTID}" -- test -f /etc/os-release 2>/dev/null && break
    sleep 2
  done
  msg_ok "Container is running"

  msg_info "Pushing install script"
  pct push "${CTID}" "${INSTALL_SCRIPT_LOCAL}" /root/install.sh
  pct exec "${CTID}" -- chmod +x /root/install.sh
  msg_ok "Install script ready"

  msg_info "Running FPP install (this takes 15–30 minutes)"
  echo ""
  pct exec "${CTID}" -- bash /root/install.sh "${FPPBRANCH}" "${APP}"
}

description() {
  local persist_dir="${PERSIST_BASE}/${CTID}"
  local persist_note=""
  [[ "${CT_PERSIST:-1}" == "1" ]] && \
    persist_note=$'\nPersist: '"${persist_dir}"

  pct set "${CTID}" --description "# ${APP}
Falcon Player ${FPPBRANCH}
Branch: ${FPPBRANCH}
OS: ${CT_OS} ${CT_VER}${persist_note}" 2>/dev/null || true
}

start() { :; }

# Create a Proxmox vzdump backup of the container.
# Usage: backup_container [storage]
backup_container() {
  local bk_storage="${1:-local}"
  msg_info "Creating vzdump backup of CT ${CTID} to ${bk_storage}"
  vzdump "${CTID}" --storage "${bk_storage}" --compress zstd --mode snapshot \
    || vzdump "${CTID}" --storage "${bk_storage}" --compress zstd --mode stop
  msg_ok "Backup complete"
}

# ──────────────────────────────────────────────────────────────────────────────
# Install-side helpers (run inside the LXC container)
# ──────────────────────────────────────────────────────────────────────────────

verb_ip6()             { :; }
setting_up_container() { :; }
customize()            { :; }

network_check() {
  local i
  for i in $(seq 1 5); do
    curl -fsSL --max-time 5 https://raw.githubusercontent.com &>/dev/null && return
    sleep 3
  done
  msg_error "No internet access — check container network"
  exit 1
}

update_os() {
  msg_info "Updating OS"
  export DEBIAN_FRONTEND=noninteractive
  $STD apt update
  $STD apt -y upgrade
  msg_ok "Updated OS"
}

motd_ssh() {
  echo "${APP:-FPP} (Falcon Player ${FPPBRANCH:-})" >/etc/motd
}

cleanup_lxc() {
  msg_info "Cleaning up"
  $STD apt -y autoremove
  $STD apt -y autoclean
  msg_ok "Cleaned up"
}
