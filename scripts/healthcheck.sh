#!/usr/bin/env bash
# Watchdog: restart deye-bridge if no MQTT traffic on solar/# for too long during daylight.
# Install via cron: */5 * * * * /path/to/bkw_tracker/scripts/healthcheck.sh

set -euo pipefail

MQTT_HOST="${MQTT_HOST:-192.168.178.52}"
MQTT_USER="${MQTT_USER:-solar}"
MQTT_PASSWORD="${MQTT_PASSWORD:?Set MQTT_PASSWORD}"
TOPIC="${MQTT_TOPIC:-solar/#}"
STALE_SECONDS="${STALE_SECONDS:-600}"
BROKER_TIMEOUT="${BROKER_TIMEOUT:-15}"
CONTAINER="${CONTAINER:-deye-bridge}"
LATITUDE="${LATITUDE:-52.0}"
LONGITUDE="${LONGITUDE:-13.0}"

if command -v sunwait &>/dev/null; then
    if ! sunwait wait rise "$LATITUDE" "$LONGITUDE"; then
        exit 0
    fi
fi

payload="$(timeout "$BROKER_TIMEOUT" mosquitto_sub \
    -h "$MQTT_HOST" -u "$MQTT_USER" -P "$MQTT_PASSWORD" \
    -t "$TOPIC" -C 1 -W "$STALE_SECONDS" 2>/dev/null || true)"

if [[ -z "$payload" ]]; then
    echo "$(date -Is) healthcheck: no MQTT on ${TOPIC} for ${STALE_SECONDS}s — restarting ${CONTAINER}"
    docker restart "$CONTAINER"
else
    echo "$(date -Is) healthcheck: OK"
fi
