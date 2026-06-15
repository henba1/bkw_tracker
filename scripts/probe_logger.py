#!/usr/bin/env python3
"""Reachability probe for Deye WiFi loggers when MQTT reports logger offline."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from resilience_lib.logger_probe import (
    DEFAULT_TCP_PORTS,
    DEFAULT_TIMEOUT,
    format_report,
    logger_reachable,
    run_probe,
    wakeup_logger,
)
from resilience_lib.stack_env import load_stack_env


def mqtt_sub_once(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    topic: str,
    wait_seconds: int,
) -> str | None:
    cmd = [
        "mosquitto_sub",
        "-h",
        host,
        "-p",
        str(port),
        "-u",
        user,
        "-P",
        password,
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


def watch_offline_then_probe(
    *,
    ip: str,
    topic: str,
    threshold: int,
    wait_seconds: int,
    attempts: int,
    interval_sec: float,
    timeout: float,
) -> None:
    host = os.environ.get("MQTT_BROKER_HOST", "127.0.0.1")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    user = os.environ["MQTT_USER"]
    password = os.environ["MQTT_PASSWORD"]

    consecutive_offline = 0
    print(f"Watching {topic} — probe after {threshold} consecutive offline message(s).")
    print("Press Ctrl-C to stop.\n")

    while True:
        payload = mqtt_sub_once(
            host=host,
            port=port,
            user=user,
            password=password,
            topic=topic,
            wait_seconds=wait_seconds,
        )
        if payload is None:
            print(f"[{time.strftime('%H:%M:%S')}] no MQTT message within {wait_seconds}s")
            continue

        if payload == "offline":
            consecutive_offline += 1
            print(f"[{time.strftime('%H:%M:%S')}] logger_status=offline ({consecutive_offline}/{threshold})")
            if consecutive_offline >= threshold:
                print()
                ok, results = wakeup_logger(
                    ip,
                    attempts=attempts,
                    interval_sec=interval_sec,
                    timeout=timeout,
                )
                print(format_report(ip, results if results else run_probe(ip, timeout=timeout)))
                if not ok:
                    print(f"Wakeup failed after {attempts} attempt(s).")
                print()
                consecutive_offline = 0
        elif payload == "online":
            if consecutive_offline:
                print(f"[{time.strftime('%H:%M:%S')}] logger_status=online (counter reset)")
            consecutive_offline = 0
        else:
            print(f"[{time.strftime('%H:%M:%S')}] ignored payload: {payload!r}")


def main() -> int:
    load_stack_env()
    parser = argparse.ArgumentParser(
        description="Probe inverter/logger reachability when MQTT logger_status is offline.",
    )
    parser.add_argument("--ip", default=os.environ.get("LOGGER_IP"), help="Logger IP (or LOGGER_IP in stack.env)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Socket timeout in seconds (default {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=int(os.environ.get("LOGGER_WAKEUP_ATTEMPTS", "5")),
        help="Spaced wakeup attempts (default: LOGGER_WAKEUP_ATTEMPTS or 5)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("LOGGER_WAKEUP_INTERVAL_SEC", "8")),
        help="Seconds between wakeup attempts (default: LOGGER_WAKEUP_INTERVAL_SEC or 8)",
    )
    parser.add_argument(
        "--tcp-port",
        action="append",
        type=int,
        dest="tcp_ports",
        help=f"Extra TCP port to probe (default: {', '.join(map(str, DEFAULT_TCP_PORTS))})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print summary line and use exit code",
    )
    parser.add_argument(
        "--after-offline",
        type=int,
        metavar="N",
        help="Watch MQTT logger_status; run probe after N consecutive offline messages",
    )
    parser.add_argument(
        "--mqtt-wait",
        type=int,
        default=120,
        help="Seconds to wait for each MQTT message in watch mode (default 120)",
    )
    args = parser.parse_args()

    if not args.ip:
        print("Provide --ip or set LOGGER_IP in stack.env", file=sys.stderr)
        return 1

    tcp_ports = tuple(args.tcp_ports) if args.tcp_ports else DEFAULT_TCP_PORTS

    if args.after_offline is not None:
        if args.after_offline < 1:
            print("--after-offline must be >= 1", file=sys.stderr)
            return 1
        for key in ("MQTT_USER", "MQTT_PASSWORD"):
            if not os.environ.get(key):
                print(f"Set {key} in stack.env for watch mode", file=sys.stderr)
                return 1
        site = os.environ.get("SITE_ID", "home")
        inverter = os.environ.get("INVERTER_ID", "inverter")
        prefix = os.environ.get("MQTT_TOPIC_PREFIX") or f"solar/{site}/{inverter}"
        status_suffix = os.environ.get("MQTT_TOPIC_DEVICE_STATUS", "logger_status")
        topic = f"{prefix}/{status_suffix}"
        try:
            watch_offline_then_probe(
                ip=args.ip,
                topic=topic,
                threshold=args.after_offline,
                wait_seconds=args.mqtt_wait,
                attempts=args.attempts,
                interval_sec=args.interval,
                timeout=args.timeout,
            )
        except KeyboardInterrupt:
            print("\nStopped.")
        return 0

    ok, results = wakeup_logger(
        args.ip,
        attempts=args.attempts,
        interval_sec=args.interval,
        timeout=args.timeout,
    )
    if not ok:
        results = run_probe(args.ip, tcp_ports, args.timeout)
    if args.quiet:
        print("reachable" if logger_reachable(results) else "unreachable")
    else:
        print(format_report(args.ip, results))
    return 0 if logger_reachable(results) else 1


if __name__ == "__main__":
    sys.exit(main())
