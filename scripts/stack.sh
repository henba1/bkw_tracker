#!/usr/bin/env bash
# IaC entrypoint: configure and run the full stack from stack.env.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/stack.sh
source "${SCRIPT_DIR}/lib/stack.sh"

usage() {
    cat <<EOF
Usage: ./scripts/stack.sh <command>

Commands:
  setup           Interactive wizard (same as ./setup.sh)
  init            Create stack.env from example (if missing), render configs + MQTT passwd
  render          Regenerate derived configs from stack.env (no containers)
  up              render + docker compose up -d
  down            docker compose down
  ps              docker compose ps
  logs [service]  docker compose logs -f [service]
  verify-broker   Test MQTT broker connectivity (Ctrl-C to exit)
  verify-metrics  Wait for one ac/active_power message (Phase 2 accept)
  smoke           Run SolarmanV5 smoke read using stack.env logger settings

Configure everything in stack.env (copy from stack.env.example).
EOF
}

cmd_setup() {
    exec "${SCRIPT_DIR}/setup.sh" "$@"
}

cmd_init() {
    if [[ ! -f "$STACK_ENV_FILE" ]]; then
        cp "$STACK_ENV_EXAMPLE" "$STACK_ENV_FILE"
        echo "Created ${STACK_ENV_FILE} — edit it, then re-run: ./scripts/stack.sh init"
        return 0
    fi
    render_mqtt_passwd
    if require_logger_env 2>/dev/null; then
        render_stack_configs
        echo "Full stack config rendered."
    else
        echo "Broker config rendered. Set LOGGER_IP in stack.env before starting deye-bridge."
    fi
    echo "Start broker only: ./scripts/stack.sh up mosquitto"
    echo "Start full stack (after logger online): ./scripts/stack.sh up"
}

cmd_render() {
    render_mqtt_passwd
    if require_logger_env 2>/dev/null; then
        render_stack_configs
    else
        echo "Skipped deye-bridge/HA render — set LOGGER_IP and LOGGER_SERIAL in stack.env."
    fi
}

cmd_up() {
    render_mqtt_passwd
    local services=("$@")
    if ((${#services[@]} == 0)) || [[ " ${services[*]} " == *" deye-bridge "* ]]; then
        render_stack_configs
    fi
    if ((${#services[@]} > 0)); then
        compose_cmd up -d "${services[@]}"
    else
        compose_cmd up -d
    fi
}

cmd_down() {
    load_stack_env
    compose_cmd down "$@"
}

cmd_ps() {
    load_stack_env
    compose_cmd ps
}

cmd_logs() {
    load_stack_env
    compose_cmd logs -f "$@"
}

cmd_verify_broker() {
    require_mqtt_env
    local -a sub_args=(-u "$MQTT_USER" -P "$MQTT_PASSWORD" -t '#' -v)
    if mosquitto_is_running; then
        echo "Subscribing via mosquitto container as ${MQTT_USER} (Ctrl-C to stop)..."
        exec docker exec -it mosquitto mosquitto_sub -h localhost "${sub_args[@]}"
    elif command -v mosquitto_sub &>/dev/null; then
        echo "Subscribing on ${HOST_IP}:${MQTT_PORT} as ${MQTT_USER} (Ctrl-C to stop)..."
        exec mosquitto_sub -h "$HOST_IP" "${sub_args[@]}"
    else
        echo "Subscribing via Docker (host network) as ${MQTT_USER} (Ctrl-C to stop)..."
        exec docker run --rm -it --network host eclipse-mosquitto:2 \
            mosquitto_sub -h 127.0.0.1 "${sub_args[@]}"
    fi
}

cmd_verify_metrics() {
    require_mqtt_env
    local topic="${MQTT_TOPIC_PREFIX}/ac/active_power"
    local wait_seconds="${VERIFY_METRICS_TIMEOUT:-60}"
    echo "Waiting for MQTT on ${topic} (timeout ${wait_seconds}s)..."
    local payload
    payload="$(timeout "$wait_seconds" mosquitto_sub_cmd \
        -u "$MQTT_USER" -P "$MQTT_PASSWORD" \
        -t "$topic" -C 1 -W "$wait_seconds" 2>/dev/null || true)"
    if [[ -z "$payload" ]]; then
        echo "FAIL: no message on ${topic} — is deye-bridge running and logger online?" >&2
        return 1
    fi
    echo "OK: ${topic} = ${payload}"
}

cmd_smoke() {
    require_logger_env
    local -a smoke_args=(
        "${STACK_ROOT}/scripts/smoke_read.py"
        --ip "$LOGGER_IP"
        --serial "$LOGGER_SERIAL"
        --port "$LOGGER_PORT"
    )
    if command -v uv &>/dev/null && [[ -f "${STACK_ROOT}/pyproject.toml" ]]; then
        uv run --project "${STACK_ROOT}" "${smoke_args[@]}"
    else
        python3 "${smoke_args[@]}"
    fi
}

main() {
    local cmd="${1:-}"
    shift || true
    case "$cmd" in
        setup) cmd_setup "$@" ;;
        init) cmd_init "$@" ;;
        render) cmd_render "$@" ;;
        up) cmd_up "$@" ;;
        down) cmd_down "$@" ;;
        ps) cmd_ps "$@" ;;
        logs) cmd_logs "$@" ;;
        verify-broker) cmd_verify_broker "$@" ;;
        verify-metrics) cmd_verify_metrics "$@" ;;
        smoke) cmd_smoke "$@" ;;
        -h | --help | help | "") usage ;;
        *)
            echo "Unknown command: ${cmd}" >&2
            usage >&2
            return 1
            ;;
    esac
}

main "$@"
