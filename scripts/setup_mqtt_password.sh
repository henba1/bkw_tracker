#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASSWD_FILE="${ROOT}/mosquitto/config/passwd"
USER="solar"

mkdir -p "$(dirname "$PASSWD_FILE")"

if [[ -f "$PASSWD_FILE" ]]; then
    echo "Updating password for existing user '${USER}' in ${PASSWD_FILE}"
    docker run --rm -it \
        -v "${PASSWD_FILE}:/mosquitto/config/passwd" \
        eclipse-mosquitto:2 \
        mosquitto_passwd /mosquitto/config/passwd "$USER"
else
    echo "Creating MQTT user '${USER}' in ${PASSWD_FILE}"
    docker run --rm -it \
        -v "${PASSWD_FILE}:/mosquitto/config/passwd" \
        eclipse-mosquitto:2 \
        mosquitto_passwd -c /mosquitto/config/passwd "$USER"
fi

chmod 600 "$PASSWD_FILE"
echo "Done. Copy the same password into deye-bridge/config.env → MQTT_PASSWORD"
