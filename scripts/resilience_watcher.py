#!/usr/bin/env python3
"""Watch logger_status on MQTT and recover flaky Deye loggers with spaced LAN probes."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from resilience_lib.logger_probe import format_report, logger_reachable, run_probe, wakeup_logger
from resilience_lib.stack_env import load_stack_env

LOG = logging.getLogger("resilience_watcher")


def env_bool(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def logger_status_topic() -> str:
    site = os.environ.get("SITE_ID", "home")
    inverter = os.environ.get("INVERTER_ID", "inverter")
    prefix = os.environ.get("MQTT_TOPIC_PREFIX") or f"solar/{site}/{inverter}"
    suffix = os.environ.get("MQTT_TOPIC_DEVICE_STATUS", "logger_status")
    return f"{prefix}/{suffix}"


def resilience_topic() -> str:
    site = os.environ.get("SITE_ID", "home")
    inverter = os.environ.get("INVERTER_ID", "inverter")
    prefix = os.environ.get("MQTT_TOPIC_PREFIX") or f"solar/{site}/{inverter}"
    return f"{prefix}/_meta/resilience"


def mqtt_sub_once(topic: str, wait_seconds: int) -> str | None:
    host = os.environ.get("MQTT_BROKER_HOST", "127.0.0.1")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    cmd = [
        "mosquitto_sub",
        "-h",
        host,
        "-p",
        str(port),
        "-u",
        os.environ["MQTT_USER"],
        "-P",
        os.environ["MQTT_PASSWORD"],
        "-t",
        topic,
        "-C",
        "1",
        "-W",
        str(wait_seconds),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    payload = completed.stdout.strip()
    return payload or None


def mqtt_publish(topic: str, payload: str) -> None:
    host = os.environ.get("MQTT_BROKER_HOST", "127.0.0.1")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    cmd = [
        "mosquitto_pub",
        "-h",
        host,
        "-p",
        str(port),
        "-u",
        os.environ["MQTT_USER"],
        "-P",
        os.environ["MQTT_PASSWORD"],
        "-t",
        topic,
        "-m",
        payload,
        "-r",
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=False)


def restart_bridge(container: str) -> bool:
    completed = subprocess.run(["docker", "restart", container], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        LOG.error("Failed to restart %s: %s", container, completed.stderr.strip() or completed.stdout.strip())
        return False
    LOG.info("Restarted %s to trigger an immediate data read", container)
    return True


def attempt_recovery(
    *,
    ip: str,
    attempts: int,
    interval_sec: float,
    timeout: float,
    restart_on_success: bool,
    bridge_container: str,
) -> dict:
    started = time.time()
    ok, probe_results = wakeup_logger(ip, attempts=attempts, interval_sec=interval_sec, timeout=timeout)
    report = {
        "event": "recovery_attempt",
        "ip": ip,
        "wakeup_ok": ok,
        "attempts": attempts,
        "interval_sec": interval_sec,
        "elapsed_sec": round(time.time() - started, 2),
        "probe": [{"name": r.name, "ok": r.ok, "detail": r.detail} for r in probe_results],
        "bridge_restarted": False,
    }

    if ok:
        LOG.info("Logger wakeup succeeded on LAN probe")
        if restart_on_success:
            report["bridge_restarted"] = restart_bridge(bridge_container)
    else:
        full = run_probe(ip, timeout=timeout)
        report["probe"] = [{"name": r.name, "ok": r.ok, "detail": r.detail} for r in full]
        report["reachable"] = logger_reachable(full)
        LOG.warning("Logger wakeup failed after %s spaced attempt(s)", attempts)
        LOG.debug("%s", format_report(ip, full))

    return report


def main() -> int:
    load_stack_env()
    logging.basicConfig(
        level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if os.environ.get("ACQUISITION_ADAPTER", "deye") != "deye":
        LOG.info("ACQUISITION_ADAPTER is not deye — resilience watcher exiting")
        return 0
    if not env_bool("LOGGER_RESILIENCE_ENABLED", default=True):
        LOG.info("LOGGER_RESILIENCE_ENABLED=false — exiting")
        return 0

    for key in ("MQTT_USER", "MQTT_PASSWORD", "LOGGER_IP"):
        if not os.environ.get(key):
            LOG.error("Missing %s in stack.env", key)
            return 1

    ip = os.environ["LOGGER_IP"]
    status_topic = logger_status_topic()
    attempts = int(os.environ.get("LOGGER_WAKEUP_ATTEMPTS", "5"))
    interval_sec = float(os.environ.get("LOGGER_WAKEUP_INTERVAL_SEC", "8"))
    timeout = float(os.environ.get("LOGGER_PROBE_TIMEOUT_SEC", "2"))
    mqtt_wait = int(os.environ.get("LOGGER_RESILIENCE_MQTT_WAIT_SEC", "120"))
    cooldown_sec = float(os.environ.get("LOGGER_RECOVERY_COOLDOWN_SEC", "90"))
    restart_on_success = env_bool("LOGGER_RECOVERY_RESTART", default=True)
    bridge_container = os.environ.get("DEYE_BRIDGE_CONTAINER", "deye-bridge")
    offline_threshold = max(1, int(os.environ.get("LOGGER_OFFLINE_THRESHOLD", "1")))

    LOG.info(
        "Watching %s — after %s offline message(s), up to %s wakeup probe(s) every %ss",
        status_topic,
        offline_threshold,
        attempts,
        interval_sec,
    )

    consecutive_offline = 0
    last_recovery_at = 0.0

    while True:
        payload = mqtt_sub_once(status_topic, mqtt_wait)
        if payload is None:
            LOG.debug("No MQTT message on %s within %ss", status_topic, mqtt_wait)
            continue

        if payload == "offline":
            consecutive_offline += 1
            LOG.info("logger_status=offline (%s/%s)", consecutive_offline, offline_threshold)
            if consecutive_offline < offline_threshold:
                continue

            now = time.time()
            if now - last_recovery_at < cooldown_sec:
                LOG.info(
                    "Skipping recovery — cooldown (%ss remaining)",
                    int(cooldown_sec - (now - last_recovery_at)),
                )
                consecutive_offline = 0
                continue

            report = attempt_recovery(
                ip=ip,
                attempts=attempts,
                interval_sec=interval_sec,
                timeout=timeout,
                restart_on_success=restart_on_success,
                bridge_container=bridge_container,
            )
            mqtt_publish(resilience_topic(), json.dumps(report))
            last_recovery_at = time.time()
            consecutive_offline = 0
        elif payload == "online":
            if consecutive_offline:
                LOG.debug("logger_status=online — counter reset")
            consecutive_offline = 0
        else:
            LOG.debug("Ignored payload on %s: %r", status_topic, payload)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        LOG.info("Stopped.")
        raise SystemExit(0) from None
