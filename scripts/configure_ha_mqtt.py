#!/usr/bin/env python3
"""Add MQTT broker config entry to homeassistant (HA 2024+ — no YAML broker)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

STACK_ROOT = Path(__file__).resolve().parents[1]
STACK_ENV = STACK_ROOT / "stack.env"
HA_CONTAINER = "homeassistant"


def load_stack_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in STACK_ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def resolve_ha_config() -> Path:
    result = subprocess.run(
        [
            "docker",
            "inspect",
            HA_CONTAINER,
            "--format",
            "{{range .Mounts}}{{if eq .Destination \"/config\"}}{{.Source}}{{end}}{{end}}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    path = Path(result.stdout.strip())
    if not path.is_dir():
        msg = f"HA config mount not found for container {HA_CONTAINER}"
        raise SystemExit(msg)
    return path


def test_mqtt(broker: str, port: int, username: str, password: str) -> None:
    result = subprocess.run(
        [
            "docker",
            "exec",
            "mosquitto",
            "mosquitto_sub",
            "-h",
            broker,
            "-p",
            str(port),
            "-u",
            username,
            "-P",
            password,
            "-t",
            "$SYS/broker/version",
            "-C",
            "1",
            "-W",
            "5",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"Cannot connect to MQTT at {broker}:{port}")


def new_entry_id() -> str:
    result = subprocess.run(
        [
            "docker",
            "exec",
            HA_CONTAINER,
            "python3",
            "-c",
            "from homeassistant.util.ulid import ulid_now; print(ulid_now())",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    env = load_stack_env()
    password = env.get("MQTT_PASSWORD", "")
    if not password:
        print("Set MQTT_PASSWORD in stack.env", file=sys.stderr)
        return 1

    broker = env.get("MQTT_BROKER_HOST", "127.0.0.1")
    port = int(env.get("MQTT_PORT", "1883"))
    username = env.get("MQTT_USER", "solar")

    test_mqtt(broker, port, username, password)

    ha_config = resolve_ha_config()
    entries_file = ha_config / ".storage" / "core.config_entries"
    backup = entries_file.with_suffix(".config_entries.bak")
    shutil.copy2(entries_file, backup)
    print(f"Backed up {entries_file} → {backup}")

    data = json.loads(entries_file.read_text())
    entries = data["data"]["entries"]
    if any(e.get("domain") == "mqtt" for e in entries):
        print("MQTT config entry already exists — skipping")
        return 0

    now = datetime.now(UTC).isoformat()
    entry = {
        "created_at": now,
        "data": {
            "broker": broker,
            "port": port,
            "username": username,
            "password": password,
        },
        "disabled_by": None,
        "discovery_keys": {},
        "domain": "mqtt",
        "entry_id": new_entry_id(),
        "minor_version": 1,
        "modified_at": now,
        "options": {
            "discovery": True,
            "discovery_prefix": "homeassistant",
        },
        "pref_disable_new_entities": False,
        "pref_disable_polling": False,
        "source": "user",
        "subentries": [],
        "title": broker,
        "unique_id": None,
        "version": 2,
    }
    entries.append(entry)
    entries_file.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Added MQTT config entry for {broker}:{port} (user {username})")
    print(f"Restart: docker restart {HA_CONTAINER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
