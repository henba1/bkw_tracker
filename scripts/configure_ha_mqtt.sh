#!/usr/bin/env bash
# Configure MQTT broker for homeassistant (HA 2024+ — config entry, not YAML).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if command -v sudo &>/dev/null; then
    sudo python3 "${SCRIPT_DIR}/configure_ha_mqtt.py" "$@"
else
    python3 "${SCRIPT_DIR}/configure_ha_mqtt.py" "$@"
fi
