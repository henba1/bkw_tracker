#!/usr/bin/env bash
# Interactive first-time setup for non-technical users.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/stack.sh
source "${SCRIPT_DIR}/lib/stack.sh"

say() { printf '%s\n' "$*"; }
pause() { say ""; read -r -p "Press Enter to continue..." _; }

require_docker() {
    if ! command -v docker &>/dev/null; then
        say "Docker is required but not installed."
        say "Install Docker, then run this script again."
        exit 1
    fi
}

prompt_password() {
    local pw1 pw2
    while true; do
        read -r -s -p "Choose an MQTT password (min. 8 characters): " pw1
        say ""
        if ((${#pw1} < 8)); then
            say "Too short — please use at least 8 characters."
            continue
        fi
        read -r -s -p "Confirm password: " pw2
        say ""
        if [[ "$pw1" == "$pw2" ]]; then
            REPLY="$pw1"
            return 0
        fi
        say "Passwords did not match. Try again."
    done
}

prompt_logger_ip() {
    say ""
    say "Inverter network address"
    say "  Find this in your router's connected-devices list (often 192.168.x.x)."
    say "  The inverter must be on the same Wi-Fi as this computer."
    say "  Leave blank if the inverter is off right now — you can add it later."
    read -r -p "Inverter IP address [skip for now]: " REPLY
}

prompt_logger_serial() {
    say ""
    say "Logger serial number (on the small sticker on the inverter, 10 digits)."
    read -r -p "Serial [default 4145330384]: " REPLY
    REPLY="${REPLY:-4145330384}"
}

write_stack_env() {
    local mqtt_password="$1"
    local logger_ip="$2"
    local logger_serial="$3"

    if [[ ! -f "$STACK_ENV_FILE" ]]; then
        cp "$STACK_ENV_EXAMPLE" "$STACK_ENV_FILE"
    fi

    python3 "${SCRIPT_DIR}/lib/write_env.py" "$STACK_ENV_FILE" \
        "MQTT_PASSWORD=${mqtt_password}" \
        "LOGGER_IP=${logger_ip}" \
        "LOGGER_SERIAL=${logger_serial}"
}

verify_broker_quiet() {
    load_stack_env
    mosquitto_is_running || return 1
    docker exec mosquitto mosquitto_pub -h localhost \
        -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "setup/ping" -m ok &>/dev/null
}

main() {
    require_docker

    say "========================================"
    say "  Deye solar inverter — easy setup"
    say "========================================"
    say ""
    say "This configures the data collection software on this computer."
    say "You only need to answer a few questions."
    pause

    prompt_password
    local mqtt_password="$REPLY"

    prompt_logger_ip
    local logger_ip="$REPLY"

    prompt_logger_serial
    local logger_serial="$REPLY"

    say ""
    say "Saving configuration..."
    write_stack_env "$mqtt_password" "$logger_ip" "$logger_serial"

    say "Starting message broker..."
    "${SCRIPT_DIR}/stack.sh" up mosquitto

    load_stack_env
    say ""
    if verify_broker_quiet; then
        say "Broker is running."
    else
        say "Broker started (waiting for connection — this is usually fine)."
    fi

    say ""
    say "========================================"
    say "  Setup complete"
    say "========================================"
    say ""
    say "This computer's address: ${HOST_IP}"
    say "MQTT port: ${MQTT_PORT}"
    say "MQTT username: ${MQTT_USER}"
    say "MQTT password: (the one you just chose)"
    say ""
    say "Home Assistant: add an MQTT broker with the values above."

    if [[ -z "$logger_ip" ]]; then
        say ""
        say "When your inverter is online (daylight), run:"
        say "  ./setup.sh --add-inverter"
        say "or:"
        say "  ./scripts/stack.sh smoke && ./scripts/stack.sh up"
    else
        say ""
        read -r -p "Start reading from the inverter now? [y/N] " start_now
        if [[ "${start_now,,}" == "y" || "${start_now,,}" == "yes" ]]; then
            if "${SCRIPT_DIR}/stack.sh" smoke; then
                "${SCRIPT_DIR}/stack.sh" up deye-bridge
                say "Inverter bridge started. Metrics appear under: ${MQTT_TOPIC_PREFIX}/"
            else
                say "Could not reach the inverter yet."
                say "Try again in daylight, then run: ./scripts/stack.sh up"
            fi
        else
            say "Start later with: ./scripts/stack.sh up"
        fi
    fi
    say ""
}

add_inverter_only() {
    require_docker
    [[ -f "$STACK_ENV_FILE" ]] || {
        say "Run ./setup.sh first."
        exit 1
    }
    prompt_logger_ip
    [[ -n "$REPLY" ]] || {
        say "An inverter IP is required."
        exit 1
    }
    python3 "${SCRIPT_DIR}/lib/write_env.py" "$STACK_ENV_FILE" "LOGGER_IP=${REPLY}"
    "${SCRIPT_DIR}/stack.sh" render
    if "${SCRIPT_DIR}/stack.sh" smoke; then
        "${SCRIPT_DIR}/stack.sh" up deye-bridge
        load_stack_env
        say "Inverter bridge started. Metrics: ${MQTT_TOPIC_PREFIX}/"
    else
        say "Could not reach the inverter. Check IP and try again."
        exit 1
    fi
}

case "${1:-}" in
    --add-inverter) add_inverter_only ;;
    -h | --help)
        say "Usage: ./setup.sh          Interactive first-time setup"
        say "       ./setup.sh --add-inverter   Add inverter IP after initial setup"
        ;;
    *) main ;;
esac
