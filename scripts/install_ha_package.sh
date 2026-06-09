#!/usr/bin/env bash
# Install solar package into the running homeassistant Docker container (Phase 3 & 4).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/stack.sh
source "${SCRIPT_DIR}/lib/stack.sh"

RESTART_HA=false
for arg in "$@"; do
    case "$arg" in
        --restart) RESTART_HA=true ;;
        -h | --help)
            echo "Usage: $0 [--restart]"
            echo "  --restart  restart homeassistant container after install"
            exit 0
            ;;
    esac
done

require_mqtt_env
export HA_ENTITY_SLUG
HA_ENTITY_SLUG="${HA_ENTITY_SLUG:-$(slugify_ha_entity_slug "${HA_INVERTER_MANUFACTURER:-Solar}" "${HA_INVERTER_MODEL:-Inverter}")}"

HA_CONFIG="$(resolve_ha_config || true)"
if [[ -z "$HA_CONFIG" ]]; then
    echo "Could not resolve HA config directory." >&2
    echo "Set HA_CONFIG in ${STACK_ENV_FILE} or start container ${HA_CONTAINER:-homeassistant}." >&2
    exit 1
fi

HA_CONTAINER="${HA_CONTAINER:-homeassistant}"
echo "Home Assistant config: ${HA_CONFIG} (container: ${HA_CONTAINER})"

HA_USE_SUDO=""
if [[ ! -w "$HA_CONFIG" ]]; then
    if command -v sudo &>/dev/null; then
        HA_USE_SUDO=sudo
        echo "Using sudo for writes under ${HA_CONFIG}"
    else
        echo "No write permission for ${HA_CONFIG} and sudo not available." >&2
        exit 1
    fi
fi

ha_mkdir() { ${HA_USE_SUDO} mkdir -p "$@"; }
ha_cp() { ${HA_USE_SUDO} cp "$@"; }
ha_tee_append() { ${HA_USE_SUDO} tee -a "$@"; }
ha_python() {
    if [[ -n "$HA_USE_SUDO" ]]; then
        ${HA_USE_SUDO} python3 - "$@"
    else
        python3 - "$@"
    fi
}

"${SCRIPT_DIR}/stack.sh" render

ha_mkdir "${HA_CONFIG}/packages" "${HA_CONFIG}/dashboards" "${HA_CONFIG}/scripts" "${HA_CONFIG}/exports"
ha_cp "${STACK_ROOT}/homeassistant/packages/solar.yaml" "${HA_CONFIG}/packages/solar.yaml"
ha_cp "${STACK_ROOT}/homeassistant/packages/solar_computed.yaml" "${HA_CONFIG}/packages/solar_computed.yaml"
ha_cp "${STACK_ROOT}/homeassistant/packages/solar_export.yaml" "${HA_CONFIG}/packages/solar_export.yaml"
ha_cp "${STACK_ROOT}/homeassistant/lovelace/solar.yaml" "${HA_CONFIG}/dashboards/solar.yaml"
ha_cp "${STACK_ROOT}/homeassistant/scripts/export_solar_csv.py" "${HA_CONFIG}/scripts/export_solar_csv.py"
ha_cp "${STACK_ROOT}/homeassistant/scripts/solar_baseline_value.py" "${HA_CONFIG}/scripts/solar_baseline_value.py"
${HA_USE_SUDO} chmod +x "${HA_CONFIG}/scripts/export_solar_csv.py" 2>/dev/null || chmod +x "${HA_CONFIG}/scripts/export_solar_csv.py"
${HA_USE_SUDO} chmod +x "${HA_CONFIG}/scripts/solar_baseline_value.py" 2>/dev/null || chmod +x "${HA_CONFIG}/scripts/solar_baseline_value.py"

config_file="${HA_CONFIG}/configuration.yaml"
if ! grep -q 'packages: !include_dir_named packages' "$config_file" 2>/dev/null; then
    cat <<'EOF' | ha_tee_append "$config_file" >/dev/null

# bkw_tracker solar package
homeassistant:
  packages: !include_dir_named packages
EOF
    echo "Enabled packages in configuration.yaml"
fi

if ! grep -q 'filename: dashboards/solar.yaml' "$config_file" 2>/dev/null; then
    cat <<'EOF' | ha_tee_append "$config_file" >/dev/null

# bkw_tracker solar Lovelace dashboard (url path must contain a hyphen)
lovelace:
  mode: storage
  dashboards:
    solar-panel:
      mode: yaml
      title: Solar
      icon: mdi:solar-power
      show_in_sidebar: true
      filename: dashboards/solar.yaml
EOF
    echo "Registered Solar Lovelace dashboard in configuration.yaml"
fi

echo ""
echo "Installed:"
echo "  ${HA_CONFIG}/packages/solar.yaml"
echo "  ${HA_CONFIG}/packages/solar_computed.yaml"
echo "  ${HA_CONFIG}/packages/solar_export.yaml"
echo "  ${HA_CONFIG}/dashboards/solar.yaml"
echo "  ${HA_CONFIG}/scripts/export_solar_csv.py"
echo ""
echo "MQTT broker for HA: ${MQTT_BROKER_HOST:-127.0.0.1}:${MQTT_PORT} (host-network container → localhost)"

if ! sudo python3 "${SCRIPT_DIR}/configure_ha_mqtt.py" 2>/dev/null; then
    python3 "${SCRIPT_DIR}/configure_ha_mqtt.py" || {
        echo "Could not auto-configure MQTT — run: ./scripts/configure_ha_mqtt.sh" >&2
    }
fi

if [[ "$RESTART_HA" == true ]]; then
    echo "Restarting ${HA_CONTAINER}..."
    docker restart "$HA_CONTAINER"
    echo "Done. Energy Dashboard: lifetime → sensor.${HA_ENTITY_SLUG}_solar_total_energy;"
    echo "  today → sensor.solar_today_energy_computed (inverter day_energy may be unreliable)"
else
    echo "Apply config: docker restart ${HA_CONTAINER}"
    echo "Then Energy Dashboard: lifetime → sensor.${HA_ENTITY_SLUG}_solar_total_energy;"
    echo "  today → sensor.solar_today_energy_computed"
fi
