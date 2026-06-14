#!/usr/bin/env bash
# Watchdog: restart acquisition container if no MQTT traffic for too long during daylight.
# When LOGGER_RESILIENCE_ENABLED=true, runs spaced LAN probes before restarting deye-bridge.
# Install via cron: */5 * * * * /path/to/bkw_tracker/scripts/healthcheck.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/stack.sh
source "${SCRIPT_DIR}/lib/stack.sh"

require_mqtt_env

TOPIC="${MQTT_TOPIC_PREFIX}/#"
STALE_SECONDS="${HEALTHCHECK_STALE_SECONDS:-600}"
BROKER_TIMEOUT="${BROKER_TIMEOUT:-15}"
CONTAINER="${CONTAINER:-deye-bridge}"
LATITUDE="${HEALTHCHECK_LATITUDE:-52.0}"
LONGITUDE="${HEALTHCHECK_LONGITUDE:-13.0}"

if command -v sunwait &>/dev/null; then
    if ! sunwait wait rise "$LATITUDE" "$LONGITUDE"; then
        exit 0
    fi
fi

payload="$(timeout "$BROKER_TIMEOUT" mosquitto_sub_cmd \
    -u "$MQTT_USER" -P "$MQTT_PASSWORD" \
    -t "$TOPIC" -C 1 -W "$STALE_SECONDS" 2>/dev/null || true)"

if [[ -z "$payload" ]]; then
    echo "$(date -Is) healthcheck: no MQTT on ${TOPIC} for ${STALE_SECONDS}s"
    should_restart=true
    if [[ "${LOGGER_RESILIENCE_ENABLED:-true}" == "true" ]] \
        && acquisition_adapter_enabled \
        && require_logger_env 2>/dev/null; then
        if "${SCRIPT_DIR}/stack.sh" probe --quiet; then
            echo "$(date -Is) healthcheck: logger reachable on LAN — restarting ${CONTAINER} to force read"
        else
            echo "$(date -Is) healthcheck: logger unreachable on LAN — skipping restart"
            should_restart=false
        fi
    fi
    if [[ "$should_restart" == true ]]; then
        docker restart "$CONTAINER"
    fi
else
    echo "$(date -Is) healthcheck: OK"
fi
