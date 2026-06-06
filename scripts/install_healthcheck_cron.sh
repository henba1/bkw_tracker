#!/usr/bin/env bash
# Install Phase 5 watchdog cron (every 5 minutes).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STACK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HEALTHCHECK="${STACK_ROOT}/scripts/healthcheck.sh"
LOG_FILE="${HEALTHCHECK_LOG:-/tmp/bkw-healthcheck.log}"
CRON_LINE="*/5 * * * * ${HEALTHCHECK} >> ${LOG_FILE} 2>&1"

if [[ ! -x "$HEALTHCHECK" ]]; then
    chmod +x "$HEALTHCHECK"
fi

if crontab -l 2>/dev/null | grep -Fq "$HEALTHCHECK"; then
    echo "Cron entry already installed for ${HEALTHCHECK}"
    exit 0
fi

(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
echo "Installed: ${CRON_LINE}"
echo "Log: ${LOG_FILE}"
echo "Restarts deye-bridge if no MQTT traffic during daylight (see scripts/healthcheck.sh)."
